#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G1 视觉检测 v3 - D435i 双模式
- 模式1 [人脸检测]: Haar Cascade 人脸检测
- 模式2 [手势识别]: MediaPipe 手势分类

用法:
    python3.8 g1_gesture.py              # 有GUI
    python3.8 g1_gesture.py --no-display  # 纯终端
    python3.8 g1_gesture.py --debug       # 显示调试信息

按键:
    1   - 切换到人脸检测模式
    2   - 切换到手势识别模式
    ESC - 退出
"""

import os
# 防止无GUI环境下 MediaPipe/OpenCV 触发 Segfault
os.environ["DISPLAY"] = ":0"
os.environ["GDK_BACKEND"] = ""
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import warnings
warnings.filterwarnings("ignore", message=".*Gdk.*")
warnings.filterwarnings("ignore", message=".*Gtk.*")

import argparse
import math
import time
import threading

import cv2
import numpy as np
import pyrealsense2 as rs

try:
    import mediapipe as mp
except ImportError:
    print("❌ 缺少 mediapipe: pip install mediapipe")
    exit(1)

mp_hands = mp.solutions.hands


# ========== 模式定义 ==========
MODE_FACE = "face"
MODE_GESTURE = "gesture"
MODE_NAMES = {MODE_FACE: "👤 人脸检测", MODE_GESTURE: "✋ 手势识别"}


# ========== 人脸检测 ==========
# 使用 Haar Cascade 分类器（OpenCV 内置，无需额外安装）
_face_cascade = None
_CASCADE_URL = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
_CASCADE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "haarcascade_frontalface_default.xml")


def _init_face_detect():
    """初始化人脸检测器"""
    global _face_cascade, _CASCADE_PATH

    # 优先用本地文件
    if not os.path.exists(_CASCADE_PATH):
        # 尝试 cv2.data（完整版 opencv-python）
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            if os.path.exists(cascade_path):
                _CASCADE_PATH = cascade_path
        except AttributeError:
            pass

    # 如果还是没有，下载
    if not os.path.exists(_CASCADE_PATH):
        print("⬇️  下载人脸分类器...")
        try:
            import urllib.request
            urllib.request.urlretrieve(_CASCADE_URL, _CASCADE_PATH)
            print("✅ 下载完成")
        except Exception as e:
            print(f"⚠️ 下载失败: {e}，跳过人脸检测")
            return

    if os.path.exists(_CASCADE_PATH):
        _face_cascade = cv2.CascadeClassifier(_CASCADE_PATH)
        print("✅ 人脸检测已加载")
    else:
        print("⚠️ 未找到人脸分类器文件，跳过人脸检测")

def detect_faces(img):
    """检测人脸，返回人脸数量和位置列表"""
    global _face_cascade
    if _face_cascade is None:
        return 0, []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    result = _face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
    )
    # 兼容不同 OpenCV 版本：可能返回 ndarray 或 (rects, weights) 元组
    if isinstance(result, tuple):
        faces = result[0] if len(result) > 0 else np.empty((0, 4), dtype=np.int32)
    else:
        faces = result
    if len(faces) == 0:
        return 0, []
    return len(faces), faces.tolist()


# ========== 向量工具 ==========

def _dist(a, b):
    """两点欧氏距离 (NormalizedCoord)"""
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)


def _angle_abc(a, b, c):
    """向量 BA 与 BC 的夹角（弧度），b 为顶点"""
    ba = (a.x - b.x, a.y - b.y, a.z - b.z)
    bc = (c.x - b.x, c.y - b.y, c.z - b.z)
    dot = ba[0]*bc[0] + ba[1]*bc[1] + ba[2]*bc[2]
    la = math.sqrt(ba[0]**2 + ba[1]**2 + ba[2]**2)
    lc = math.sqrt(bc[0]**2 + bc[1]**2 + bc[2]**2)
    if la < 1e-6 or lc < 1e-6:
        return 0.0
    cos_val = max(-1.0, min(1.0, dot / (la * lc)))
    return math.acos(cos_val)


# ========== 手指状态判断 ==========

def _is_finger_extended(lm, tip_idx, pip_idx, mcp_idx):
    """通过 PIP-MCP-TIP 角度判断手指是否伸直
    伸直时角度接近 180°(π)，弯曲时 < 150°
    """
    angle = _angle_abc(lm[tip_idx], lm[pip_idx], lm[mcp_idx])
    return angle > 2.5  # ~143° 以上算伸直


def _is_thumb_extended(lm, handedness):
    """拇指: 主要判断是否向上伸出（y方向为主）
    拇指向上时 tip 的 y 值明显小于手腕/其他手指
    """
    # 核心指标：拇指 tip 相对手腕的垂直位置
    thumb_above_wrist = lm[0].y - lm[4].y  # 正值=拇指在手腕上方

    # 辅助指标：x 方向偏移（区分左右手）
    dx = lm[4].x - lm[3].x
    is_right = (handedness == "Right")

    # 主要条件：拇指明显在手腕上方（最可靠的信号）
    if thumb_above_wrist < 0.03:
        return False  # 拇指没抬起来，肯定不是伸出

    # 次要条件：x 方向大致正确
    if is_right and dx > 0.03:
        return False   # 右手拇指向右了，不太像伸出
    if not is_right and dx < -0.03:
        return False   # 左手拇指向左了

    return True


# ========== 手势分类 ==========

def classify_gesture(landmarks, handedness="Right"):
    """基于角度的手势分类，返回 (英文名, 中文名)"""
    lm = landmarks

    thumb_up = _is_thumb_extended(lm, handedness)
    idx_up   = _is_finger_extended(lm, 8,  6, 5)
    mid_up   = _is_finger_extended(lm, 12, 10, 9)
    ring_up  = _is_finger_extended(lm, 16, 14, 13)
    pinky_up = _is_finger_extended(lm, 20, 18, 17)

    four_up = [idx_up, mid_up, ring_up, pinky_up]
    n_four = sum(four_up)

    # 拇指相对手腕的高度（正=向上）
    thumb_height = lm[0].y - lm[4].y

    # ===== 优先判断 thumbs_up (四指弯曲 + 拇指抬起) =====
    if n_four == 0 and thumb_up and thumb_height > 0.04:
        return "thumbs_up", "yes"

    # ===== fist: 四指弯曲 + 拇指明显收拢 =====
    if n_four == 0 and not thumb_up:
        # 收紧：拇指 tip 必须靠近食指 tip（握拳状态）且没有抬高
        thumb_to_index = _dist(lm[4], lm[8])
        if thumb_to_index < 0.07 and thumb_height < 0.02:
            return "fist", "拳头"

    # ===== palm: 全部张开 =====
    if n_four == 4 and thumb_up:
        return "palm", "手掌"

    # ===== thumbs_down: 拇指向下 + 其余弯曲 =====
    if n_four == 0 and not thumb_up and lm[4].y > lm[3].y + 0.02:
        return "thumbs_down", "拇指向下"

    # --- peace: 食指+中指 ---
    if idx_up and mid_up and not ring_up and not pinky_up:
        return "peace", "剪刀手"

    # ===== 仅食指 (point系列) 放在 ok 前面，防止 ok 拦截 =====
    if idx_up and not mid_up and not ring_up and not pinky_up:
        finger_dir_x = lm[8].x - lm[5].x
        if finger_dir_x > 0.025:
            return "point_right", "右指"
        elif finger_dir_x < -0.025:
            return "point_left", "左指"
        return "point", "指向"

    # --- rock: 食指+小指 ---
    if idx_up and pinky_up and not mid_up and not ring_up:
        return "rock", "摇滚"

    # --- ok: 拇指尖与食指尖距离近（收紧：排除食指伸出状态） ---
    if _dist(lm[4], lm[8]) < 0.05 and not idx_up:
        return "ok", "OK"

    # --- three: 食中无名 ---
    if idx_up and mid_up and ring_up and not pinky_up:
        return "three", "三"

    return "unknown", f"未知({n_four}指)"


# ========== 主程序（双模式） ==========

def run(show_display=True, debug=False):
    WIDTH, HEIGHT = 640, 480

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, 30)
    profile = pipeline.start(config)

    # 初始化人脸检测
    _init_face_detect()

    # 初始化手势识别
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.65,
        min_tracking_confidence=0.5,
        model_complexity=0,
    )

    # 模式状态
    mode = MODE_FACE
    last_gesture = ""
    stable_count = 0
    STABLE = 2  # 降低防抖阈值：2帧≈67ms，提升响应速度
    last_face_count = -1   # 上次人脸数，避免重复打印
    fps_counter = 0
    fps_time = time.time()
    # 无GUI模式下用线程读取按键
    key_input = None

    def _read_keys():
        """无GUI模式下读取终端按键"""
        nonlocal key_input
        import sys
        import select
        while True:
            if select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                if ch:
                    key_input = ch
            time.sleep(0.05)

    print("=" * 45)
    print("  G1 视觉检测 v3 (双模式)")
    print("=" * 45)
    print(f"  当前: {MODE_NAMES[mode]}")
    print("\n  ┌─ 操作按键 ─────────────────────┐")
    print("  │ 1       人脸检测模式             │")
    print("  │ 2       手势识别模式             │")
    print("  │ ESC     退出                     │")
    print("  └────────────────────────────────┘")

    if not show_display:
        # 无GUI：启动键盘监听线程
        t = threading.Thread(target=_read_keys, daemon=True)
        t.start()
        print("\n  (纯终端模式，直接按 1/2/ESC 键)")

    try:
        while True:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue

            img = np.asanyarray(color_frame.get_data())
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # ---- 模式1: 人脸检测 ----
            if mode == MODE_FACE:
                n_faces, face_boxes = detect_faces(img)

                # 终端输出（仅变化时）
                if n_faces != last_face_count:
                    if n_faces > 0:
                        print(f"👤 检测到 {n_faces} 张人脸")
                    else:
                        print("👤 未检测到人脸")
                    last_face_count = n_faces

                if show_display:
                    for (x, y, fw, fh) in face_boxes:
                        cv2.rectangle(img, (x, y), (x+fw, y+fh), (255, 0, 0), 2)
                        cv2.putText(img, "Face", (x, y-8),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

            # ---- 模式2: 手势识别 ----
            elif mode == MODE_GESTURE:
                results = hands.process(img_rgb)
                current_gesture = ""

                if results.multi_hand_landmarks and results.multi_handedness:
                    for hl, hd in zip(results.multi_hand_landmarks,
                                       results.multi_handedness):
                        handedness = hd.classification[0].label
                        name_en, name_cn = classify_gesture(hl.landmark, handedness)
                        current_gesture = name_en

                        if show_display:
                            h, w = img.shape[:2]
                            pts = [(int(lm.x * w), int(lm.y * h)) for lm in hl.landmark]
                            connections = [
                                (0,1),(1,2),(2,3),(3,4),
                                (0,5),(5,6),(6,7),(7,8),
                                (0,9),(9,10),(10,11),(11,12),
                                (0,13),(13,14),(14,15),(15,16),
                                (0,17),(17,18),(18,19),(19,20),
                                (5,9),(13,17)]
                            for a, b in connections:
                                cv2.line(img, pts[a], pts[b], (0,255,0), 2)
                            for p in pts:
                                cv2.circle(img, p, 4, (0,0,255), -1)
                            wrist = pts[0]
                            cv2.putText(img, name_cn,
                                        (max(0,wrist[0]-50), max(20,wrist[1]-30)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

                        if debug:
                            lm = hl.landmark
                            t = _is_thumb_extended(lm, handedness)
                            iu = _is_finger_extended(lm, 8,6,5)
                            mu = _is_finger_extended(lm, 12,10,9)
                            ru = _is_finger_extended(lm, 16,14,13)
                            pu = _is_finger_extended(lm, 20,18,17)
                            # 静默模式：不打印每帧手指状态，只输出最终识别结果
                            pass

                # 防抖输出
                if current_gesture and current_gesture != "unknown":
                    if current_gesture == last_gesture:
                        stable_count += 1
                        if stable_count == STABLE:
                            print(f"✅ {name_cn} ({current_gesture})")
                    else:
                        last_gesture = current_gesture
                        stable_count = 1
                else:
                    last_gesture = ""
                    stable_count = 0

            # FPS
            fps_counter += 1
            now = time.time()
            if now - fps_time >= 1.0:
                # FPS 统计（静默，不打印）
                fps_counter = 0
                fps_time = now

            # 显示 & 按键处理
            if show_display:
                # 左上角显示当前模式
                cv2.putText(img, f"[{MODE_NAMES[mode]}]",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("G1 Vision (1:人脸 2:手势 ESC退出)", img)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('1'):
                    mode = MODE_FACE
                    last_face_count = -1
                    print(f"\n>>> 切换到 {MODE_NAMES[mode]}")
                elif key == ord('2'):
                    mode = MODE_GESTURE
                    last_gesture = ""
                    stable_count = 0
                    print(f"\n>>> 切换到 {MODE_NAMES[mode]}")
                elif key == 27:  # ESC
                    break
            else:
                # 无GUI：从线程读取按键
                if key_input is not None:
                    k = key_input
                    key_input = None
                    if k == '1':
                        mode = MODE_FACE
                        last_face_count = -1
                        print(f"\n>>> 切换到 {MODE_NAMES[mode]}")
                    elif k == '2':
                        mode = MODE_GESTURE
                        last_gesture = ""
                        stable_count = 0
                        print(f"\n>>> 切换到 {MODE_NAMES[mode]}")
                    elif k == '\x1b':  # ESC
                        break
                time.sleep(0.01)  # 减少睡眠时间：10ms（原30ms），提升响应速度

    finally:
        pipeline.stop()
        hands.close()
        cv2.destroyAllWindows()
        print("\n👋 已停止")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="G1 视觉检测 v3 (双模式)")
    parser.add_argument("--no-display", action="store_true", help="纯终端输出")
    parser.add_argument("--debug", action="store_true", help="显示调试信息")
    args = parser.parse_args()

    run(show_display=not args.no_display, debug=args.debug)

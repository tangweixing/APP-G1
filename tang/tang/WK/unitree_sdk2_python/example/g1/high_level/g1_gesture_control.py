#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G1 手势遥控 - D435i 深度相机手势识别 → 五模式控制

用法:
    python3.8 g1_gesture_control.py eth0

操作:
    R      - 开始/暂停 手势识别
    1/2/3/4/5  - 切换模式
    Q      - 退出

五种模式:
    Mode 1 [手势控制]  - thumbs_up→握手, ok→释放手臂
    Mode 2 [跟随]      - 握拳后机器人跟随，保持0.6m
    Mode 3 [走近+握手] - 握拳(画面中央)→走到0.5-0.6m→自动执行握手
    Mode 4 [手势导航]  - 左指→左转90° 右指→右转90° 握拳→前进2步 手掌→后退2步
    Mode 5 [人脸问候]  - 检测人脸→走近到0.5m→居中→握手→语音"你好"
"""

import os
# ===== 关键：无GUI环境下防止 OpenCV/MediaPipe 崩溃 =====
os.environ["DISPLAY"] = ":0"          # 设一个假的 display（不能为空）
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["GDK_BACKEND"] = ""        # 禁用 GDK/GTK 后端
os.environ["MPLBACKEND"] = "Agg"      # matplotlib 无头

# 抑制 Gtk/Gdk 警告输出
import warnings
warnings.filterwarnings("ignore", message=".*Gdk.*")
warnings.filterwarnings("ignore", message=".*Gtk.*")
warnings.filterwarnings("ignore", message=".*display.*")

import sys
import time
import select
import termios
import tty
import threading
import signal
import math

import cv2
import numpy as np
import pyrealsense2 as rs

try:
    import mediapipe as mp
except ImportError:
    print("❌ 缺少 mediapipe: pip install mediapipe")
    exit(1)

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient

mp_hands = mp.solutions.hands


# ========== 手势识别（轻量版）==========

def _angle_abc(a, b, c):
    ba = (a.x - b.x, a.y - b.y, a.z - b.z)
    bc = (c.x - b.x, c.y - b.y, c.z - b.z)
    dot = ba[0]*bc[0] + ba[1]*bc[1] + ba[2]*bc[2]
    la = math.sqrt(ba[0]**2 + ba[1]**2 + ba[2]**2)
    lc = math.sqrt(bc[0]**2 + bc[1]**2 + bc[2]**2)
    if la < 1e-6 or lc < 1e-6:
        return 0.0
    return math.acos(max(-1.0, min(1.0, dot / (la * lc))))


def _is_finger_extended(lm, tip_idx, pip_idx, mcp_idx):
    return _angle_abc(lm[tip_idx], lm[pip_idx], lm[mcp_idx]) > 2.5


def _is_thumb_extended(lm, handedness):
    """拇指: 主要判断是否向上伸出（y方向为主）"""
    thumb_above_wrist = lm[0].y - lm[4].y  # 正值=拇指在手腕上方
    if thumb_above_wrist < 0.03:
        return False
    # 辅助：x 方向大致正确
    dx = lm[4].x - lm[3].x
    is_right = (handedness == "Right")
    if is_right and dx > 0.03:
        return False
    if not is_right and dx < -0.03:
        return False
    return True


def _dist(a, b):
    """两点欧氏距离"""
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)


def classify_gesture(landmarks, handedness="Right"):
    """基于角度的手势分类（与g1_gesture.py同步）"""
    lm = landmarks

    thumb_up = _is_thumb_extended(lm, handedness)
    idx_up   = _is_finger_extended(lm, 8,  6, 5)
    mid_up   = _is_finger_extended(lm, 12, 10, 9)
    ring_up  = _is_finger_extended(lm, 16, 14, 13)
    pinky_up = _is_finger_extended(lm, 20, 18, 17)

    four_up = [idx_up, mid_up, ring_up, pinky_up]
    n_four = sum(four_up)

    # 拇指相对手腕的高度
    thumb_height = lm[0].y - lm[4].y

    # ===== thumbs_up 优先 (四指弯曲 + 拇指明显抬起) =====
    if n_four == 0 and thumb_up and thumb_height > 0.04:
        return "thumbs_up"

    # ===== fist: 四指弯曲 + 拇指明显收拢 =====
    if n_four == 0 and not thumb_up:
        thumb_to_index = _dist(lm[4], lm[8])
        if thumb_to_index < 0.07 and thumb_height < 0.02:
            return "fist"

    # ===== palm: 全部张开 + 拇指伸出 =====
    if n_four == 4 and thumb_up:
        return "palm"

    # ===== peace: 食指+中指 =====
    if idx_up and mid_up and not ring_up and not pinky_up:
        return "peace"

    # ===== 仅食指 (point系列) 放在 ok 前面 =====
    if idx_up and not mid_up and not ring_up and not pinky_up:
        finger_dir_x = lm[8].x - lm[5].x
        if finger_dir_x > 0.025:
            return "point_right"
        elif finger_dir_x < -0.025:
            return "point_left"
        return "point"

    # ===== rock: 食指+小指 =====
    if idx_up and pinky_up and not mid_up and not ring_up:
        return "rock"

    # ===== ok: 拇指尖与食指尖近 + 食指不伸直 =====
    if _dist(lm[4], lm[8]) < 0.05 and not idx_up:
        return "ok"

    # ===== three: 食中无名 =====
    if idx_up and mid_up and ring_up and not pinky_up:
        return "three"

    return "unknown"


# ========== 相机清理辅助函数 ==========

def _kill_camera_occupants():
    """清理占用 RealSense 相机的进程（启动手势识别前调用）。

    解决 "xioctl(VIDIOC_S_FMT) failed, errno=16 Device or resource busy"：
    当 g1_face_greet.py / face.py 等进程占用相机时，RealSense pipeline.start
    会报 "Device or resource busy"。这里在启动相机前先释放设备。

    注意：不能 kill g1_gesture_control.py 自身，否则会导致自杀后手势识别无法启动。
    """
    import subprocess
    import glob
    import os

    killed = []
    current_pid = os.getpid()

    # 1. kill 其他占用相机的脚本（不含 g1_gesture_control.py 自身）
    for script in ['g1_face_greet.py', 'face.py']:
        try:
            result = subprocess.run(
                ['pkill', '-9', '-f', script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                killed.append(script)
        except Exception:
            pass

    # 2. kill 所有占用 /dev/video* 的进程（排除当前 PID）
    video_devices = glob.glob('/dev/video*')
    if video_devices:
        try:
            # 先用 pgrep 找到占用设备的进程 PID
            for dev in video_devices:
                pgrep_result = subprocess.run(
                    ['fuser', dev],
                    capture_output=True, text=True, timeout=2
                )
                if pgrep_result.returncode == 0 and pgrep_result.stdout.strip():
                    pids = pgrep_result.stdout.strip().split()
                    # 排除当前进程 PID
                    for pid_str in pids:
                        try:
                            pid = int(pid_str)
                            if pid != current_pid:
                                subprocess.run(['kill', '-9', str(pid)], timeout=2)
                                killed.append(f"PID:{pid}")
                        except (ValueError, subprocess.TimeoutExpired):
                            pass
        except Exception:
            pass

    if killed:
        print(f"[相机] 已清理占用进程: {', '.join(killed)}")
        import time as _time
        _time.sleep(2.0)  # 等待 USB 设备释放


# ========== 三模式主类 ==========

class GestureControl:

    MODE_NAMES = {
        1: {"name": "手势控制", "desc": "thumbs_up→握手, ok→释放"},
        2: {"name": "跟随",     "desc": "握拳跟随(保持0.6m)"},
        3: {"name": "走近+握手", "desc": "握拳→调到0.5-0.6m+中央→握手"},
        4: {"name": "手势导航", "desc": "左指←转 右指→转 握拳前进 手掌后退"},
        5: {"name": "人脸问候", "desc": "检测人脸→走近0.5m+居中→握手+你好"},
    }

    def __init__(self, network_interface):
        print("=" * 55)
        print("   G1 手势遥控 v4 (五模式)")
        print("=" * 55)

        # ---- 网络初始化 ----
        try:
            ChannelFactoryInitialize(0, network_interface)
            print("✅ 网络已连接:", network_interface)
        except Exception as e:
            print(f"❌ 网络初始化失败: {e}")
            sys.exit(-1)

        # ---- 运动客户端 ----
        self.sport_client = LocoClient()
        self.sport_client.SetTimeout(10.0)
        try:
            self.sport_client.Init()
            print("✅ 运动客户端就绪")
        except Exception as e:
            print(f"⚠️ 运动客户端失败（运动功能不可用）: {e}")
            self.sport_client = None

        # ---- 机械臂客户端 ----
        self.arm_client = G1ArmActionClient()
        self.arm_client.SetTimeout(10.0)
        try:
            self.arm_client.Init()
            print("✅ 机械臂客户端就绪")
        except Exception as e:
            print(f"❌ 机械臂客户端失败: {e}")
            self.arm_client = None

        # ---- 语音客户端 ----
        self.audio_client = AudioClient()
        self.audio_client.SetTimeout(10.0)
        try:
            self.audio_client.Init()
            print("✅ 语音客户端就绪")
        except Exception as e:
            print(f"⚠️ 语音客户端失败: {e}")
            self.audio_client = None

        # ---- 基础状态 ----
        self.running = True
        self.gesture_active = False
        self.arm_busy = False
        self.last_action_gesture = ""
        self.cooldown_until = 0
        self.arm_lock = threading.Lock()
        # 是否为交互式终端 (用于决定状态行刷新方式)
        self.is_tty = sys.stdin.isatty()
        # 状态行节流: 非交互模式下避免日志过快刷屏
        self._last_status_ts = 0.0

        # ---- 模式 ----
        self.current_mode = 1          # 当前模式 1/2/3

        # ---- 跟随参数 (Mode 2) ----
        self.follow_active = False
        self.follow_target_dist = 0.7          # 目标跟随距离 0.7m
        self.follow_max_vx = 0.8
        self.follow_max_vy = 0.5
        self.follow_max_wz = 1.0                # 提高转向上限 (参考键盘遥控 gear2=0.8)
        self.follow_arrive_threshold = 0.08
        self.follow_lost_frames = 0
        self.follow_lost_limit = 15
        self.follow_send_vx = 0.0
        self.follow_send_vy = 0.0
        self.follow_send_wz = 0.0
        self.follow_smoothing = 0.15            # 与键盘遥控一致

        # ---- 走近+握手参数 (Mode 3) ----
        self.approach_dist_min = 0.5        # 目标距离下限
        self.approach_dist_max = 0.6        # 目标距离上限
        self.approach_dist_mid = (self.approach_dist_min + self.approach_dist_max) / 2  # 0.55m
        self.approach_center_threshold = 0.15 # 中央判定阈值 (归一化偏心)
        self.approach_max_vx = 0.35           # 更慢更安全
        self.approach_max_vy = 0.25
        self.approach_max_wz = 0.4
        self.approach_smoothing = 0.10
        self.approach_send_vx = 0.0
        self.approach_send_vy = 0.0
        self.approach_send_wz = 0.0
        # 状态: idle / adjusting(同时调距+调位) / arrived
        self.approach_state = "idle"
        self.approach_arrived_count = 0
        self.approach_arrived_need = 15  # 连续多少帧到位才触发握手

        # ---- 手势导航参数 (Mode 4) ----
        self.nav_busy = False          # 导航动作执行中（防重复触发）
        self.nav_rotate_speed = 0.40   # 转向速度 (rad/s)
        self.nav_rotate_time = 4.0     # 转向持续时间 → 0.4*4=1.6rad≈92°
        self.nav_move_speed = 0.25     # 前进/后退速度
        self.nav_move_steps = 2        # 步数，每步约1秒

        # ---- 人脸问候参数 (Mode 5) ----
        self.face_greet_state = "idle"   # idle / approaching / centering / greeting / done
        self.face_greet_target_dist = 0.5
        self.face_greet_center_threshold = 0.12
        self.face_greet_arrived_count = 0
        self.face_greet_arrived_need = 20
        self.face_greet_max_vx = 0.30
        self.face_greet_max_vy = 0.20
        self.face_greet_max_wz = 0.35
        self.face_greet_smoothing = 0.12
        self.face_greet_send_vx = 0.0
        self.face_greet_send_vy = 0.0
        self.face_greet_send_wz = 0.0

        # ---- 共享数据 ----
        self.latest_data = {
            "distance": 0.0,
            "x_offset": 0.0,
            "y_offset": 0.0,
            "gesture": "",
            "valid": False,
            # 人脸数据 (Mode 5)
            "face_detected": False,
            "face_count": 0,
            "face_center_x": 0.0,
            "face_center_y": 0.0,
        }
        self.data_lock = threading.Lock()

        self._print_help()

    def _print_help(self):
        print("\n  ┌─ 操作按键 ─────────────────────┐")
        print("  │ R       开始/暂停手势识别       │")
        print("  │ 1       Mode1 手势控制           │")
        print("  │ 2       Mode2 跟随模式           │")
        print("  │ 3       Mode3 走近+握手          │")
        print("  │ 4       Mode4 手势导航           │")
        print("  │ 5       Mode5 人脸问候           │")
        print("  │ Q       退出                     │")
        print("  ├─ 五种模式 ────────────────────┤")
        print("  │ Mode1: 👍握手  👌释放手臂       │")
        print("  │ Mode2: ✊握拳→跟随(0.6m)         │")
        print("  │ Mode3: ✊握拳→自动调距+调位→🤝   │")
        print("  │ Mode4: 👈左转  👉右转 ✊前进 🖐后退│")
        print("  │ Mode5: 👤检测人脸→走近→居中→🤝你好│")
        print("  └────────────────────────────────┘\n")

    # ==================== 机械臂 ====================

    def _execute_arm(self, action_name, desc):
        if self.arm_client is None:
            print("  ❌ 机械臂未就绪")
            return
        with self.arm_lock:
            if self.arm_busy:
                return
            self.arm_busy = True
        def _run():
            try:
                print(f"\n  🤖 执行: {desc} ({action_name})")
                self.arm_client.ExecuteAction(action_map.get(action_name))
                print(f"  ✅ 完成: {desc}")
            except Exception as e:
                print(f"  ❌ 动作失败: {e}")
            finally:
                with self.arm_lock:
                    self.arm_busy = False
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    # ==================== 停止运动 ====================

    def _stop_motion(self):
        """停止所有运动"""
        self.follow_active = False
        self.approach_state = "idle"
        self.approach_arrived_count = 0
        if self.sport_client is not None:
            try:
                self.sport_client.StopMove()
            except Exception:
                pass
        self.follow_send_vx = 0.0
        self.follow_send_vy = 0.0
        self.follow_send_wz = 0.0
        self.approach_send_vx = 0.0
        self.approach_send_vy = 0.0
        self.approach_send_wz = 0.0

    # ==================== Mode 1: 手势控制 ====================

    def _handle_mode1(self, gesture_name):
        """Mode 1: 手势 → 机械臂动作"""
        now = time.time()
        if now < self.cooldown_until:
            return
        if gesture_name == self.last_action_gesture:
            return

        mapping = {
            "thumbs_up": ("shake hand",    "握手"),
            "ok":         ("release arm",   "释放手臂"),
        }
        info = mapping.get(gesture_name)
        if not info:
            return

        self._execute_arm(info[0], info[1])
        self.last_action_gesture = gesture_name
        self.cooldown_until = now + 3.0

    # ==================== Mode 2: 跟随 ====================

    def _handle_mode2(self, gesture_name):
        """Mode 2: fist 启动/停止跟随"""
        if gesture_name == "fist":
            if not self.follow_active and self.sport_client is not None:
                self.follow_active = True
                self.follow_lost_frames = 0
                self.follow_send_vx = 0.0
                self.follow_send_vy = 0.0
                self.follow_send_wz = 0.0
                print(f"\n  🚶 Mode2 跟随启动! 目标: {self.follow_target_dist}m")
            return

        # 非fist → 停止跟随
        if self.follow_active:
            self._stop_motion()
            print("  ⏹️ Mode2 跟随已停止")

    # ==================== Mode 3: 走近+握手 ====================

    def _handle_mode3(self, gesture_name):
        """Mode 3: fist → 同时调整距离(0.5~0.6m) + 位置(中央) → 握手"""
        if gesture_name != "fist":
            # 非fist → 重置状态
            if self.approach_state != "idle":
                self._stop_motion()
                print("  ⏹️ Mode3 已重置（非fist）")
            return

        with self.data_lock:
            valid = self.latest_data["valid"]

        if not valid or self.sport_client is None:
            return

        # 检测到fist → 进入调整模式
        if self.approach_state == "idle":
            self.approach_state = "adjusting"
            self.approach_arrived_count = 0
            self.approach_send_vx = 0.0
            self.approach_send_vy = 0.0
            self.approach_send_wz = 0.0
            with self.data_lock:
                d = self.latest_data["distance"]
                xo = self.latest_data["x_offset"]
                yo = self.latest_data["y_offset"]
            print(f"\n  🎯 Mode3 检测到fist! 开始调整 (距:{d:.2f}m, 偏心:x={xo:+.2f} y={yo:+.2f})")

    def _compute_approach_cmd(self):
        """Mode 3: 同时计算距离修正 + 位置修正"""
        with self.data_lock:
            dist = self.latest_data["distance"]
            x_off = self.latest_data["x_offset"]
            y_off = self.latest_data["y_offset"]
            valid = self.latest_data["valid"]

        if not valid or self.approach_state != "adjusting" or self.sport_client is None:
            return 0.0, 0.0, 0.0

        # ---- 距离修正 ----
        # 目标: dist 在 [0.5, 0.6] 范围内
        if dist < self.approach_dist_min:
            # 太近了 → 后退
            dist_err = dist - self.approach_dist_min   # 负值，需要后退
            kp = 1.2
            target_vx = np.clip(dist_err * kp,
                               -self.approach_max_vx * 0.6,
                                -0.05)  # 后退最小速度
        elif dist > self.approach_dist_max:
            # 太远了 → 前进
            dist_err = dist - self.approach_dist_max   # 正值，需要前进
            kp = 1.2
            target_vx = np.clip(dist_err * kp,
                                0.05,
                                self.approach_max_vx)
        else:
            # 距离在目标范围内 → 微调到中点或停止
            mid_err = dist - self.approach_dist_mid
            target_vx = np.clip(mid_err * 0.8,
                               -self.approach_max_vx * 0.15,
                                self.approach_max_vx * 0.15)

        # ---- 位置修正（横移+转向）----
        target_vy = -x_off * self.approach_max_vy
        target_wz = -x_off * self.approach_max_wz * 0.4

        # ---- 到位判定: 距离在范围 + 位置在中央 ----
        dist_ok = (self.approach_dist_min <= dist <= self.approach_dist_max)
        pos_ok = (abs(x_off) < self.approach_center_threshold and
                  abs(y_off) < self.approach_center_threshold)

        if dist_ok and pos_ok:
            # 两项都满足 → 累加计数
            target_vx *= 0.15  # 大幅减速
            target_vy *= 0.15
            target_wz *= 0.15
            self.approach_arrived_count += 1
        else:
            # 不满足 → 减少计数（允许短暂偏离）
            self.approach_arrived_count = max(0, self.approach_arrived_count - 2)

        # 到位足够帧数 → 触发握手
        if self.approach_arrived_count >= self.approach_arrived_need:
            self.approach_state = "arrived"
            self._stop_motion()
            print(f"\n  🎉 到位! 距离:{dist:.2f}m(目标{self.approach_dist_min}-{self.approach_dist_max}) | "
                  f"偏心:x={x_off:+.2f} y={y_off:+.2f} → 执行握手!")
            self._execute_arm("shake hand", "握手(Mode3)")
            return 0.0, 0.0, 0.0

        return target_vx, target_vy, target_wz

    # ==================== Mode 4: 手势导航 ====================

    def _handle_mode4(self, gesture_name):
        """Mode 4: 手势导航 - 左指/右指/握拳/手掌"""
        if self.nav_busy or self.sport_client is None:
            return

        nav_actions = {
            "point_left":  ("左转90°",  lambda: self._nav_rotate(-self.nav_rotate_speed)),
            "point_right": ("右转90°",  lambda: self._nav_rotate( self.nav_rotate_speed)),
            "fist":        ("前进2步",  lambda: self._nav_move_forward()),
            "palm":        ("后退2步",  lambda: self._nav_move_backward()),
        }
        action = nav_actions.get(gesture_name)
        if action:
            self.nav_busy = True
            print(f"\n  🧭 Mode4 {action[0]}")
            t = threading.Thread(target=action[1], daemon=True)
            t.start()

    def _nav_rotate(self, wz):
        """转向动作（后台线程执行）"""
        try:
            for i in range(int(self.nav_rotate_time / 0.2)):
                if not self.running or self.current_mode != 4:
                    break
                self.sport_client.Move(0, 0, wz)
                time.sleep(0.2)
            self.sport_client.StopMove()
        except Exception as e:
            print(f"  ❌ 转向失败: {e}")
        finally:
            self.nav_busy = False

    def _nav_move_forward(self):
        """前进2步"""
        try:
            for step in range(self.nav_move_steps):
                if not self.running or self.current_mode != 4:
                    break
                self.sport_client.Move(self.nav_move_speed, 0, 0)
                time.sleep(1.0)
            self.sport_client.StopMove()
        except Exception as e:
            print(f"  ❌ 前进失败: {e}")
        finally:
            self.nav_busy = False

    def _nav_move_backward(self):
        """后退2步"""
        try:
            for step in range(self.nav_move_steps):
                if not self.running or self.current_mode != 4:
                    break
                self.sport_client.Move(-self.nav_move_speed, 0, 0)
                time.sleep(1.0)
            self.sport_client.StopMove()
        except Exception as e:
            print(f"  ❌ 后退失败: {e}")
        finally:
            self.nav_busy = False

    # ==================== Mode 5: 人脸问候 ====================

    def _handle_mode5_face(self, face_count, face_center_x, face_center_y, distance):
        """Mode 5: 检测到人脸时的回调（由相机线程调用）"""
        if self.face_greet_state == "done":
            return
        if self.sport_client is None:
            return

        # 首次检测到人脸 → 开始接近
        if self.face_greet_state == "idle" and face_count > 0:
            self.face_greet_state = "approaching"
            self.face_greet_arrived_count = 0
            self.face_greet_send_vx = 0.0
            self.face_greet_send_vy = 0.0
            self.face_greet_send_wz = 0.0
            with self.data_lock:
                d = self.latest_data["distance"]
            print(f"\n  👤 Mode5 检测到{face_count}张人脸! 开始接近 (当前距离:{d:.2f}m)")

    def _compute_face_greet_cmd(self):
        """Mode 5: 计算人脸接近+居中速度指令"""
        with self.data_lock:
            dist = self.latest_data["distance"]
            x_off = self.latest_data["x_offset"]
            y_off = self.latest_data["y_offset"]
            face_detected = self.latest_data["face_detected"]

        if not face_detected or self.face_greet_state not in ("approaching", "centering"):
            return 0.0, 0.0, 0.0

        # ---- 距离修正：目标 0.5m ----
        if dist < self.face_greet_target_dist - 0.05:
            target_vx = np.clip((dist - self.face_greet_target_dist) * 1.5,
                               -self.face_greet_max_vx * 0.6, -0.05)
        elif dist > self.face_greet_target_dist + 0.05:
            target_vx = np.clip((dist - self.face_greet_target_dist) * 1.5,
                                0.05, self.face_greet_max_vx)
        else:
            target_vx = 0.0

        # ---- 位置修正：让人脸居中 ----
        target_vy = -x_off * self.face_greet_max_vy
        target_wz = -x_off * self.face_greet_max_wz * 0.3

        # ---- 到位判定 ----
        dist_ok = abs(dist - self.face_greet_target_dist) < 0.08
        pos_ok = abs(x_off) < self.face_greet_center_threshold and abs(y_off) < self.face_greet_center_threshold

        if dist_ok and pos_ok:
            target_vx *= 0.15
            target_vy *= 0.15
            target_wz *= 0.15
            self.face_greet_arrived_count += 1
        else:
            self.face_greet_arrived_count = max(0, self.face_greet_arrived_count - 1)

        # 到位足够帧数 → 触发握手+语音
        if self.face_greet_arrived_count >= self.face_greet_arrived_need:
            self.face_greet_state = "greeting"
            self._stop_motion()
            print(f"\n  🎉 Mode5 到位! 距离:{dist:.2f}m | 偏心:x={x_off:+.2f} y={y_off:+.2f}")
            self._execute_arm("shake hand", "握手(Mode5)")
            if self.audio_client is not None:
                try:
                    self.audio_client.TtsMaker("你好！", 0)
                    print("  🔊 语音: 你好！")
                except Exception as e:
                    print(f"  ⚠️ 语音失败: {e}")
            self.face_greet_state = "done"
            return 0.0, 0.0, 0.0

        return target_vx, target_vy, target_wz

    # ==================== 统一手势回调 ====================

    def _on_gesture(self, gesture_name):
        """稳定手势回调 → 分发给当前模式"""
        if self.current_mode == 1:
            self._handle_mode1(gesture_name)
        elif self.current_mode == 2:
            self._handle_mode2(gesture_name)
        elif self.current_mode == 3:
            self._handle_mode3(gesture_name)
        elif self.current_mode == 4:
            self._handle_mode4(gesture_name)

    # ==================== 手势识别线程 ====================

    def _gesture_loop(self):
        print("[DEBUG] _gesture_loop: 开始")
        pipeline = None
        hands = None
        try:
            # 前置清理：确保相机未被占用 (解决 "Device or resource busy")
            print("[DEBUG] 检查并清理相机占用进程...")
            _kill_camera_occupants()

            print("[DEBUG] 创建 rs.pipeline")
            pipeline = rs.pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            print("[DEBUG] pipeline.start...")
            profile = pipeline.start(config)
            print("[DEBUG] camera OK")

            align = rs.align(rs.stream.color)

            print("[DEBUG] 初始化 MediaPipe Hands...")
            hands = mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.65,
                min_tracking_confidence=0.5,
                model_complexity=0,
            )
            print("[DEBUG] MediaPipe OK")

            # ---- 初始化人脸检测 (Mode 5) ----
            _face_cascade = None
            _cascade_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "haarcascade_frontalface_default.xml")
            if not os.path.exists(_cascade_path):
                try:
                    cp = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                    if os.path.exists(cp):
                        _cascade_path = cp
                except AttributeError:
                    pass
            # 还没有就下载
            if not os.path.exists(_cascade_path):
                print("⬇️  下载人脸分类器...")
                try:
                    import urllib.request
                    _CASCADE_URL = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
                    urllib.request.urlretrieve(_CASCADE_URL, _cascade_path)
                    print("✅ 人脸分类器下载完成")
                except Exception as e:
                    print(f"⚠️ 下载失败: {e}")
            if os.path.exists(_cascade_path):
                _face_cascade = cv2.CascadeClassifier(_cascade_path)
                # 关键：CascadeClassifier 加载失败不报错，必须检查 empty()
                if _face_cascade.empty():
                    print(f"⚠️ 分类器文件存在但加载失败: {_cascade_path}")
                    _face_cascade = None
                else:
                    print(f"✅ 人脸检测已加载 ({os.path.basename(_cascade_path)})")
            else:
                print("⚠️ 人脸检测未加载（Mode5不可用）")

            last_gesture = ""
            stable_count = 0
            STABLE = 5

            print("📷 手势识别线程就绪 (等待按 R 启动)")

            while self.running:
                if not self.gesture_active:
                    time.sleep(0.1)
                    self._stop_motion()
                    with self.data_lock:
                        self.latest_data["valid"] = False
                    continue

                frames = pipeline.wait_for_frames()
                aligned_frames = align.process(frames)
                color_frame = aligned_frames.get_color_frame()
                depth_frame = aligned_frames.get_depth_frame()

                if not color_frame or not depth_frame:
                    continue

                img = np.asanyarray(color_frame.get_data())
                h, w = img.shape[:2]
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # ---- 人脸检测 (Mode 5) ----
                if _face_cascade is not None and self.current_mode == 5:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    result = _face_cascade.detectMultiScale(gray, scaleFactor=1.1,
                                                            minNeighbors=5, minSize=(30, 30))
                    # 兼容不同 OpenCV 版本：可能返回 ndarray 或 (rects, weights) 元组
                    if isinstance(result, tuple):
                        faces = result[0] if len(result) > 0 else np.empty((0, 4), dtype=np.int32)
                    else:
                        faces = result
                    n_faces = len(faces)
                    fc_x, fc_y = 0.0, 0.0
                    if n_faces > 0:
                        # 取最大人脸的中心
                        max_area = 0
                        best_face = faces[0]
                        for face_rect in faces:
                            fx, fy, fw, fh = int(face_rect[0]), int(face_rect[1]), int(face_rect[2]), int(face_rect[3])
                            area = fw * fh
                            if area > max_area:
                                max_area = area
                                best_face = (fx, fy, fw, fh)
                        fx, fy, fw, fh = best_face
                        fc_x = (fx + fw / 2.0) / w   # 归一化中心x (0~1)
                        fc_y = (fy + fh / 2.0) / h   # 归一化中心y (0~1)
                        # 用人脸中心作为深度采样点
                        face_px = int(fx + fw / 2)
                        face_py = int(fy + fh / 2)
                        if 0 <= face_px < w and 0 <= face_py < h:
                            face_dist = depth_frame.get_distance(face_px, face_py)
                        else:
                            face_dist = 0
                    else:
                        face_dist = 0

                    with self.data_lock:
                        self.latest_data["face_detected"] = n_faces > 0
                        self.latest_data["face_count"] = n_faces
                        self.latest_data["face_center_x"] = fc_x
                        self.latest_data["face_center_y"] = fc_y

                    # Mode 5: 检测到人脸时触发接近
                    if n_faces > 0:
                        self._handle_mode5_face(n_faces, fc_x, fc_y, face_dist)

                results = hands.process(img_rgb)

                current = ""
                wrist_px = None

                if results.multi_hand_landmarks and results.multi_handedness:
                    hl = results.multi_hand_landmarks[0]
                    hd = results.multi_handedness[0].classification[0].label
                    current = classify_gesture(hl.landmark, hd)
                    wrist_lm = hl.landmark[0]
                    wrist_px = (int(wrist_lm.x * w), int(wrist_lm.y * h))

                # ---- 每帧更新共享数据 ----
                hand_ok = current != "" and current != "unknown"
                if hand_ok and wrist_px is not None:
                    px, py = wrist_px
                    if 0 <= px < w and 0 <= py < h:
                        dist_raw = depth_frame.get_distance(px, py)
                        x_off = (px - w / 2.0) / (w / 2.0)
                        y_off = (py - h / 2.0) / (h / 2.0)
                        with self.data_lock:
                            self.latest_data["distance"] = dist_raw
                            self.latest_data["x_offset"] = x_off
                            self.latest_data["y_offset"] = y_off
                            self.latest_data["gesture"] = current
                            self.latest_data["valid"] = dist_raw > 0
                        self.follow_lost_frames = 0
                    else:
                        self.follow_lost_frames += 1
                else:
                    self.follow_lost_frames += 1
                    if self.follow_lost_frames > self.follow_lost_limit:
                        self._stop_motion()
                    with self.data_lock:
                        self.latest_data["valid"] = False

                # ---- 防抖 + 触发 ----
                if current and current != "unknown":
                    if current == last_gesture:
                        stable_count += 1
                        if stable_count == STABLE:
                            mode_info = self.MODE_NAMES[self.current_mode]
                            print(f"  ✋ [{mode_info['name']}] {current}")

                            # fist 时显示距离和位置信息
                            if current == "fist" and wrist_px is not None:
                                px, py = wrist_px
                                if 0 <= px < w and 0 <= py < h:
                                    d = depth_frame.get_distance(px, py)
                                    if d > 0:
                                        with self.data_lock:
                                            xo = self.latest_data["x_offset"]
                                            yo = self.latest_data["y_offset"]
                                        centered = "✅中央" if (abs(xo) < self.approach_center_threshold and abs(yo) < self.approach_center_threshold) else "⬅️非中央"
                                        print(f"  📏 距离:{d:.2f}m | 偏心:x={xo:+.2f} y={yo:+.2f} | {centered}")

                            self._on_gesture(current)
                    else:
                        last_gesture = current
                        stable_count = 1
                else:
                    last_gesture = ""
                    stable_count = 0

                time.sleep(0.03)

        except Exception as e:
            print(f"[ERROR] _gesture_loop 异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if pipeline is not None:
                try:
                    pipeline.stop()
                except Exception:
                    pass
            if hands is not None:
                try:
                    hands.close()
                except Exception:
                    pass

    # ==================== 运动控制计算 ====================

    def _compute_follow_cmd(self):
        """Mode 2: 跟随速度计算 (增强转向锁定)"""
        with self.data_lock:
            dist = self.latest_data["distance"]
            x_off = self.latest_data["x_offset"]
            y_off = self.latest_data.get("y_offset", 0.0)
            valid = self.latest_data["valid"]

        if not valid or not self.follow_active:
            return 0.0, 0.0, 0.0

        # ---- 距离修正: 目标 0.7m ----
        dist_err = dist - self.follow_target_dist
        kp = 2.0
        target_vx = np.clip(dist_err * kp,
                           -self.follow_max_vx * 0.5,
                            self.follow_max_vx)
        if abs(dist_err) < self.follow_arrive_threshold:
            target_vx *= 0.3

        # ---- 横移: x偏移 → 左右平移 ----
        target_vy = -x_off * self.follow_max_vy

        # ---- 转向增强: x偏移为主 + y偏移辅助 ----
        # 系数从 0.4 提升到 1.2，让机器人更快转向锁定目标
        target_wz = (-x_off * self.follow_max_wz * 1.0 -
                     y_off * self.follow_max_wz * 0.15)
        return target_vx, target_vy, target_wz

    # ==================== 主循环 ====================

    def run(self):
        # SIGTERM → 优雅停止：置 running=False。主循环 50ms select 内退出；
        # _gesture_loop 的 while 退出后 finally 执行 pipeline.stop() 干净释放相机
        def _on_sigterm(*_):
            self.running = False
        signal.signal(signal.SIGTERM, _on_sigterm)

        gesture_thread = threading.Thread(target=self._gesture_loop, daemon=True)
        self.gesture_thread = gesture_thread
        gesture_thread.start()

        # 支持 TTY 交互模式 与 非TTY 子进程模式 (例如 Web 端通过 stdin 发送按键)
        old_settings = None
        if self.is_tty:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
        else:
            # 非交互模式: 让 stdout 行缓冲 (终端行模式输出更可读)
            try:
                sys.stdout.reconfigure(line_buffering=True)
            except Exception:
                pass
        try:
            if self.is_tty:
                print("\n🚀 已启动 (Mode1), 按 R 开始识别, 1-5 切换模式\n")
            else:
                print("\n🚀 已启动 (Mode1) [子进程模式 - 等待 Web 端按键输入]\n")

            while self.running:
                # ---- 键盘输入 ----
                if select.select([sys.stdin], [], [], 0.05)[0]:
                    key = sys.stdin.read(1)

                    if key == '\x03' or key.lower() == 'q':
                        break

                    elif key.lower() == 'r':
                        self.gesture_active = not self.gesture_active
                        status = "▶️ 已启动" if self.gesture_active else "⏸️ 已暂停"
                        mode_info = self.MODE_NAMES[self.current_mode]
                        print(f"\n  {status} | {mode_info['name']}")

                    elif key == '1':
                        self._stop_motion()
                        self.current_mode = 1
                        self.last_action_gesture = ""
                        print(f"\n  🔀 → Mode1: {self.MODE_NAMES[1]['desc']}")

                    elif key == '2':
                        self._stop_motion()
                        self.current_mode = 2
                        self.last_action_gesture = ""
                        print(f"\n  🔀 → Mode2: {self.MODE_NAMES[2]['desc']}")

                    elif key == '3':
                        self._stop_motion()
                        self.current_mode = 3
                        self.last_action_gesture = ""
                        self.approach_state = "idle"
                        self.approach_arrived_count = 0
                        print(f"\n  🔀 → Mode3: {self.MODE_NAMES[3]['desc']}")

                    elif key == '4':
                        self._stop_motion()
                        self.current_mode = 4
                        self.last_action_gesture = ""
                        self.nav_busy = False
                        print(f"\n  🔀 → Mode4: {self.MODE_NAMES[4]['desc']}")

                    elif key == '5':
                        self._stop_motion()
                        self.current_mode = 5
                        self.last_action_gesture = ""
                        self.face_greet_state = "idle"
                        self.face_greet_arrived_count = 0
                        print(f"\n  🔀 → Mode5: {self.MODE_NAMES[5]['desc']}")

                # ---- 运动控制 (Mode 2 跟随 或 Mode 3 接近) ----
                if self.gesture_active and self.sport_client is not None:
                    if self.current_mode == 2 and self.follow_active:
                        tvx, tvy, twz = self._compute_follow_cmd()
                        s = self.follow_smoothing
                        self.follow_send_vx += (tvx - self.follow_send_vx) * s
                        self.follow_send_vy += (tvy - self.follow_send_vy) * s
                        self.follow_send_wz += (twz - self.follow_send_wz) * s
                        stop_t = 0.02
                        if (abs(self.follow_send_vx) < stop_t and
                                abs(self.follow_send_vy) < stop_t and
                                abs(self.follow_send_wz) < stop_t):
                            self.sport_client.StopMove()
                        else:
                            self.sport_client.Move(
                                self.follow_send_vx,
                                self.follow_send_vy,
                                self.follow_send_wz)

                    elif self.current_mode == 3 and self.approach_state == "adjusting":
                        tvx, tvy, twz = self._compute_approach_cmd()
                        s = self.approach_smoothing
                        self.approach_send_vx += (tvx - self.approach_send_vx) * s
                        self.approach_send_vy += (tvy - self.approach_send_vy) * s
                        self.approach_send_wz += (twz - self.approach_send_wz) * s
                        stop_t = 0.02
                        if (abs(self.approach_send_vx) < stop_t and
                                abs(self.approach_send_vy) < stop_t and
                                abs(self.approach_send_wz) < stop_t):
                            self.sport_client.StopMove()
                        else:
                            self.sport_client.Move(
                                self.approach_send_vx,
                                self.approach_send_vy,
                                self.approach_send_wz)

                    elif self.current_mode == 5 and self.face_greet_state in ("approaching", "centering"):
                        tvx, tvy, twz = self._compute_face_greet_cmd()
                        s = self.face_greet_smoothing
                        self.face_greet_send_vx += (tvx - self.face_greet_send_vx) * s
                        self.face_greet_send_vy += (tvy - self.face_greet_send_vy) * s
                        self.face_greet_send_wz += (twz - self.face_greet_send_wz) * s
                        stop_t = 0.02
                        if (abs(self.face_greet_send_vx) < stop_t and
                                abs(self.face_greet_send_vy) < stop_t and
                                abs(self.face_greet_send_wz) < stop_t):
                            self.sport_client.StopMove()
                        else:
                            self.sport_client.Move(
                                self.face_greet_send_vx,
                                self.face_greet_send_vy,
                                self.face_greet_send_wz)

                # ---- 状态行 ----
                status_tag = "运行中" if self.gesture_active else "已暂停"
                mode_info = self.MODE_NAMES[self.current_mode]
                arm_s = "执行中" if self.arm_busy else "空闲"
                extra = ""
                if self.current_mode == 2 and self.follow_active:
                    with self.data_lock:
                        d = self.latest_data["distance"]
                    extra = f" | 🚶{d:.2f}m"
                elif self.current_mode == 3 and self.approach_state == "adjusting":
                    with self.data_lock:
                        d = self.latest_data["distance"]
                        xo = self.latest_data["x_offset"]
                        yo = self.latest_data["y_offset"]
                    dist_ok = "✅" if (self.approach_dist_min <= d <= self.approach_dist_max) else "❌"
                    pos_ok = "✅" if (abs(xo) < self.approach_center_threshold and abs(yo) < self.approach_center_threshold) else "❌"
                    extra = (f" | ⚙️调整中 距:{d:.2f}m{dist_ok}[{self.approach_dist_min}-{self.approach_dist_max}] "
                            f"偏心:x={xo:+.2f}{pos_ok} y={yo:+.2f} "
                            f"({self.approach_arrived_count}/{self.approach_arrived_need})")
                elif self.current_mode == 3 and self.approach_state == "arrived":
                    extra = " | 🤝已完成!"
                elif self.current_mode == 4:
                    extra = f" | {'🧭执行中' if self.nav_busy else '待命'}"
                elif self.current_mode == 5:
                    with self.data_lock:
                        fc = self.latest_data["face_count"]
                        fd = self.latest_data["face_detected"]
                    state_map = {"idle": "等待人脸", "approaching": "接近中",
                                 "centering": "居中中", "greeting": "问候中", "done": "✅完成"}
                    gs = state_map.get(self.face_greet_state, self.face_greet_state)
                    extra = (f" | 👤{fc}张脸 {gs}"
                             f" ({self.face_greet_arrived_count}/{self.face_greet_arrived_need})")

                status_line = (
                    f"[{status_tag}] "
                    f"M{self.current_mode}:{mode_info['name']:<6} | "
                    f"上次:{self.last_action_gesture or '-':<8} | "
                    f"手臂:{arm_s}"
                    f"{extra} | "
                    f"1/2/3/4/5切换 R=启停 Q=退出"
                )
                if self.is_tty:
                    # 交互模式: 行内刷新
                    print(f"\r  {status_line}  ", end="", flush=True)
                else:
                    # 子进程模式: 节流到 1Hz 输出独立行 (便于 Web 日志显示)
                    now_ts = time.time()
                    if now_ts - self._last_status_ts >= 1.0:
                        self._last_status_ts = now_ts
                        print(status_line, flush=True)

        except Exception as e:
            print(f"\n  [ERROR] {e}")
        finally:
            if old_settings is not None:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self.running = False
            # 等 gesture 线程退出并执行 pipeline.stop()，避免 daemon 被进程退出
            # 强杀导致 uvcvideo 不释放相机 (errno=16 EBUSY)
            gt = getattr(self, "gesture_thread", None)
            if gt is not None:
                try:
                    gt.join(timeout=8.0)
                except Exception:
                    pass
            self._stop_motion()
            if self.arm_client:
                try:
                    self.arm_client.ExecuteAction(action_map.get("release arm"))
                except Exception:
                    pass
            print("\n\n👋 已退出。")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3.8 g1_gesture_control.py <网卡接口>")
        print("示例: python3.8 g1_gesture_control.py enp2s0")
        sys.exit(-1)

    ctrl = GestureControl(sys.argv[1])
    ctrl.run()

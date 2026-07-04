#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G1 人脸问候 - 拍照 → 百度识别 → 挥手 + 语音播报姓名

用法:
    python3.8 g1_face_greet.py eth0

流程:
    1. RealSense D435i 拍照
    2. 发送百度 API 识别人名
    3. 执行挥手动作 (high wave)
    4. 语音播报 "你好，{姓名}！"
"""

import os

# ===== 无GUI环境防崩溃 =====
os.environ["DISPLAY"] = ":0"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["GDK_BACKEND"] = ""
os.environ["MPLBACKEND"] = "Agg"

import warnings
warnings.filterwarnings("ignore", message=".*Gdk.*")
warnings.filterwarnings("ignore", message=".*Gtk.*")
warnings.filterwarnings("ignore", message=".*display.*")

import sys
import time
import threading

import cv2
import numpy as np
import pyrealsense2 as rs
import base64
import requests
import json

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient


# ========== 百度人脸识别配置 ==========
BAIDU_API_KEY = "yXbancvADClsW0ZoE6gqdy2Y"
BAIDU_SECRET_KEY = "y5doRgpAogar093deVDvmji9a6WmPEZE"
BAIDU_GROUP_ID = "g1_users_normal"

# 缓存 token（有效期约30天，无需反复获取）
_cached_token = None

USER_ID_TO_NAME = {
    "1": "卓",
    "2": "徐总",
    "3": "张主管",
    "4": "赵工",
    "harry": "哈利",
    "tangweixing": "唐伟兴",
}


def get_baidu_access_token():
    """获取百度 Access Token（带缓存，只获取一次）"""
    global _cached_token
    if _cached_token:
        return _cached_token
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials",
              "client_id": BAIDU_API_KEY,
              "client_secret": BAIDU_SECRET_KEY}
    try:
        resp = requests.post(url, params=params)
        _cached_token = str(resp.json().get("access_token"))
        return _cached_token
    except Exception as e:
        print(f"获取百度 token 失败: {e}")
        return None


def recognize_face_baidu(image):
    """
    发送图片到百度人脸识别 API，返回人名或 None
    image: numpy array (BGR)，完整画面（百度自带人脸检测）
    """
    token = get_baidu_access_token()
    if not token:
        return None

    # 编码图片为 base64
    _, buf = cv2.imencode('.jpg', image)
    img_base64 = base64.b64encode(buf).decode('utf8')

    url = f"https://aip.baidubce.com/rest/2.0/face/v3/search?access_token={token}"
    payload = json.dumps({
        "group_id_list": BAIDU_GROUP_ID,
        "image": img_base64,
        "image_type": "BASE64",
    }, ensure_ascii=False)

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    # QPS 限制时自动重试（最多3次）
    for attempt in range(3):
        try:
            resp = requests.post(url, headers=headers, data=payload.encode("utf-8"))
            result = json.loads(resp.text)
            err_code = result.get("error_code", 0)

            if err_code == 17 or err_code == 18:
                wait = 1.5 * (attempt + 1)
                print(f"⏳ QPS 限制，等待 {wait:.1f}s 后重试 ({attempt+1}/3)...")
                time.sleep(wait)
                continue

            if err_code == 0:
                user_id = result["result"]["user_list"][0]["user_id"]
                name = USER_ID_TO_NAME.get(user_id, f"未知用户({user_id})")
                return name
            else:
                print(f"百度识别失败: {result.get('error_msg')}")
                return None
        except Exception as e:
            print(f"百度识别异常: {e}")
            return None

    print("❌ QPS 限制重试耗尽")
    return None


def capture_photo_realsense():
    """使用 RealSense D435i 深度相机拍照一张，返回 numpy array 或 None"""
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    try:
        pipeline.start(config)
        # 等几帧让相机稳定
        for _ in range(10):
            frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()

        if not color_frame:
            print("❌ 无法获取彩色帧")
            return None

        img = np.asanyarray(color_frame.get_data())
        return img

    except RuntimeError as e:
        print(f"❌ 相机帧超时: {e}")
        return None
    except Exception as e:
        print(f"❌ 拍照失败: {e}")
        return None
    finally:
        try:
            pipeline.stop()
        except Exception:
            pass


# ========== 主类 ==========

class FaceGreet:

    def __init__(self, network_interface):
        print("=" * 55)
        print("   G1 人脸问候 (拍照→识别→挥手+语音)")
        print("=" * 55)

        # ---- 网络初始化 ----
        try:
            ChannelFactoryInitialize(0, network_interface)
            print(f"✅ 网络已连接: {network_interface}")
        except Exception as e:
            print(f"❌ 网络初始化失败: {e}")
            sys.exit(-1)

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

        # ---- 状态 ----
        self.running = True
        self.arm_busy = False
        self.arm_lock = threading.Lock()

        # ---- 循环间隔 ----
        self.loop_interval = 3.0   # 每次循环间隔秒数（避免频繁调用百度API）

    # ==================== 机械臂 ====================

    def _execute_wave(self):
        """执行挥手动作 (high wave → 等待 → release arm)"""
        if self.arm_client is None:
            print("  ❌ 机械臂未就绪")
            return
        with self.arm_lock:
            if self.arm_busy:
                return
            self.arm_busy = True

        def _run():
            try:
                print("\n  🤖 执行: 挥手 (high wave)")
                self.arm_client.ExecuteAction(action_map.get("high wave"))
                time.sleep(2.0)
                self.arm_client.ExecuteAction(action_map.get("release arm"))
                print("  ✅ 挥手完成 + 手臂已复位")
            except Exception as e:
                print(f"  ❌ 动作失败: {e}")
            finally:
                with self.arm_lock:
                    self.arm_busy = False

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    # ==================== 语音播报 ====================

    def _speak(self, text):
        """使用 AudioClient.TtsMaker 播报语音"""
        if self.audio_client is not None:
            try:
                self.audio_client.TtsMaker(text, 0)
                print(f"  🔊 语音已发送: {text}")
            except Exception as e:
                print(f"  ⚠️ 语音失败: {e}")

    # ==================== 主循环 ====================

    def run(self):
        print("\n🚀 开始运行! (按 Ctrl+C 退出)\n")

        while self.running:
            print("-" * 45)
            print("📷 正在拍照...")

            # 1. 拍照
            img = capture_photo_realsense()
            if img is None:
                print("⚠️  拍照失败，稍后重试...")
                time.sleep(self.loop_interval)
                continue

            print("✅  拍照成功，正在调用百度识别...")

            # 2. 百度识别
            name = recognize_face_baidu(img)
            if not name:
                print("❌  识别失败，稍后重试...\n")
                time.sleep(self.loop_interval)
                continue

            greeting = f"你好，{name}！"
            print(f"\n🎉 识别成功: {name}")
            print(f"👋  执行挥手 + 🔊 语音: {greeting}\n")

            # 3. 挥手
            self._execute_wave()

            # 4. 语音播报
            self._speak(greeting)

            # 等待动作完成后再进入下一轮
            time.sleep(self.loop_interval)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 g1_face_greet.py <network_interface>")
        print("Example: python3.8 g1_face_greet.py eth0")
        sys.exit(-1)

    app = FaceGreet(sys.argv[1])
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 已退出")

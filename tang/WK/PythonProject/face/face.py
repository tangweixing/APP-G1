import base64
import urllib
import requests
import json
import cv2  # 用于访问摄像头
import os  # 用于文件操作
import numpy as np
import sys

# 尝试导入 RealSense (G1 机器人使用 D435i 深度相机)
try:
    import pyrealsense2 as rs
    HAS_REALSENSE = True
except ImportError:
    HAS_REALSENSE = False

# 尝试导入 G1 语音客户端
try:
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize
    from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
    HAS_AUDIO_CLIENT = True
except ImportError:
    HAS_AUDIO_CLIENT = False
#百度云的API服务
API_KEY = "yXbancvADClsW0ZoE6gqdy2Y"
SECRET_KEY = "y5doRgpAogar093deVDvmji9a6WmPEZE"
PHOTO_PATH = "captured_face.jpg"  # 拍摄的照片保存路径

# 添加用户ID与人名的映射字典
USER_ID_TO_NAME = {
    "1": "卓",
    "2": "徐总",
    "3": "张主管",
    "4": "赵工",
    "harry": "哈利",
    "tangweixing": "唐伟兴",
    # 可以根据需要继续添加更多用户ID和对应的人名
}

# 全局语音客户端
_audio_client = None


def speak_text(text):
    """让G1机器人说话 (优先使用 AudioClient.TtsMaker)"""
    if HAS_AUDIO_CLIENT and _audio_client is not None:
        try:
            _audio_client.TtsMaker(text, 0)
            print(f"[语音输出] {text}")
            return
        except Exception as e:
            print(f"TtsMaker 失败: {e}, 尝试 espeak...")
    # 回退: espeak
    try:
        import subprocess
        subprocess.run(['espeak', '-v', 'zh', f'"{text}"'], capture_output=True, check=True)
        print(f"[语音输出] {text}")
    except Exception as e:
        print(f"语音输出失败: {e}")


def capture_photo():
    """调用摄像头拍摄一张照片并保存 (优先使用 RealSense D435i)"""
    if HAS_REALSENSE:
        return _capture_photo_realsense()
    else:
        return _capture_photo_opencv()


def _kill_camera_occupants():
    """清理占用 RealSense 相机的进程（Web 端人脸/手势识别等）"""
    import subprocess
    import time

    killed = []

    # 1. pkill 已知的占用脚本 (Web 端人脸识别 / 手势识别)
    for script in ['g1_face_greet.py', 'g1_gesture_control.py']:
        try:
            # 先 SIGTERM 优雅退出
            result = subprocess.run(
                ['pkill', '-f', script],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                killed.append(script)
        except Exception:
            pass

    # 2. 杀死所有占用 /dev/video* 的进程 (兜底)
    try:
        subprocess.run(
            ['fuser', '-k', '/dev/video*'],
            capture_output=True, text=True
        )
    except Exception:
        pass

    if killed:
        print(f"🛑 已停止占用相机的进程: {', '.join(killed)}")
        time.sleep(2.0)  # 给系统时间释放相机

        # 如果还存活, 强制 SIGKILL
        for script in killed:
            try:
                subprocess.run(
                    ['pkill', '-9', '-f', script],
                    capture_output=True, text=True
                )
            except Exception:
                pass
        time.sleep(1.0)  # 再等待 1 秒
    else:
        time.sleep(0.5)


def _capture_photo_realsense():
    """使用 RealSense D435i 深度相机拍照 (带重试机制)"""
    import time

    # 最多重试 3 次
    for attempt in range(1, 4):
        if _try_capture_realsense():
            return True

        if attempt < 3:
            print(f"⚠️ 第 {attempt} 次拍照失败, 尝试清理占用相机的进程后重试...")
            _kill_camera_occupants()
            time.sleep(0.5)
        else:
            print(f"❌ 第 {attempt} 次拍照仍失败, 放弃")

    return False


def _try_capture_realsense():
    """实际执行 RealSense 拍照"""
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    started = False

    try:
        pipeline.start(config)
        started = True
        # 等待一帧
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()

        if not color_frame:
            print("RealSense: 无法获取彩色帧")
            return False

        img = np.asanyarray(color_frame.get_data())
        cv2.imwrite(PHOTO_PATH, img)
        return True

    except Exception as e:
        print(f"RealSense 拍照失败: {e}")
        return False
    finally:
        # 只有 start 成功后才调用 stop，否则会抛出
        # "stop() cannot be called before start()"
        if started:
            try:
                pipeline.stop()
            except Exception:
                pass


def _capture_photo_opencv():
    """回退: 使用 OpenCV 默认摄像头拍照"""
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("无法打开摄像头")
        return False

    ret, frame = cap.read()

    if ret:
        cv2.imwrite(PHOTO_PATH, frame)
    else:
        print("拍摄失败")
        return False

    cap.release()
    return True


def main():
    global _audio_client

    # ---- 网络初始化 & 语音客户端 ----
    if HAS_AUDIO_CLIENT and len(sys.argv) >= 2:
        network_interface = sys.argv[1]
        try:
            ChannelFactoryInitialize(0, network_interface)
            print(f"✅ 网络已连接: {network_interface}")
        except Exception as e:
            print(f"⚠️ 网络初始化失败: {e} (语音功能不可用)")

        _audio_client = AudioClient()
        _audio_client.SetTimeout(10.0)
        try:
            _audio_client.Init()
            print("✅ 语音客户端就绪")
        except Exception as e:
            print(f"⚠️ 语音客户端失败: {e}")
            _audio_client = None
    else:
        if not HAS_AUDIO_CLIENT:
            print("⚠️ 未安装 unitree_sdk2py, 语音功能不可用")
        else:
            print("⚠️ 未指定网卡接口, 用法: python3.8 face.py <网卡接口> (如 eth0)")
            print("   语音功能不可用, 仅拍照+人脸识别")

    # 先调用摄像头拍摄照片
    if not capture_photo():
        print("拍摄照片失败，程序退出")
        return

    # 检查照片是否存在
    if not os.path.exists(PHOTO_PATH):
        print(f"照片文件不存在: {PHOTO_PATH}")
        return

    url = "https://aip.baidubce.com/rest/2.0/face/v3/search?access_token=" + get_access_token()

    # 获取拍摄照片的base64编码
    image_base64 = get_file_content_as_base64(PHOTO_PATH, False)

    payload = json.dumps({
        "group_id_list": "g1_users_normal",
        "image": image_base64,  # 使用拍摄的照片
    "image_type": "BASE64"
    # "scene": "LIVE"  # 添加场景类型
    }, ensure_ascii=False)

    # 添加请求头
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))

    # print("识别结果：")
    # print(response.text)

    # 解析响应并输出对应的人名
    try:
        result = json.loads(response.text)
        if result.get("error_code") == 0:
            # 获取识别到的user_id
            user_id = result["result"]["user_list"][0]["user_id"]
            # 获取对应的人名，如果没有则显示未知
            user_name = USER_ID_TO_NAME.get(user_id, f"未知用户（ID: {user_id}）")
            greeting = f"你好，{user_name}！"
            print(greeting)
            speak_text(greeting)  # 调用语音输出
        else:
            print(f"识别失败: {result.get('error_msg')}")
    except Exception as e:
        print(f"解析识别结果失败: {e}")


def get_file_content_as_base64(path, urlencoded=False):
    """获取文件base64编码"""
    with open(path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf8")
        if urlencoded:
            content = urllib.parse.quote_plus(content)
    return content


def get_access_token():
    """使用 AK，SK 生成鉴权签名（Access Token）"""
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    try:
        response = requests.post(url, params=params)
        return str(response.json().get("access_token"))
    except Exception as e:
        print(f"获取access_token失败: {e}")
        return None


if __name__ == '__main__':
    main()

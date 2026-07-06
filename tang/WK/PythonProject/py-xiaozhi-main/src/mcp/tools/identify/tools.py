from typing import List, Dict, Tuple, Set, Union, Optional
import subprocess
import logging
import sys
import time
import glob
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def _get_network_interface() -> str:
    """获取网络接口名称 (优先从 py-xiaozhi 启动参数获取, 回退 eth0)"""
    # 1. 从 py-xiaozhi 主程序启动参数获取
    for i, arg in enumerate(sys.argv):
        if arg.startswith("eth") or arg.startswith("en") or arg.startswith("wlan"):
            return arg
    # 2. 回退到默认网卡
    return "eth0"


def _kill_camera_occupants():
    """在调用 face.py 之前清理占用 RealSense 相机的进程。

    Web 端的 g1_face_greet.py / g1_gesture_control.py 子进程会持续占用
    RealSense D435i, 导致 face.py 启动后 wait_for_frames 超时
    ("Frame didn't arrive within 5000")。这里在子进程启动前先释放相机。
    """
    killed = []

    # 1. SIGTERM 已知占用脚本 (Web 端人脸识别 / 手势识别)
    for script in ['g1_face_greet.py', 'g1_gesture_control.py']:
        try:
            result = subprocess.run(
                ['pkill', '-f', script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                killed.append(script)
        except Exception as e:
            logger.debug(f"pkill {script} 异常: {e}")

    # 2. 兜底: 杀死所有占用 /dev/video* 的进程
    # 注意: fuser 不支持 shell glob, 必须列出具体设备
    video_devices = glob.glob('/dev/video*')
    if video_devices:
        try:
            subprocess.run(
                ['fuser', '-k'] + video_devices,
                capture_output=True, text=True, timeout=5
            )
        except Exception as e:
            logger.debug(f"fuser 异常: {e}")

    if killed:
        logger.info(f"已停止占用相机的进程: {', '.join(killed)}")
        # 给系统时间释放 USB 设备
        time.sleep(2.0)
        # 强制 SIGKILL 残留进程
        for script in killed:
            try:
                subprocess.run(
                    ['pkill', '-9', '-f', script],
                    capture_output=True, text=True, timeout=5
                )
            except Exception:
                pass
        time.sleep(1.0)
    else:
        time.sleep(0.3)


async def identify_function(args: dict) -> str:
    """
    响应“我是谁”“认识我”指令，调用face.py脚本执行身份识别
    :param args: 工具调用参数（无参数）
    :return: 执行结果文本
    """
    try:
        # 指定Python解释器和脚本路径
        python_path = r"/usr/bin/python3"
        script_path = r"/home/unitree/tang/WK/PythonProject/face/face.py"
        network_interface = _get_network_interface()

        logger.info(f"身份识别: 使用网络接口 {network_interface}")

        # 先清理占用相机的进程, 确保 face.py 启动时相机空闲
        # (face.py 内部也会再做一次清理, 这里是双重保险)
        _kill_camera_occupants()

        # 执行脚本（传入网卡接口参数, 启用语音）
        result = subprocess.run(
            [python_path, script_path, network_interface],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="ignore",
            timeout=45  # 加长到 45 秒, 因为前置清理 + 相机预热会多耗几秒
        )

        # 打印并记录输出
        print(f"[{script_path} 输出] {result.stdout.strip()}")
        logger.info(f"身份识别脚本执行输出: {result.stdout.strip()}")

        # 构造返回结果
        output = result.stdout.strip() or "身份识别操作执行成功（无输出）"
        return f"已执行身份识别：{output}"

    except subprocess.CalledProcessError as e:
        error_msg = f"脚本执行失败（状态码：{e.returncode}）：{e.stderr.strip()}"
        logger.error(error_msg)
        return error_msg
    except subprocess.TimeoutExpired:
        error_msg = "身份识别超时（30秒），可能相机被占用或网络异常"
        logger.error(error_msg)
        return error_msg
    except FileNotFoundError:
        error_msg = f"未找到文件，请检查路径：Python={python_path}，脚本={script_path}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"身份识别工具异常：{str(e)}"
        logger.error(error_msg)
        return error_msg

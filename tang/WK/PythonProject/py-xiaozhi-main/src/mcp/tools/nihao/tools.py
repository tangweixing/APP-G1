from typing import List, Dict, Tuple, Set, Union, Optional
import subprocess
import logging
from src.utils.logging_config import get_logger

# 初始化日志记录器
logger = get_logger(__name__)

# 指定Python解释器路径
python_path = r"/usr/bin/python3"


async def hello_function(args: dict) -> str:
    """
    运行机械臂动作脚本和面部识别脚本
    :param args: 工具调用参数（本工具无需参数，为空字典）
    :return: 执行结果文本（成功/失败信息）
    """
    try:
        # 脚本路径
        arm_script_path = r"/home/unitree/tang/WK/unitree_sdk2_python/example/g1/high_level/g1_arm_action_example.py"
        face_script_path = r"/home/harry/unitree/WK/face/face.py"

        # 网络接口（保持与机器人配置一致）
        network_interface = "eth0"

        # 动作ID：6 对应“你好”
        action_id = "6"

        # 先运行机械臂动作脚本
        logger.info(f"开始执行机械臂动作脚本: {arm_script_path}")
        arm_result = subprocess.run(
            [python_path, arm_script_path, network_interface, action_id],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="ignore"
        )

        # 打印并记录机械臂脚本输出
        arm_output = arm_result.stdout.strip()
        print(f"[{arm_script_path} 输出] {arm_output}")
        logger.info(f"机械臂动作脚本执行输出: {arm_output}")

        # 再运行面部识别脚本
        logger.info(f"开始执行面部识别脚本: {face_script_path}")
        face_result = subprocess.run(
            [python_path, face_script_path],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="ignore"
        )

        # 打印并记录面部识别脚本输出
        face_output = face_result.stdout.strip()
        print(f"[{face_script_path} 输出] {face_output}")
        logger.info(f"面部识别脚本执行输出: {face_output}")

        # 构造返回结果
        return (f"机械臂动作脚本执行成功：{arm_output or '无输出'}\n"
                f"面部识别脚本执行成功：{face_output or '无输出'}")

    except subprocess.CalledProcessError as e:
        error_msg = f"脚本执行失败（状态码：{e.returncode}）：{e.stderr.strip()}"
        logger.error(error_msg)
        return error_msg

    except FileNotFoundError as e:
        error_msg = f"未找到文件：{str(e)}"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"工具调用异常：{str(e)}"
        logger.error(error_msg)
        return error_msg

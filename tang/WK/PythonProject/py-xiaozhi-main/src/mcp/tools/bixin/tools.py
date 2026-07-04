from typing import List, Dict, Tuple, Set, Union, Optional
import subprocess
import logging
from src.utils.logging_config import get_logger

# 初始化日志记录器
logger = get_logger(__name__)


async def bixin_function(args: dict) -> str:
    """
    触发ID=2的动作（high five），拉起指定路径的g1_arm_action_example.py脚本
    :param args: 工具调用参数（本工具无需参数，为空字典）
    :return: 执行结果文本（成功/失败信息）
    """
    try:
        # 目标脚本的绝对路径（与原路径一致）
        script_path = r"/home/unitree/tang/WK/unitree_sdk2_python/example/g1/high_level/g1_arm_action_example.py"

        # 网络接口（保持与机器人配置一致）
        network_interface = "eth0"

        # 动作ID：2 对应“high five”
        action_id = "2"

        # 执行脚本并传入参数：python3 脚本路径 网络接口 动作ID
        result = subprocess.run(
            ["/usr/bin/python3", script_path, network_interface, action_id],  # 调用Python3解释器并传入参数
            capture_output=True,  # 捕获标准输出和错误输出
            text=True,  # 以文本模式处理输出
            check=True,  # 若脚本执行返回非0状态码，会抛出异常
            encoding="utf-8",  # 使用UTF-8编码解码输出
            errors="ignore"  # 忽略无法解码的字符
        )

        # 打印脚本输出到控制台
        print(f"[{script_path} 输出] {result.stdout.strip()}")

        # 记录脚本输出到日志
        logger.info(f"ID=2动作执行输出: {result.stdout.strip()}")

        # 构造返回结果
        output = result.stdout.strip() or "ID=2动作执行成功（无输出）"
        return f"ID=2动作（high five）执行成功：{output}"

    except subprocess.CalledProcessError as e:
        error_msg = f"脚本执行失败（状态码：{e.returncode}）：{e.stderr.strip()}"
        logger.error(error_msg)
        return error_msg

    except FileNotFoundError:
        error_msg = f"未找到文件，请检查路径：{script_path}"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"工具调用异常：{str(e)}"
        logger.error(error_msg)
        return error_msg

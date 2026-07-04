from typing import List, Dict, Tuple, Set, Union, Optional
import subprocess
import logging
from src.utils.logging_config import get_logger

# 初始化日志记录器
logger = get_logger(__name__)


async def handshake_function(args: dict) -> str:
    """
    触发握手动作，拉起指定路径的g1_arm_action_example.py脚本
    并传入网口参数enp7s0和动作ID 1
    :param args: 工具调用参数（本工具无需参数，为空字典）
    :return: 执行结果文本（成功/失败信息）
    """
    try:
        # 1. 关键修改：指定conda环境的python3绝对路径
        python_path = r"/usr/bin/python3"

        # 目标脚本的绝对路径（请再次确认路径是否正确，避免因路径错误导致FileNotFound）
        script_path = r"/home/unitree/tang/WK/unitree_sdk2_python/example/g1/high_level/g1_arm_action_example.py"

        # 网口参数（固定为enp7s0，与之前测试一致）
        network_interface = "eth0"

        # 动作ID（握手动作对应ID为1）
        action_id = "1"

        # 2. 执行脚本：用conda的python3解释器，传入参数
        result = subprocess.run(
            [python_path, script_path, network_interface, action_id],  # 替换为conda的python3路径
            capture_output=True,  # 捕获标准输出和错误输出
            text=True,  # 以文本模式处理输出
            check=True,  # 执行失败（非0状态码）时抛出异常
            encoding="utf-8",  # 编码格式
            errors="ignore"  # 忽略无法解码的字符
        )

        # 打印脚本输出到控制台（调试用）
        print(f"[{script_path} 输出] {result.stdout.strip()}")

        # 记录脚本输出到日志
        logger.info(f"握手动作脚本执行输出: {result.stdout.strip()}")

        # 构造返回结果
        output = result.stdout.strip() or "脚本执行成功（无输出）"
        return f"握手动作执行成功：{output}"

    except subprocess.CalledProcessError as e:
        # 脚本执行返回非0状态码（执行出错）
        error_msg = f"脚本执行失败（状态码：{e.returncode}）：{e.stderr.strip()}"
        logger.error(error_msg)
        return error_msg

    except FileNotFoundError:
        # 未找到python解释器或脚本文件（重点检查两个路径）
        error_msg = f"未找到文件：请确认 python路径[{python_path}] 和 脚本路径[{script_path}] 是否正确"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        # 其他未知异常
        error_msg = f"工具调用异常：{str(e)}"
        logger.error(error_msg)
        return error_msg

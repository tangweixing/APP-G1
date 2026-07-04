from typing import List, Dict, Tuple, Set, Union, Optional
import subprocess
import logging
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


async def hug_function(args: dict) -> str:
    """
    触发拥抱动作（ID=3），拉起指定路径的g1_arm_action_example.py脚本
    :param args: 工具调用参数（本工具无需参数，为空字典）
    :return: 执行结果文本（成功/失败信息）
    """
    try:
        # 指定Python解释器路径（使用/usr/bin/python3）
        python_path = r"/usr/bin/python3"

        # 目标脚本的绝对路径（按指定路径修改）
        script_path = r"/home/unitree/tang/WK/unitree_sdk2_python/example/g1/high_level/g1_arm_action_example.py"

        network_interface = "eth0"  # 网络接口保持不变
        action_id = "3"  # 拥抱动作对应ID=3

        # 执行脚本（使用指定的Python解释器）
        result = subprocess.run(
            [python_path, script_path, network_interface, action_id],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="ignore"
        )

        print(f"[{script_path} 输出] {result.stdout.strip()}")
        logger.info(f"拥抱动作（ID=3）执行输出: {result.stdout.strip()}")

        output = result.stdout.strip() or "拥抱动作（ID=3）执行成功（无输出）"
        return f"拥抱动作（ID=3）执行成功：{output}"

    except subprocess.CalledProcessError as e:
        error_msg = f"脚本执行失败（状态码：{e.returncode}）：{e.stderr.strip()}"
        logger.error(error_msg)
        return error_msg
    except FileNotFoundError:
        # 同时检查Python解释器和脚本路径
        error_msg = f"未找到文件：请确认Python路径[{python_path}]和脚本路径[{script_path}]是否正确"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"工具调用异常：{str(e)}"
        logger.error(error_msg)
        return error_msg

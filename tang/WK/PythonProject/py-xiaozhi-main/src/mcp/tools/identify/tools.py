from typing import List, Dict, Tuple, Set, Union, Optional
import subprocess
import logging
import sys
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

        # 执行脚本（传入网卡接口参数, 启用语音）
        result = subprocess.run(
            [python_path, script_path, network_interface],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="ignore",
            timeout=30  # 30秒超时, 避免阻塞太久
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

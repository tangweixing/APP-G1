from typing import List, Dict, Tuple, Set, Union, Optional
import subprocess
import logging
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

async def check_function(args: dict) -> str:
    """
    响应“看一下”“有什么”指令，调用指定的111.py脚本
    :param args: 工具调用参数（无参数）
    :return: 执行结果文本
    """
    try:
        # 脚本路径和Python解释器路径（按需求指定）
        python_path = r"/usr/bin/python3"
        # script_path = r"/home/zhuo/point_nav/point4.py"
        # python_path = r"/home/zhuo/miniconda3/bin/python3"
        script_path = r"/home/harry/unitree/WK/PythonProject/doubao/111.py"
        # 执行脚本（使用指定的虚拟环境Python解释器）
        result = subprocess.run(
            [python_path, script_path],  # 直接调用脚本，无需额外参数
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="ignore"
        )

        # 打印并记录脚本输出
        print(f"[{script_path} 输出] {result.stdout.strip()}")
        logger.info(f"查看脚本执行输出: {result.stdout.strip()}")

        # 构造返回结果
        output = result.stdout.strip() or "查看操作执行成功（无输出）"
        return f"已执行查看操作：{output}"

    except subprocess.CalledProcessError as e:
        error_msg = f"脚本执行失败（状态码：{e.returncode}）：{e.stderr.strip()}"
        logger.error(error_msg)
        return error_msg
    except FileNotFoundError:
        error_msg = f"未找到文件，请检查路径：Python={python_path}，脚本={script_path}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"查看工具异常：{str(e)}"
        logger.error(error_msg)
        return error_msg

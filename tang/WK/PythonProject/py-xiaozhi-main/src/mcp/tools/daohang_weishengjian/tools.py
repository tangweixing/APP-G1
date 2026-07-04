from typing import List, Dict, Tuple, Set, Union, Optional
import subprocess
import logging
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


async def toilet_function(args: dict) -> str:
    """
    响应“厕所”“卫生间”指令，调用指定脚本查询位置
    :param args: 工具调用参数（无参数）
    :return: 执行结果文本
    """
    try:
        # 固定Python解释器路径，脚本路径预留
        python_path = r"/home/zhuo/miniconda3/bin/python3"
        script_path = r"/home/zhuo/PycharmProjects/PythonProject/daohang/daohang_weishengjian.py"  # 此处预留脚本路径，需后续填充

        # 检查脚本路径是否已设置
        if not script_path.strip():
            return "错误：脚本路径未设置，请先配置厕所查询脚本路径"

        # 执行脚本
        result = subprocess.run(
            [python_path, script_path],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="ignore"
        )

        # 打印并记录输出
        print(f"[{script_path} 输出] {result.stdout.strip()}")
        logger.info(f"厕所查询脚本执行输出: {result.stdout.strip()}")

        # 构造返回结果
        output = result.stdout.strip() or "厕所查询操作执行成功（无输出）"
        return f"已查询厕所位置：{output}"

    except subprocess.CalledProcessError as e:
        error_msg = f"脚本执行失败（状态码：{e.returncode}）：{e.stderr.strip()}"
        logger.error(error_msg)
        return error_msg
    except FileNotFoundError:
        error_msg = f"未找到文件，请检查路径：Python={python_path}，脚本={script_path}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"厕所查询工具异常：{str(e)}"
        logger.error(error_msg)
        return error_msg

# import subprocess
#
# print("告诉用户你已经到达卫生间。")
#
# python_path = r"/usr/bin/python3"
# script_path = r"/home/zhuo/point_nav/123.py"
#
# if not script_path:
#     print("错误：请先填写要执行的脚本路径(script_path)")
# else:
#     try:
#         # 启动脚本并捕获输出（方便调试）
#         process = subprocess.Popen(
#             [python_path, script_path],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True
#         )
#         # 立即打印PID（证明脚本已启动）
#         print(f"脚本已启动，PID: {process.pid}，主程序即将退出")
#
#         # （调试用）等待脚本结束并打印输出（实际使用时可删除）
#         stdout, stderr = process.communicate()
#         print(f"脚本输出: {stdout}")
#         print(f"脚本错误: {stderr}")
#
#     except FileNotFoundError:
#         print(f"错误：找不到Python解释器或脚本文件，请检查路径是否正确")

import subprocess
import os
import sys

# 告诉用户正在前往卫生间
print("告诉用户你正在前往卫生间。")
sys.stdout.flush()  # 立刻刷新输出，把消息传递给小智 AI

# 定义Python解释器路径
python_path = r"/usr/bin/python3"

# 要执行的脚本路径
script_path = r"/home/zhuo/point_nav/point1.py"  # 修改成你自己的目标脚本路径

# 检查脚本路径是否已填写
if not script_path:
    print("错误：请先填写要执行的脚本路径(script_path)")
else:
    try:
        # 使用 Popen 启动外部 Python 脚本，并让它独立运行
        subprocess.Popen(
            [python_path, script_path],
            stdout=subprocess.DEVNULL,  # 不打印子程序输出
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid  # 关键：让子进程脱离父进程
        )
        # 第一个程序此处就要退出了
    except FileNotFoundError:
        print(f"错误：找不到Python解释器或脚本文件，请检查路径是否正确")



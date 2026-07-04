import os
import sys
import getpass
from win32com.client import Dispatch


def create_startup_shortcut_with_params():
    # 目标Python脚本路径
    script_path = r"C:\Users\MOREFINE\PycharmProjects\pythonProject\py-xiaozhi-main\main.py"

    # 验证脚本是否存在
    if not os.path.exists(script_path):
        print(f"错误：脚本文件不存在 - {script_path}")
        return False

    # 获取Python解释器路径
    python_exe = sys.executable

    # 命令行参数（保持你需要的--mode cli）
    arguments = f'"{script_path}" --mode cli'

    # 获取当前用户的启动文件夹路径
    username = getpass.getuser()
    startup_folder = os.path.join(
        os.environ.get('APPDATA', f"C:\\Users\\MOREFINE\\AppData\\Roaming"),
        "Microsoft\\Windows\\Start Menu\\Programs\\Startup"
    )

    # 确保启动文件夹存在
    os.makedirs(startup_folder, exist_ok=True)

    # 快捷方式名称
    shortcut_name = "xiaozhi-main.lnk"
    shortcut_path = os.path.join(startup_folder, shortcut_name)

    try:
        # 创建快捷方式
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)

        # 设置快捷方式属性（包含参数）
        shortcut.TargetPath = python_exe  # Python解释器路径
        shortcut.Arguments = arguments  # 脚本路径 + 命令行参数
        shortcut.WorkingDirectory = os.path.dirname(script_path)  # 工作目录
        shortcut.IconLocation = f"{script_path}, 0"  # 使用脚本图标

        shortcut.save()
        print(f"成功创建带参数的开机启动快捷方式：")
        print(f"路径：{shortcut_path}")
        print(f"启动命令：{python_exe} {arguments}")
        return True

    except Exception as e:
        print(f"创建快捷方式失败：{str(e)}")
        return False


if __name__ == "__main__":
    create_startup_shortcut_with_params()

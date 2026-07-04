from flask import Flask, jsonify
import subprocess
import os
import sys

app = Flask(__name__)

# 配置路径
MAIN_PY_PATH = r"C:\Users\MOREFINE\PycharmProjects\pythonProject\py-xiaozhi-main\main.py"
# 使用当前环境的Python解释器路径
PYTHON_PATH = sys.executable


@app.route('/')
def index():
    """根路径提示页面"""
    return """
    <h1>main.py执行工具</h1> 
    <p>点击下方链接执行main.py：</p>
    <a href="/run-main" style="padding:8px 16px; background:#007bff; color:white; text-decoration:none; border-radius:4px;">
        执行main.py
    </a>
    """


@app.route('/run-main', methods=['GET'])
def run_main_script():
    """运行main.py并返回详细结果"""
    # 检查文件是否存在
    if not os.path.exists(MAIN_PY_PATH):
        return jsonify({
            "error": "文件不存在",
            "details": f"找不到指定路径的文件: {MAIN_PY_PATH}"
        }), 404

    # 检查文件是否可执行
    if not os.access(MAIN_PY_PATH, os.R_OK):
        return jsonify({
            "error": "权限不足",
            "details": f"没有读取/执行文件的权限: {MAIN_PY_PATH}"
        }), 403

    try:
        # 运行main.py，优化参数确保输出捕获
        result = subprocess.run(
            [PYTHON_PATH, MAIN_PY_PATH],
            capture_output=True,
            text=True,
            check=True,
            shell=True,  # 在Windows环境下有助于解决路径问题
            timeout=30,  # 设置30秒超时，防止无限运行
            env=os.environ.copy()  # 继承当前环境变量
        )

        return jsonify({
            "message": "main.py执行成功",
            "python_path": PYTHON_PATH,
            "script_path": MAIN_PY_PATH,
            "stdout": result.stdout if result.stdout else "没有标准输出",
            "stderr": result.stderr if result.stderr else "没有错误输出",
            "return_code": result.returncode
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            "error": "执行超时",
            "details": f"main.py执行超过30秒未完成"
        }), 504

    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": "main.py执行出错",
            "python_path": PYTHON_PATH,
            "script_path": MAIN_PY_PATH,
            "return_code": e.returncode,
            "stdout": e.stdout if e.stdout else "没有标准输出",
            "stderr": e.stderr if e.stderr else "没有错误输出，但执行返回非零状态码"
        }), 500

    except Exception as e:
        return jsonify({
            "error": "系统错误",
            "details": f"执行过程中发生意外错误: {str(e)}",
            "python_path": PYTHON_PATH,
            "script_path": MAIN_PY_PATH
        }), 500


if __name__ == '__main__':
    # 显示更详细的启动信息
    print(f"使用Python解释器: {PYTHON_PATH}")
    print(f"目标脚本路径: {MAIN_PY_PATH}")
    app.run(debug=True)
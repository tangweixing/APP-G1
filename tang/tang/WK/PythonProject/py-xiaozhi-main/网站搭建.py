import argparse
import asyncio
import sys
import time
from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import threading
import atexit
import gc
import logging
from logging.handlers import RotatingFileHandler


# 配置日志
def setup_logging():
    handler = RotatingFileHandler('xiaozhi_ai.log', maxBytes=10000, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


logger = setup_logging()


# 模拟原代码中的一些模块
class SystemInitializer:
    async def run_initialization(self):
        # 实际应用中替换为真实的初始化逻辑
        logger.info("执行系统初始化...")
        await asyncio.sleep(1)  # 模拟异步操作
        return {
            "success": True,
            "activation_version": "v2",
            "need_activation_ui": True
        }


class CLIActivation:
    def __init__(self, initializer):
        self.initializer = initializer

    async def run_activation_process(self):
        # 实际应用中替换为真实的CLI激活逻辑
        logger.info("执行CLI激活流程...")
        await asyncio.sleep(1)  # 模拟异步操作
        return True


class Application:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def run(self, mode, protocol):
        logger.info(f"应用以{mode}模式，{protocol}协议运行")
        # 实际应用中替换为真实的应用运行逻辑
        await asyncio.sleep(0.1)
        return 0


# 创建Flask应用
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 用于会话管理
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# 全局事件循环
loop = asyncio.get_event_loop()


# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description="小智Ai客户端 (Flask版)")
    parser.add_argument(
        "--mode",
        choices=["web", "cli"],
        default="web",
        help="运行模式：web(网页界面) 或 cli(命令行)",
    )
    parser.add_argument(
        "--protocol",
        choices=["mqtt", "websocket"],
        default="websocket",
        help="通信协议：mqtt 或 websocket",
    )
    parser.add_argument(
        "--skip-activation",
        action="store_true",
        help="跳过激活流程，直接启动应用（仅用于调试）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Web服务器端口，默认为5000",
    )
    return parser.parse_args()


# 处理设备激活流程
async def handle_activation(mode: str) -> bool:
    try:
        logger.info("开始设备激活流程检查...")

        # 创建SystemInitializer实例
        system_initializer = SystemInitializer()

        # 运行初始化流程
        init_result = await system_initializer.run_initialization()

        # 检查初始化是否成功
        if not init_result.get("success", False):
            logger.error(f"系统初始化失败: {init_result.get('error', '未知错误')}")
            return False

        # 获取激活版本
        activation_version = init_result.get("activation_version", "v1")
        logger.info(f"当前激活版本: {activation_version}")

        # 如果是v1协议，直接返回成功
        if activation_version == "v1":
            logger.info("v1协议：系统初始化完成，无需激活流程")
            return True

        # 如果是v2协议，检查是否需要激活界面
        if not init_result.get("need_activation_ui", False):
            logger.info("v2协议：无需显示激活界面，设备已激活")
            return True

        logger.info("v2协议：需要显示激活界面，准备激活流程")

        # 根据模式处理
        if mode == "web":
            # Web模式下，我们将在网页上处理激活
            session['activation_required'] = True
            session['system_initializer'] = system_initializer  # 注意：实际应用中可能需要序列化或使用ID引用
            return None  # 表示需要Web交互

        elif mode == "cli":
            # CLI模式
            cli_activation = CLIActivation(system_initializer)
            return await cli_activation.run_activation_process()

    except Exception as e:
        logger.error(f"激活流程异常: {e}", exc_info=True)
        return False


# 异步任务运行器
def run_async_task(coroutine):
    future = asyncio.run_coroutine_threadsafe(coroutine, loop)
    return future.result()


# 启动事件循环的线程
def start_event_loop():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()


# 启动事件循环线程
loop_thread = threading.Thread(target=start_event_loop, daemon=True)
loop_thread.start()


# Flask路由
@app.route('/')
def index():
    if 'activation_completed' in session and session['activation_completed']:
        return render_template('dashboard.html')
    elif 'activation_required' in session and session['activation_required']:
        return render_template('activation.html')
    else:
        return render_template('loading.html')


@app.route('/api/check-activation')
def check_activation():
    if 'activation_completed' in session and session['activation_completed']:
        return jsonify({"status": "completed"})
    elif 'activation_required' in session and session['activation_required']:
        return jsonify({"status": "required"})
    else:
        return jsonify({"status": "checking"})


@app.route('/api/activate', methods=['POST'])
def activate():
    # 处理激活逻辑
    data = request.json
    # 实际应用中替换为真实的激活验证
    logger.info(f"处理激活请求: {data}")

    # 模拟激活成功
    session['activation_completed'] = True
    session['activation_required'] = False
    return jsonify({"success": True})


@app.route('/api/status')
def status():
    return jsonify({
        "status": "running",
        "mode": args.mode,
        "protocol": args.protocol
    })


# 清理函数
def cleanup():
    loop.call_soon_threadsafe(loop.stop)
    loop_thread.join()
    logger.info("应用程序已关闭")


atexit.register(cleanup)


# 主函数
def main():
    global args
    args = parse_args()

    logger.info("启动小智AI客户端 (Flask版)")

    # 处理激活流程
    if not args.skip_activation:
        # 在事件循环中运行激活检查
        activation_result = run_async_task(handle_activation(args.mode))

        if args.mode == "cli":
            if not activation_result:
                logger.error("设备激活失败，程序退出")
                return 1
            else:
                logger.info("设备激活成功，启动应用程序")
                # 运行应用
                app_instance = Application.get_instance()
                return run_async_task(app_instance.run(args.mode, args.protocol))
        else:  # web模式
            if activation_result is False:
                logger.error("设备激活失败，程序退出")
                return 1
    else:
        logger.warning("跳过激活流程（调试模式）")
        session['activation_completed'] = True

    # 如果是Web模式，启动Flask服务器
    if args.mode == "web":
        logger.info(f"启动Web服务器，端口: {args.port}")
        app.run(host='0.0.0.0', port=args.port, debug=False, use_reloader=False)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        sys.exit(1)

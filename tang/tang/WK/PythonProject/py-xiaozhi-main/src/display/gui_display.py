from typing import List, Dict, Tuple, Set, Union, Optional
import os
import platform
from pathlib import Path
from typing import Callable, Optional

from PyQt5.QtCore import QObject, Qt
from PyQt5.QtGui import QFont, QMovie
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

# 根据不同操作系统处理 pynput 导入
try:
    if platform.system() == "Windows":
        from pynput import keyboard as pynput_keyboard
    elif os.environ.get("DISPLAY"):
        from pynput import keyboard as pynput_keyboard
    else:
        pynput_keyboard = None
except ImportError:
    pynput_keyboard = None

from abc import ABCMeta

from src.display.base_display import BaseDisplay
from src.utils.resource_finder import find_assets_dir


# 创建兼容的元类
class CombinedMeta(type(QObject), ABCMeta):
    pass


class GuiDisplay(BaseDisplay, QObject, metaclass=CombinedMeta):
    def __init__(self):
        super().__init__()
        QObject.__init__(self)
        self.app = None
        self.root = None

        # UI控件
        self.status_label = None
        self.emotion_label = None
        self.tts_text_label = None
        self.manual_btn = None
        self.abort_btn = None
        self.auto_btn = None
        self.mode_btn = None
        self.text_input = None
        self.send_btn = None

        # 表情管理
        self.emotion_movie = None
        self._emotion_cache = {}
        self._last_emotion_name = None

        # 状态管理
        self.auto_mode = False
        self._running = True
        self.current_status = ""
        self.is_connected = True

        # 回调函数
        self.button_press_callback = None
        self.button_release_callback = None
        self.mode_callback = None
        self.auto_callback = None
        self.abort_callback = None
        self.send_text_callback = None

        # 系统托盘组件
        self.system_tray = None

    async def set_callbacks(
        self,
        press_callback: Optional[Callable] = None,
        release_callback: Optional[Callable] = None,
        mode_callback: Optional[Callable] = None,
        auto_callback: Optional[Callable] = None,
        abort_callback: Optional[Callable] = None,
        send_text_callback: Optional[Callable] = None,
    ):
        """
        设置回调函数.
        """
        self.button_press_callback = press_callback
        self.button_release_callback = release_callback
        self.mode_callback = mode_callback
        self.auto_callback = auto_callback
        self.abort_callback = abort_callback
        self.send_text_callback = send_text_callback

        # 不再注册状态监听回调，由update_status直接处理所有逻辑

    def _on_manual_button_press(self):
        """
        手动模式按钮按下事件处理.
        """
        if self.manual_btn and self.manual_btn.isVisible():
            self.manual_btn.setText("松开以停止")
        if self.button_press_callback:
            self.button_press_callback()

    def _on_manual_button_release(self):
        """
        手动模式按钮释放事件处理.
        """
        if self.manual_btn and self.manual_btn.isVisible():
            self.manual_btn.setText("按住后说话")
        if self.button_release_callback:
            self.button_release_callback()

    def _on_auto_button_click(self):
        """
        自动模式按钮点击事件处理.
        """
        if self.auto_callback:
            self.auto_callback()

    def _on_abort_button_click(self):
        """
        处理中止按钮点击事件.
        """
        if self.abort_callback:
            self.abort_callback()

    def _on_mode_button_click(self):
        """
        对话模式切换按钮点击事件.
        """
        if self.mode_callback:
            if not self.mode_callback():
                return

        self.auto_mode = not self.auto_mode

        if self.auto_mode:
            self._update_mode_button_status("自动对话")
            self._switch_to_auto_mode()
        else:
            self._update_mode_button_status("手动对话")
            self._switch_to_manual_mode()

    def _switch_to_auto_mode(self):
        """
        切换到自动模式的UI更新.
        """
        if self.manual_btn and self.auto_btn:
            self.manual_btn.hide()
            self.auto_btn.show()

    def _switch_to_manual_mode(self):
        """
        切换到手动模式的UI更新.
        """
        if self.manual_btn and self.auto_btn:
            self.auto_btn.hide()
            self.manual_btn.show()

    async def update_status(self, status: str):
        """
        更新状态文本并处理相关逻辑.
        """
        full_status_text = f"状态: {status}"
        self._safe_update_label(self.status_label, full_status_text)

        if status != self.current_status:
            self.current_status = status

            # 根据状态更新连接状态
            self._update_connection_status(status)

            # 更新系统托盘
            self._update_system_tray(status)

    async def update_text(self, text: str):
        """
        更新TTS文本.
        """
        self._safe_update_label(self.tts_text_label, text)

    async def update_emotion(self, emotion_name: str):
        """
        更新表情显示.
        """
        if emotion_name == self._last_emotion_name:
            return

        self._last_emotion_name = emotion_name
        gif_path = self._get_emotion_gif_path(emotion_name)

        if self.emotion_label:
            try:
                self._set_emotion_gif(self.emotion_label, gif_path)
            except Exception as e:
                self.logger.error(f"设置表情GIF时发生错误: {str(e)}")

    def _get_emotion_gif_path(self, emotion_name: str) -> str:
        """
        获取表情GIF文件路径.
        """
        if emotion_name in self._emotion_cache:
            return self._emotion_cache[emotion_name]

        assets_dir = find_assets_dir()
        if not assets_dir:
            path = "😊"
        else:
            emotion_dir = assets_dir / "emojis"
            gif_file = emotion_dir / f"{emotion_name}.gif"

            if gif_file.exists():
                path = str(gif_file)
            elif (emotion_dir / "neutral.gif").exists():
                path = str(emotion_dir / "neutral.gif")
            else:
                path = "😊"

        self._emotion_cache[emotion_name] = path
        return path

    def _set_emotion_gif(self, label, gif_path):
        """
        设置表情GIF动画.
        """
        if not label:
            return

        # 如果是emoji字符串，直接设置文本
        if not gif_path.endswith(".gif"):
            label.setText(gif_path)
            return

        try:
            # 检查缓存中是否有该GIF
            if hasattr(self, "_gif_movies") and gif_path in self._gif_movies:
                movie = self._gif_movies[gif_path]
            else:
                movie = QMovie(gif_path)
                if not movie.isValid():
                    label.setText("😊")
                    return

                movie.setCacheMode(QMovie.CacheAll)

                if not hasattr(self, "_gif_movies"):
                    self._gif_movies = {}
                self._gif_movies[gif_path] = movie

            # 保存动画对象
            self.emotion_movie = movie

            # 设置标签属性
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            label.setAlignment(Qt.AlignCenter)
            label.setMovie(movie)

            # 设置动画速度并开始播放
            movie.setSpeed(105)
            movie.start()

        except Exception as e:
            self.logger.error(f"设置GIF动画失败: {e}")
            label.setText("😊")

    def _safe_update_label(self, label, text):
        """
        安全地更新标签文本.
        """
        if label:
            try:
                label.setText(text)
            except RuntimeError as e:
                self.logger.error(f"更新标签失败: {e}")

    async def close(self):
        """
        关闭窗口处理.
        """
        self._running = False
        if self.system_tray:
            self.system_tray.hide()
        if self.root:
            self.root.close()

    async def start(self):
        """
        启动GUI.
        """
        try:
            # 设置Qt环境变量
            os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.debug=false")

            self.app = QApplication.instance()
            if self.app is None:
                raise RuntimeError("QApplication未找到，请确保在qasync环境中运行")

            # 设置默认字体
            default_font = QFont()
            default_font.setPointSize(12)
            self.app.setFont(default_font)

            # 加载UI
            from PyQt5 import uic

            self.root = QWidget()
            ui_path = Path(__file__).parent / "gui_display.ui"
            uic.loadUi(str(ui_path), self.root)

            # 获取控件并连接事件
            self._init_ui_controls()
            self._connect_events()

            # 初始化系统托盘
            self._setup_system_tray()

            # 设置默认表情
            await self._set_default_emotion()

            # 显示窗口
            self.root.show()

        except Exception as e:
            self.logger.error(f"GUI启动失败: {e}", exc_info=True)
            raise

    def _init_ui_controls(self):
        """
        初始化UI控件.
        """
        self.status_label = self.root.findChild(QLabel, "status_label")
        self.emotion_label = self.root.findChild(QLabel, "emotion_label")
        self.tts_text_label = self.root.findChild(QLabel, "tts_text_label")
        self.manual_btn = self.root.findChild(QPushButton, "manual_btn")
        self.abort_btn = self.root.findChild(QPushButton, "abort_btn")
        self.auto_btn = self.root.findChild(QPushButton, "auto_btn")
        self.mode_btn = self.root.findChild(QPushButton, "mode_btn")
        self.text_input = self.root.findChild(QLineEdit, "text_input")
        self.send_btn = self.root.findChild(QPushButton, "send_btn")

    def _connect_events(self):
        """
        连接事件.
        """
        if self.manual_btn:
            self.manual_btn.pressed.connect(self._on_manual_button_press)
            self.manual_btn.released.connect(self._on_manual_button_release)
        if self.abort_btn:
            self.abort_btn.clicked.connect(self._on_abort_button_click)
        if self.auto_btn:
            self.auto_btn.clicked.connect(self._on_auto_button_click)
            self.auto_btn.hide()
        if self.mode_btn:
            self.mode_btn.clicked.connect(self._on_mode_button_click)
        if self.text_input and self.send_btn:
            self.send_btn.clicked.connect(self._on_send_button_click)
            self.text_input.returnPressed.connect(self._on_send_button_click)

        # 设置窗口关闭事件
        self.root.closeEvent = self._closeEvent

    def _setup_system_tray(self):
        """
        设置系统托盘.
        """
        try:
            from src.views.components.system_tray import SystemTray

            self.system_tray = SystemTray(self.root)
            self.system_tray.show_window_requested.connect(self._show_main_window)
            self.system_tray.settings_requested.connect(self._on_settings_button_click)
            self.system_tray.quit_requested.connect(self._quit_application)

        except Exception as e:
            self.logger.error(f"初始化系统托盘组件失败: {e}", exc_info=True)

    async def _set_default_emotion(self):
        """
        设置默认表情.
        """
        try:
            await self.update_emotion("neutral")
        except Exception as e:
            self.logger.error(f"设置默认表情失败: {e}", exc_info=True)

    def _update_system_tray(self, status):
        """
        更新系统托盘状态.
        """
        if self.system_tray:
            self.system_tray.update_status(status, self.is_connected)

    def _show_main_window(self):
        """
        显示主窗口.
        """
        if self.root:
            if self.root.isMinimized():
                self.root.showNormal()
            if not self.root.isVisible():
                self.root.show()
            self.root.activateWindow()
            self.root.raise_()

    def _quit_application(self):
        """
        退出应用程序.
        """
        self.logger.info("开始退出应用程序...")
        self._running = False

        if self.system_tray:
            self.system_tray.hide()

        try:
            from src.application import Application

            app = Application.get_instance()
            if app:
                # 异步启动关闭流程，但设置超时
                import asyncio

                from PyQt5.QtCore import QTimer

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 创建关闭任务，但不等待
                    shutdown_task = asyncio.create_task(app.shutdown())

                    # 设置超时后强制退出
                    def force_quit():
                        if not shutdown_task.done():
                            self.logger.warning("关闭超时，强制退出")
                            shutdown_task.cancel()
                        QApplication.quit()

                    # 3秒后强制退出
                    QTimer.singleShot(3000, force_quit)

                    # 当shutdown完成时正常退出
                    def on_shutdown_complete(task):
                        if not task.cancelled():
                            if task.exception():
                                self.logger.error(
                                    f"应用程序关闭异常: {task.exception()}"
                                )
                            else:
                                self.logger.info("应用程序正常关闭")
                        QApplication.quit()

                    shutdown_task.add_done_callback(on_shutdown_complete)
                else:
                    # 如果事件循环未运行，直接退出
                    QApplication.quit()
            else:
                QApplication.quit()

        except Exception as e:
            self.logger.error(f"关闭应用程序失败: {e}")
            # 异常情况下直接退出
            QApplication.quit()

    def _closeEvent(self, event):
        """
        处理窗口关闭事件.
        """
        if self.system_tray and self.system_tray.is_visible():
            self.root.hide()
            self.system_tray.show_message(
                "小智AI助手", "程序仍在运行中，点击托盘图标可以重新打开窗口。"
            )
            event.ignore()
        else:
            self._quit_application()
            event.accept()

    def _update_mode_button_status(self, text: str):
        """
        更新模式按钮状态.
        """
        if self.mode_btn:
            self.mode_btn.setText(text)

    async def update_button_status(self, text: str):
        """
        更新按钮状态.
        """
        if self.auto_mode and self.auto_btn:
            self.auto_btn.setText(text)

    def _on_send_button_click(self):
        """
        处理发送文本按钮点击事件.
        """
        if not self.text_input or not self.send_text_callback:
            return

        text = self.text_input.text().strip()
        if not text:
            return

        self.text_input.clear()

        try:
            import asyncio

            asyncio.create_task(self.send_text_callback(text))
        except Exception as e:
            self.logger.error(f"发送文本时出错: {e}")

    def _on_settings_button_click(self):
        """
        处理设置按钮点击事件.
        """
        try:
            from src.views.settings import SettingsWindow

            settings_window = SettingsWindow(self.root)
            settings_window.exec_()

        except Exception as e:
            self.logger.error(f"打开设置窗口失败: {e}", exc_info=True)

    def _update_connection_status(self, status: str):
        """
        根据状态更新连接状态.
        """
        if status in ["连接中...", "聆听中...", "说话中..."]:
            self.is_connected = True
        elif status == "待命":
            # 对于待命状态，需要检查音频通道是否真的开启
            from src.application import Application

            app = Application.get_instance()
            if app and app.protocol:
                self.is_connected = app.protocol.is_audio_channel_opened()
            else:
                self.is_connected = False
        else:
            # 其他状态（如错误状态）设为未连接
            self.is_connected = False

    async def toggle_mode(self):
        """
        切换模式.
        """
        # 调用现有的模式切换功能
        if hasattr(self, "mode_callback") and self.mode_callback:
            self._on_mode_button_click()
            self.logger.debug("通过快捷键切换了对话模式")

    async def toggle_window_visibility(self):
        """
        切换窗口可见性.
        """
        if self.root:
            if self.root.isVisible():
                self.logger.debug("通过快捷键隐藏窗口")
                self.root.hide()
            else:
                self.logger.debug("通过快捷键显示窗口")
                self.root.show()
                self.root.activateWindow()
                self.root.raise_()

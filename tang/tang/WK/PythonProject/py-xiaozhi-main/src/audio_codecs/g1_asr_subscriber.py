"""
G1 ASR订阅器 - 订阅G1机器人内置离线ASR模块的识别结果
"""
import asyncio
import json
import threading
from typing import Optional, Callable

try:
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize
    from unitree_sdk2py.idl.std_msgs.msg.dds_ import String_
    G1_SDK_AVAILABLE = True
except ImportError:
    G1_SDK_AVAILABLE = False

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class G1ASRSubscriber:
    """
    G1 ASR订阅器，接收内置离线ASR模块的识别结果
    """

    def __init__(self, network_interface="eth1"):
        """
        初始化G1 ASR订阅器
        
        Args:
            network_interface: 网络接口，默认eth1
        """
        self.network_interface = network_interface
        self.is_initialized = False
        self._is_running = False
        self._asr_callback = None
        self._subscriber_thread = None

    async def initialize(self):
        """
        初始化ASR订阅器
        """
        if not G1_SDK_AVAILABLE:
            raise ImportError("G1 SDK不可用，请确保已安装unitree_sdk2_python")
        
        try:
            # 初始化通道工厂
            ChannelFactoryInitialize(0, self.network_interface)
            self.is_initialized = True
            logger.info(f"G1 ASR订阅器初始化成功，网络接口: {self.network_interface}")
            return True
        except Exception as e:
            logger.error(f"初始化G1 ASR订阅器失败: {e}")
            raise

    async def start(self, callback: Callable[[dict], None]):
        """
        启动ASR订阅
        
        Args:
            callback: ASR消息回调函数，接收ASR消息字典
        """
        if not self.is_initialized:
            raise RuntimeError("G1 ASR订阅器未初始化")
        
        if self._is_running:
            logger.info("G1 ASR订阅已在运行中")
            return
        
        self._asr_callback = callback
        self._is_running = True
        
        # 启动订阅线程
        self._subscriber_thread = threading.Thread(
            target=self._subscribe_asr_messages,
            daemon=True
        )
        self._subscriber_thread.start()
        
        logger.info("G1 ASR订阅已启动")

    async def stop(self):
        """
        停止ASR订阅
        """
        self._is_running = False
        if self._subscriber_thread and self._subscriber_thread.is_alive():
            self._subscriber_thread.join(timeout=2.0)
        logger.info("G1 ASR订阅已停止")

    def _subscribe_asr_messages(self):
        """
        订阅ASR消息线程函数
        """
        try:
            from unitree_sdk2py.core.channel import ChannelSubscriber
            
            # 创建订阅器
            subscriber = ChannelSubscriber("rt/audio_msg", String_)
            
            def on_message(msg):
                if not self._is_running:
                    return
                
                try:
                    # 解析ASR消息
                    json_str = msg.data()
                    asr_data = json.loads(json_str)
                    
                    logger.info(f"G1 ASR识别结果: {asr_data.get('text', 'unknown')}")
                    logger.debug(f"ASR详情: {asr_data}")
                    
                    # 调用回调
                    if self._asr_callback:
                        self._asr_callback(asr_data)
                except Exception as e:
                    logger.error(f"处理ASR消息失败: {e}")
            
            # 初始化通道
            subscriber.InitChannel(on_message)
            
            # 保持线程运行
            while self._is_running:
                import time
                time.sleep(0.1)
                
        except Exception as e:
            if self._is_running:
                logger.error(f"ASR订阅失败: {e}")
        finally:
            logger.info("ASR订阅线程结束")

    def get_asr_info(self) -> dict:
        """
        获取ASR订阅器信息
        
        Returns:
            包含ASR订阅器信息的字典
        """
        return {
            "initialized": self.is_initialized,
            "running": self._is_running,
            "network_interface": self.network_interface
        }

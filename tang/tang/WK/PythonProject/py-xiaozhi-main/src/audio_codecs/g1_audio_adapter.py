"""
G1音频适配器 - 集成G1机器人的音频功能
"""
import asyncio
import numpy as np
import json
from typing import Optional, Callable
from collections import deque

try:
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize
    from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
    G1_AVAILABLE = True
except ImportError:
    G1_AVAILABLE = False

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class G1AudioAdapter:
    """
    G1音频适配器类，提供与G1机器人音频系统的接口
    """

    def __init__(self, network_interface="eth1"):
        """
        初始化G1音频适配器
        
        Args:
            network_interface: 网络接口，默认eth1
        """
        self.network_interface = network_interface
        self.audio_client = None
        self.is_initialized = False
        self.volume = 85
        
        # 录音相关
        self._recording_buffer = deque(maxlen=1000)
        self._is_recording = False
        
        # 播放相关
        self._playback_queue = asyncio.Queue(maxsize=100)
        self._is_playing = False
        
        # 回调函数
        self._audio_callback = None

    async def initialize(self):
        """
        初始化G1音频客户端
        """
        if not G1_AVAILABLE:
            raise ImportError("G1 SDK不可用，请确保已安装unitree_sdk2_python")
        
        try:
            # 初始化通道
            ChannelFactoryInitialize(0, self.network_interface)
            
            # 创建音频客户端
            self.audio_client = AudioClient()
            self.audio_client.SetTimeout(10.0)
            self.audio_client.Init()
            
            # 获取当前音量
            code, volume_data = self.audio_client.GetVolume()
            if code == 0 and volume_data:
                self.volume = volume_data.get('volume', 85)
                logger.info(f"G1音频客户端初始化成功，当前音量: {self.volume}")
            else:
                logger.warning(f"获取G1音量失败，使用默认音量85")
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"初始化G1音频客户端失败: {e}")
            raise

    async def start_recording(self, callback: Callable[[bytes], None]):
        """
        开始录音
        
        Args:
            callback: 音频数据回调函数，接收PCM格式的音频数据
        """
        if not self.is_initialized:
            raise RuntimeError("G1音频客户端未初始化")
        
        # 防止重复启动
        if self._is_recording:
            logger.info("G1录音已经在运行中，跳过重复启动")
            # 更新回调函数
            self._audio_callback = callback
            return
        
        self._audio_callback = callback
        self._is_recording = True
        self._recording_buffer.clear()
        
        # 启动组播接收线程
        import threading
        self._mic_thread = threading.Thread(target=self._receive_mic_data, daemon=True)
        self._mic_thread.start()
        
        logger.info("开始G1录音（组播接收）")

    async def stop_recording(self):
        """
        停止录音
        """
        self._is_recording = False
        logger.info("停止G1录音")
    
    def _get_local_ip_for_multicast(self):
        """获取本地用于组播的IP地址"""
        import subprocess
        try:
            result = subprocess.run(
                ['ip', 'addr', 'show', self.network_interface],
                capture_output=True, text=True
            )
            output = result.stdout
            for line in output.split('\n'):
                if 'inet ' in line and '192.168.123.' in line:
                    parts = line.strip().split()
                    return parts[1].split('/')[0]
        except Exception as e:
            logger.warning(f"获取本地IP失败: {e}")
        return "192.168.123.164"

    def _receive_mic_data(self):
        """
        接收G1麦克风组播数据
        优化：使用连续缓冲区确保音频数据完整性
        """
        import socket
        import struct
        import time
        import numpy as np

        GROUP_IP = "239.168.123.161"
        PORT = 5555

        local_ip = self._get_local_ip_for_multicast()

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass

            sock.bind(('', PORT))
            mreq = struct.pack('4s4s', socket.inet_aton(GROUP_IP), socket.inet_aton(local_ip))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            logger.info(f"已加入组播组 {GROUP_IP}:{PORT}，接口: {local_ip}，开始接收麦克风数据")
            logger.info("请确保G1机器人处于唤醒模式，麦克风指示灯应该是亮的")

            # 连续缓冲区 - 确保音频数据完整性
            continuous_buffer = bytearray()
            # 目标帧大小：16kHz * 60ms * 2字节 = 1920字节
            TARGET_FRAME_SIZE = 1920
            
            packet_count = 0
            total_bytes = 0

            while self._is_recording:
                try:
                    # 设置超时，避免阻塞
                    sock.settimeout(1.0)
                    data, addr = sock.recvfrom(4096)

                    if len(data) > 0 and len(data) % 2 == 0:
                        packet_count += 1
                        total_bytes += len(data)
                        
                        # 添加到连续缓冲区
                        continuous_buffer.extend(data)
                        
                        # 当缓冲区足够大时，按帧处理
                        while len(continuous_buffer) >= TARGET_FRAME_SIZE:
                            # 提取一帧数据
                            frame_data = bytes(continuous_buffer[:TARGET_FRAME_SIZE])
                            del continuous_buffer[:TARGET_FRAME_SIZE]
                            
                            if self._audio_callback:
                                # 直接传递完整的帧数据
                                self._audio_callback(frame_data)

                            self._recording_buffer.append(frame_data)

                except socket.timeout:
                    # 超时是正常的，继续等待
                    continue
                except socket.error as e:
                    if self._is_recording:
                        logger.warning(f"接收麦克风数据时出错: {e}")
                    break
                except Exception as e:
                    if self._is_recording:
                        logger.error(f"处理麦克风数据时出错: {e}")

        except Exception as e:
            if self._is_recording:
                logger.error(f"初始化麦克风组播接收失败: {e}")

        finally:
            try:
                if 'sock' in locals():
                    sock.close()
            except:
                pass
            logger.info("麦克风组播接收已停止")

    async def play_audio(self, text: str, speaker_id: int = 0):
        """
        播放TTS语音
        
        Args:
            text: 要播放的文本
            speaker_id: 说话人ID，0为中文，1为英文
        """
        if not self.is_initialized:
            raise RuntimeError("G1音频客户端未初始化")
        
        try:
            code = self.audio_client.TtsMaker(text, speaker_id)
            if code == 0:
                logger.info(f"开始播放TTS: {text[:50]}...")
                return True
            else:
                logger.error(f"TTS播放失败，错误码: {code}")
                return False
        except Exception as e:
            logger.error(f"播放TTS失败: {e}")
            return False

    async def play_pcm_stream(self, app_name: str, stream_id: str, pcm_data: bytes):
        """
        播放PCM音频流
        
        Args:
            app_name: 应用名称
            stream_id: 流ID
            pcm_data: PCM格式的音频数据（16kHz，单通道，16bit）
        """
        if not self.is_initialized:
            raise RuntimeError("G1音频客户端未初始化")
        
        try:
            code, _ = self.audio_client.PlayStream(app_name, stream_id, pcm_data)
            if code == 0:
                logger.debug(f"播放PCM流成功，数据长度: {len(pcm_data)}")
                return True
            else:
                logger.error(f"播放PCM流失败，错误码: {code}")
                return False
        except Exception as e:
            logger.error(f"播放PCM流失败: {e}")
            return False
    
    async def play_pcm(self, pcm_data: bytes):
        """
        播放PCM音频数据
        
        Args:
            pcm_data: PCM格式的音频数据（16kHz，单通道，16bit）
        """
        if not self.is_initialized:
            raise RuntimeError("G1音频客户端未初始化")
        
        try:
            # 使用默认的应用名称和流ID
            code, _ = self.audio_client.PlayStream("py-xiaozhi", "stream1", pcm_data)
            if code == 0:
                logger.debug(f"播放PCM数据成功，数据长度: {len(pcm_data)}")
                return True
            else:
                logger.error(f"播放PCM数据失败，错误码: {code}")
                return False
        except Exception as e:
            logger.error(f"播放PCM数据失败: {e}")
            return False

    async def stop_playback(self, app_name: str):
        """
        停止播放
        
        Args:
            app_name: 应用名称
        """
        if not self.is_initialized:
            raise RuntimeError("G1音频客户端未初始化")
        
        try:
            self.audio_client.PlayStop(app_name)
            logger.info(f"停止播放: {app_name}")
        except Exception as e:
            logger.error(f"停止播放失败: {e}")

    def set_volume(self, volume: int):
        """
        设置音量
        
        Args:
            volume: 音量值 (0-100)
        """
        if not self.is_initialized:
            raise RuntimeError("G1音频客户端未初始化")
        
        try:
            code = self.audio_client.SetVolume(volume)
            if code == 0:
                self.volume = volume
                logger.info(f"设置音量: {volume}")
                return True
            else:
                logger.error(f"设置音量失败，错误码: {code}")
                return False
        except Exception as e:
            logger.error(f"设置音量失败: {e}")
            return False

    def get_volume(self) -> int:
        """
        获取当前音量
        
        Returns:
            当前音量值 (0-100)
        """
        if not self.is_initialized:
            return self.volume
        
        try:
            code, volume_data = self.audio_client.GetVolume()
            if code == 0 and volume_data:
                self.volume = volume_data.get('volume', 85)
                return self.volume
        except Exception as e:
            logger.error(f"获取音量失败: {e}")
        
        return self.volume

    def set_led_color(self, r: int, g: int, b: int):
        """
        设置LED灯带颜色
        
        Args:
            r: 红色值 (0-255)
            g: 绿色值 (0-255)  
            b: 蓝色值 (0-255)
        """
        if not self.is_initialized:
            raise RuntimeError("G1音频客户端未初始化")
        
        try:
            code = self.audio_client.LedControl(r, g, b)
            if code == 0:
                logger.debug(f"设置LED颜色: RGB({r}, {g}, {b})")
                return True
            else:
                logger.error(f"设置LED颜色失败，错误码: {code}")
                return False
        except Exception as e:
            logger.error(f"设置LED颜色失败: {e}")
            return False

    async def close(self):
        """
        关闭G1音频适配器
        """
        if self._is_playing:
            await self.stop_playback("py_xiaozhi")
        
        if self._is_recording:
            await self.stop_recording()
        
        self.is_initialized = False
        logger.info("G1音频适配器已关闭")

    @staticmethod
    def is_available() -> bool:
        """
        检查G1 SDK是否可用
        
        Returns:
            True如果G1 SDK可用，否则False
        """
        return G1_AVAILABLE

    def get_audio_info(self) -> dict:
        """
        获取音频设备信息
        
        Returns:
            包含音频设备信息的字典
        """
        return {
            "type": "G1",
            "initialized": self.is_initialized,
            "volume": self.volume,
            "recording": self._is_recording,
            "playing": self._is_playing,
            "network_interface": self.network_interface
        }
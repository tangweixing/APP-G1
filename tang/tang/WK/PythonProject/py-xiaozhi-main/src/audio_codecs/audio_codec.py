from typing import List, Dict, Tuple, Set, Union, Optional
import asyncio
import gc
import time
from collections import deque
from typing import Optional

import numpy as np
import opuslib
import sounddevice as sd
import soxr

from src.constants.constants import AudioConfig
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AudioCodec:
    """
    音频编解码器，负责录音编码和播放解码
    支持标准音频设备和G1机器人音频设备
    """

    def __init__(self, use_g1_audio=False, g1_network_interface="eth0"):
        """
        初始化音频编解码器
        
        Args:
            use_g1_audio: 是否使用G1音频设备
            g1_network_interface: G1网络接口，默认eth0
        """
        self.use_g1_audio = use_g1_audio
        self.g1_network_interface = g1_network_interface
        self.g1_adapter = None
        
        self.opus_encoder = None
        self.opus_decoder = None

        # 设备采样率信息
        self.device_input_sample_rate = None
        self.device_output_sample_rate = None

        # 输入重采样器
        self.input_resampler = None

        # 重采样缓冲区，用deque提高性能
        self._resample_input_buffer = deque()

        # 输入帧大小缓存
        self._device_input_frame_size = None

        # 关闭状态标志
        self._is_closing = False

        # 音频流对象
        self.input_stream = None
        self.output_stream = None

        # 音频数据队列
        self._wakeword_buffer = asyncio.Queue(maxsize=100)  # 唤醒词检测
        self._output_buffer = asyncio.Queue(maxsize=500)  # 音频播放
        
        # 实时编码回调
        self._encoded_audio_callback = None

    async def initialize(self):
        """
        初始化音频设备和编解码器
        """
        try:
            # 检查是否使用G1音频设备
            if self.use_g1_audio:
                await self._initialize_g1_audio()
            else:
                await self._initialize_standard_audio()
                
            logger.info("音频设备和编解码器初始化成功")
        except Exception as e:
            logger.error(f"初始化音频设备失败: {e}")
            await self.close()
            raise

    async def _initialize_g1_audio(self):
        """
        初始化G1音频设备
        """
        try:
            from src.audio_codecs.g1_audio_adapter import G1AudioAdapter
            
            logger.info("初始化G1音频设备...")
            self.g1_adapter = G1AudioAdapter(self.g1_network_interface)
            await self.g1_adapter.initialize()
            
            # G1音频参数：使用16kHz（官方推荐格式）
            self.device_input_sample_rate = 16000  # G1麦克风16kHz
            self.device_output_sample_rate = 16000  # G1扬声器16kHz
            
            # 创建Opus编解码器（直接使用16kHz，不重采样）
            self.opus_encoder = opuslib.Encoder(
                AudioConfig.INPUT_SAMPLE_RATE,  # 使用16000
                AudioConfig.CHANNELS,
                opuslib.APPLICATION_AUDIO,
            )
            self.opus_decoder = opuslib.Decoder(
                AudioConfig.INPUT_SAMPLE_RATE,  # 使用16000
                AudioConfig.CHANNELS
            )
            
            # G1音频不需要重采样（直接使用16kHz原始数据）
            self.input_resampler = None
            
            logger.info(f"G1音频设备初始化成功: {self.g1_adapter.get_audio_info()}")
            logger.info(f"Opus编码器/解码器采样率: {AudioConfig.INPUT_SAMPLE_RATE}Hz（G1原始格式）")
            
        except Exception as e:
            logger.error(f"初始化G1音频设备失败: {e}")
            raise

    async def _initialize_standard_audio(self):
        """
        初始化标准音频设备
        """
        try:
            # 查询设备采样率
            input_device_info = sd.query_devices(sd.default.device[0])
            output_device_info = sd.query_devices(sd.default.device[1])

            self.device_input_sample_rate = int(input_device_info["default_samplerate"])
            self.device_output_sample_rate = int(
                output_device_info["default_samplerate"]
            )

            # 计算输入帧大小
            frame_duration_sec = AudioConfig.FRAME_DURATION / 1000
            self._device_input_frame_size = int(
                self.device_input_sample_rate * frame_duration_sec
            )

            logger.info(f"设备输入采样率: {self.device_input_sample_rate}Hz")
            logger.info(f"设备输出采样率: {self.device_output_sample_rate}Hz")
            logger.info(f"音频输出将使用固定24kHz采样率")

            # 创建重采样器
            await self._create_resamplers()

            # 设置SoundDevice默认参数
            sd.default.samplerate = None
            sd.default.channels = AudioConfig.CHANNELS
            sd.default.dtype = np.int16

            # 创建音频流
            await self._create_streams()

            # 初始化Opus编解码器
            # 编码器用于16kHz录音数据
            # 解码器用于24kHz播放数据
            self.opus_encoder = opuslib.Encoder(
                AudioConfig.INPUT_SAMPLE_RATE,
                AudioConfig.CHANNELS,
                opuslib.APPLICATION_AUDIO,
            )
            self.opus_decoder = opuslib.Decoder(
                AudioConfig.OUTPUT_SAMPLE_RATE, AudioConfig.CHANNELS
            )

        except Exception as e:
            logger.error(f"初始化标准音频设备失败: {e}")
            raise

    async def _create_resamplers(self):
        """
        创建输入重采样器，转换设备采样率到16kHz
        输出固定24kHz，不需要重采样
        """
        if self.device_input_sample_rate != AudioConfig.INPUT_SAMPLE_RATE:
            self.input_resampler = soxr.ResampleStream(
                self.device_input_sample_rate,
                AudioConfig.INPUT_SAMPLE_RATE,
                AudioConfig.CHANNELS,
                dtype="int16",
                quality="QQ",
            )
            logger.info(
                f"创建输入重采样器: {self.device_input_sample_rate}Hz -> "
                f"{AudioConfig.INPUT_SAMPLE_RATE}Hz"
            )

        logger.info(f"输出使用24kHz固定采样率")

    async def _create_streams(self):
        """
        创建音频输入输出流
        输入流使用设备原生采样率，输出流固定24kHz
        """
        try:
            # 录音流
            self.input_stream = sd.InputStream(
                samplerate=self.device_input_sample_rate,
                channels=AudioConfig.CHANNELS,
                dtype=np.int16,
                blocksize=self._device_input_frame_size,
                callback=self._input_callback,
                finished_callback=self._input_finished_callback,
                latency="low",
            )

            # 播放流
            self.output_stream = sd.OutputStream(
                samplerate=AudioConfig.OUTPUT_SAMPLE_RATE,
                channels=AudioConfig.CHANNELS,
                dtype=np.int16,
                blocksize=AudioConfig.OUTPUT_FRAME_SIZE,
                callback=self._output_callback,
                finished_callback=self._output_finished_callback,
                latency="low",
            )

            # 启动音频流
            self.input_stream.start()
            self.output_stream.start()

        except Exception as e:
            logger.error(f"创建音频流失败: {e}")
            raise
    
    def _g1_audio_callback(self, pcm_data: bytes):
        """
        G1音频数据回调函数
        处理从G1麦克风接收到的PCM数据（16kHz，单通道，16bit）
        直接编码，不进行重采样
        """
        try:
            # G1麦克风数据格式：单通道/16K采样率/16bit
            audio_array = np.frombuffer(pcm_data, dtype=np.int16)
            
            # 调试日志：显示接收到的音频数据
            if not hasattr(self, '_g1_callback_counter'):
                self._g1_callback_counter = 0
            self._g1_callback_counter += 1
            if self._g1_callback_counter % 100 == 0:
                logger.debug(f"G1音频回调：已接收 {self._g1_callback_counter} 次音频数据，长度: {len(pcm_data)} 字节")
            
            # 提供数据给唤醒词检测（使用原始16kHz数据）
            self._put_audio_data_safe(self._wakeword_buffer, audio_array.copy())
            
            # 实时编码录音数据
            if self._encoded_audio_callback:
                try:
                    # 计算16kHz下的帧大小（60ms帧 = 16000 * 0.06 = 960采样点）
                    frame_size = int(AudioConfig.INPUT_SAMPLE_RATE * (AudioConfig.FRAME_DURATION / 1000))
                    
                    # 按帧处理
                    for i in range(0, len(audio_array) - frame_size + 1, frame_size):
                        frame_data = audio_array[i:i+frame_size]
                        if len(frame_data) == frame_size:
                            frame_bytes = frame_data.tobytes()
                            encoded_data = self.opus_encoder.encode(frame_bytes, frame_size)
                            if encoded_data:
                                self._encoded_audio_callback(encoded_data)
                except Exception as e:
                    logger.warning(f"G1音频编码失败: {e}")
            else:
                logger.warning("编码音频回调未设置")
            
        except Exception as e:
            logger.error(f"处理G1音频数据失败: {e}")
    
    def _high_quality_resample(self, audio_array: np.ndarray, original_len: int, new_len: int) -> np.ndarray:
        """
        高质量重采样函数（16kHz -> 24kHz）
        使用sinc插值算法，比线性插值音质更好
        """
        try:
            # 使用scipy的重采样（如果可用）
            try:
                from scipy.signal import resample
                resampled = resample(audio_array.astype(np.float64), new_len)
                return np.clip(resampled, -32768, 32767).astype(np.int16)
            except ImportError:
                pass
            
            # 回退到改进的线性插值
            # 生成更精确的源位置
            src_positions = np.linspace(0, original_len - 1, new_len)
            src_indices = np.floor(src_positions).astype(np.int32)
            fractions = src_positions - src_indices
            
            # 边界处理
            src_indices = np.clip(src_indices, 0, original_len - 2)
            
            # 线性插值
            resampled = (audio_array[src_indices].astype(np.float32) * (1 - fractions) + 
                        audio_array[src_indices + 1].astype(np.float32) * fractions)
            
            return np.clip(resampled, -32768, 32767).astype(np.int16)
            
        except Exception as e:
            logger.warning(f"高质量重采样失败，使用基础方法: {e}")
            # 最终回退到基础方法
            src_positions = np.arange(new_len) * 2 / 3
            src_indices = src_positions.astype(np.int32)
            fractions = src_positions - src_indices
            src_indices = np.clip(src_indices, 0, original_len - 2)
            resampled = (audio_array[src_indices] * (1 - fractions) + 
                        audio_array[src_indices + 1] * fractions).astype(np.int16)
            return resampled

    def _input_callback(self, indata, frames, time_info, status):
        """
        录音回调函数
        处理录音数据，重采样到16kHz并进行Opus编码
        """
        if status and "overflow" not in str(status).lower():
            logger.warning(f"输入流状态: {status}")

        if self._is_closing:
            return

        try:
            audio_data = indata.copy().flatten()

            # 重采样处理
            if self.input_resampler is not None:
                audio_data = self._process_input_resampling(audio_data)
                if audio_data is None:
                    return

            # 实时编码录音数据
            if self._encoded_audio_callback and len(audio_data) == AudioConfig.INPUT_FRAME_SIZE:
                try:
                    pcm_data = audio_data.astype(np.int16).tobytes()
                    encoded_data = self.opus_encoder.encode(pcm_data, AudioConfig.INPUT_FRAME_SIZE)
                    
                    if encoded_data:
                        self._encoded_audio_callback(encoded_data)
                        
                except Exception as e:
                    logger.warning(f"实时录音编码失败: {e}")

            # 提供数据给唤醒词检测
            self._put_audio_data_safe(self._wakeword_buffer, audio_data.copy())

        except Exception as e:
            logger.error(f"输入回调错误: {e}")

    def _process_input_resampling(self, audio_data):
        """
        输入音频重采样处理
        将设备采样率转换为16kHz
        """
        try:
            resampled_data = self.input_resampler.resample_chunk(audio_data, last=False)
            if len(resampled_data) > 0:
                # 添加到缓冲区
                self._resample_input_buffer.extend(resampled_data.astype(np.int16))

            # 检查是否有足够数据组成完整帧
            expected_frame_size = AudioConfig.INPUT_FRAME_SIZE
            if len(self._resample_input_buffer) < expected_frame_size:
                return None

            # 取出一帧数据
            frame_data = []
            for _ in range(expected_frame_size):
                frame_data.append(self._resample_input_buffer.popleft())

            return np.array(frame_data, dtype=np.int16)

        except Exception as e:
            logger.error(f"输入重采样失败: {e}")
            return None

    def _put_audio_data_safe(self, queue, audio_data):
        """
        安全地将音频数据放入队列
        """
        try:
            queue.put_nowait(audio_data)
        except asyncio.QueueFull:
            # 队列满时移除最旧数据
            try:
                queue.get_nowait()
                queue.put_nowait(audio_data)
            except asyncio.QueueEmpty:
                queue.put_nowait(audio_data)

    def _output_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """
        播放回调函数
        从缓冲区取出24kHz音频数据进行播放
        """
        if status:
            if "underflow" not in str(status).lower():
                logger.warning(f"输出流状态: {status}")

        try:
            try:
                # 从输出缓冲区获取音频数据
                audio_data = self._output_buffer.get_nowait()

                # 写入音频数据
                if len(audio_data) >= frames:
                    outdata[:] = audio_data[:frames].reshape(-1, AudioConfig.CHANNELS)
                else:
                    outdata[: len(audio_data)] = audio_data.reshape(-1, AudioConfig.CHANNELS)
                    outdata[len(audio_data) :] = 0

            except asyncio.QueueEmpty:
                # 无数据时输出静音
                outdata.fill(0)

        except Exception as e:
            logger.error(f"输出回调错误: {e}")
            outdata.fill(0)


    def _input_finished_callback(self):
        """
        输入流结束回调
        """
        logger.info("输入流已结束")

    def _output_finished_callback(self):
        """
        输出流结束回调
        """
        logger.info("输出流已结束")

    async def reinitialize_stream(self, is_input=True):
        """
        重新初始化音频流
        """
        if self._is_closing:
            return False if is_input else None

        try:
            if is_input:
                # 重建录音流
                if self.input_stream:
                    self.input_stream.stop()
                    self.input_stream.close()

                self.input_stream = sd.InputStream(
                    samplerate=self.device_input_sample_rate,
                    channels=AudioConfig.CHANNELS,
                    dtype=np.int16,
                    blocksize=self._device_input_frame_size,
                    callback=self._input_callback,
                    finished_callback=self._input_finished_callback,
                    latency="low",
                )
                self.input_stream.start()
                logger.info("输入流重新初始化成功")
                return True
            else:
                # 重建播放流
                if self.output_stream:
                    self.output_stream.stop()
                    self.output_stream.close()

                self.output_stream = sd.OutputStream(
                    samplerate=AudioConfig.OUTPUT_SAMPLE_RATE,
                    channels=AudioConfig.CHANNELS,
                    dtype=np.int16,
                    blocksize=AudioConfig.OUTPUT_FRAME_SIZE,
                    callback=self._output_callback,
                    finished_callback=self._output_finished_callback,
                    latency="low",
                )
                self.output_stream.start()
                logger.info("输出流重新初始化成功")
                return None
        except Exception as e:
            stream_type = "输入" if is_input else "输出"
            logger.error(f"{stream_type}流重建失败: {e}")
            if is_input:
                return False
            else:
                raise

    async def get_raw_audio_for_detection(self) -> Optional[bytes]:
        """
        获取唤醒词检测用的原始音频数据
        
        从专用队列获取数据，与录音编码独立运行，
        避免数据竞争问题。

        Returns:
            Optional[bytes]: PCM格式音频数据，无数据时返回None
        """
        try:
            if self._wakeword_buffer.empty():
                return None

            audio_data = self._wakeword_buffer.get_nowait()

            # 转换为bytes格式
            if hasattr(audio_data, "tobytes"):
                return audio_data.tobytes()
            elif hasattr(audio_data, "astype"):
                return audio_data.astype("int16").tobytes()
            else:
                return audio_data

        except asyncio.QueueEmpty:
            return None
        except Exception as e:
            logger.error(f"获取唤醒词音频数据失败: {e}")
            return None

    def set_encoded_audio_callback(self, callback):
        """
        设置编码后音频数据的回调函数
        
        启用实时编码模式，录音回调中直接编码并传递，
        消除轮询延迟，提升录音实时性。
        
        Args:
            callback: 回调函数，接收编码数据参数，None时禁用实时编码
        """
        self._encoded_audio_callback = callback
        
        if callback:
            logger.info("✓ 启用实时录音编码模式 - 录音回调直接编码传递")
            # 如果使用G1音频设备，启动录音
            if self.use_g1_audio and self.g1_adapter:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.g1_adapter.start_recording(self._g1_audio_callback))
                    else:
                        loop.run_until_complete(self.g1_adapter.start_recording(self._g1_audio_callback))
                except Exception as e:
                    logger.error(f"启动G1录音失败: {e}")
        else:
            logger.info("✓ 禁用录音编码回调")
            # 如果使用G1音频设备，停止录音
            if self.use_g1_audio and self.g1_adapter:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.g1_adapter.stop_recording())
                    else:
                        loop.run_until_complete(self.g1_adapter.stop_recording())
                except Exception as e:
                    logger.error(f"停止G1录音失败: {e}")

    async def write_audio(self, opus_data: bytes):
        """
        解码Opus音频数据并放入播放队列
        输出24kHz PCM数据，直接用于播放
        """
        try:
            if self.use_g1_audio and self.g1_adapter:
                # 使用G1音频设备播放
                # G1音频设备需要PCM数据，所以仍然需要解码
                pcm_data = self.opus_decoder.decode(
                    opus_data, AudioConfig.OUTPUT_FRAME_SIZE
                )
                
                # 播放PCM数据
                await self.g1_adapter.play_pcm(pcm_data)
                logger.debug("G1音频设备播放音频数据")
            else:
                # 使用标准音频设备
                # Opus解码为24kHz PCM数据
                pcm_data = self.opus_decoder.decode(
                    opus_data, AudioConfig.OUTPUT_FRAME_SIZE
                )

                audio_array = np.frombuffer(pcm_data, dtype=np.int16)

                # 验证数据长度
                expected_length = AudioConfig.OUTPUT_FRAME_SIZE * AudioConfig.CHANNELS
                if len(audio_array) != expected_length:
                    logger.warning(f"解码音频长度异常: {len(audio_array)}, 期望: {expected_length}")
                    return

                # 放入播放缓冲区
                self._put_audio_data_safe(self._output_buffer, audio_array)

        except opuslib.OpusError as e:
            logger.warning(f"Opus解码失败，丢弃此帧: {e}")
        except Exception as e:
            logger.warning(f"音频写入失败，丢弃此帧: {e}")

    async def wait_for_audio_complete(self, timeout=10.0):
        """
        等待音频播放完成
        """
        start = time.time()
        
        # 等待播放队列清空
        while not self._output_buffer.empty() and time.time() - start < timeout:
            await asyncio.sleep(0.05)
        
        # 额外等待确保最后的音频播放完成
        await asyncio.sleep(0.3)
        
        # 检查超时情况
        if not self._output_buffer.empty():
            output_remaining = self._output_buffer.qsize()
            logger.warning(
                f"音频播放超时，剩余队列 - 输出: {output_remaining} 帧"
            )

    async def clear_audio_queue(self):
        """
        清空音频队列
        """
        cleared_count = 0

        # 清空所有队列
        queues_to_clear = [
            self._wakeword_buffer,
            self._output_buffer,
        ]

        for queue in queues_to_clear:
            while not queue.empty():
                try:
                    queue.get_nowait()
                    cleared_count += 1
                except asyncio.QueueEmpty:
                    break

        # 清空重采样缓冲区
        if self._resample_input_buffer:
            cleared_count += len(self._resample_input_buffer)
            self._resample_input_buffer.clear()

        # 等待正在处理的音频数据完成
        await asyncio.sleep(0.01)

        if cleared_count > 0:
            logger.info(f"清空音频队列，丢弃 {cleared_count} 帧音频数据")

        # 数据量大时执行垃圾回收
        if cleared_count > 100:
            gc.collect()
            logger.debug("执行垃圾回收以释放内存")

    async def start_streams(self):
        """
        启动音频输入输出流
        """
        try:
            if self.use_g1_audio and self.g1_adapter:
                # 使用G1音频设备
                if self._encoded_audio_callback:
                    await self.g1_adapter.start_recording(self._g1_audio_callback)
                logger.info("G1音频流已启动")
            else:
                # 使用标准音频设备
                if self.input_stream and not self.input_stream.active:
                    try:
                        self.input_stream.start()
                    except Exception as e:
                        logger.warning(f"启动输入流时出错: {e}")
                        await self.reinitialize_stream(is_input=True)

                if self.output_stream and not self.output_stream.active:
                    try:
                        self.output_stream.start()
                    except Exception as e:
                        logger.warning(f"启动输出流时出错: {e}")
                        await self.reinitialize_stream(is_input=False)

                logger.info("标准音频流已启动")
        except Exception as e:
            logger.error(f"启动音频流失败: {e}")

    async def stop_streams(self):
        """
        停止音频输入输出流
        """
        try:
            if self.use_g1_audio and self.g1_adapter:
                # 使用G1音频设备
                await self.g1_adapter.stop_recording()
                logger.info("G1音频流已停止")
            else:
                # 使用标准音频设备
                try:
                    if self.input_stream and self.input_stream.active:
                        self.input_stream.stop()
                except Exception as e:
                    logger.warning(f"停止输入流失败: {e}")

                try:
                    if self.output_stream and self.output_stream.active:
                        self.output_stream.stop()
                except Exception as e:
                    logger.warning(f"停止输出流失败: {e}")
                    
                logger.info("标准音频流已停止")
        except Exception as e:
            logger.error(f"停止音频流失败: {e}")

    async def _cleanup_resampler(self, resampler, name):
        """
        清理重采样器资源
        """
        if resampler:
            try:
                # 处理完剩余数据
                if hasattr(resampler, "resample_chunk"):
                    empty_array = np.array([], dtype=np.int16)
                    resampler.resample_chunk(empty_array, last=True)
            except Exception as e:
                logger.warning(f"清理{name}重采样器失败: {e}")

    async def close(self):
        """
        关闭音频编解码器，释放所有资源
        """
        if self._is_closing:
            return

        self._is_closing = True
        logger.info("开始关闭音频编解码器...")

        try:
            # 关闭G1适配器
            if self.g1_adapter:
                try:
                    await self.g1_adapter.close()
                    logger.info("G1音频适配器已关闭")
                except Exception as e:
                    logger.warning(f"关闭G1音频适配器失败: {e}")
                finally:
                    self.g1_adapter = None

            # 清空队列
            await self.clear_audio_queue()

            # 关闭流
            if self.input_stream:
                try:
                    self.input_stream.stop()
                    self.input_stream.close()
                except Exception as e:
                    logger.warning(f"关闭输入流失败: {e}")
                finally:
                    self.input_stream = None

            if self.output_stream:
                try:
                    self.output_stream.stop()
                    self.output_stream.close()
                except Exception as e:
                    logger.warning(f"关闭输出流失败: {e}")
                finally:
                    self.output_stream = None

            # 清理重采样器
            await self._cleanup_resampler(self.input_resampler, "输入")
            self.input_resampler = None

            # 清理重采样缓冲区
            self._resample_input_buffer.clear()

            # 清理编解码器
            self.opus_encoder = None
            self.opus_decoder = None

            gc.collect()  # 强制释放 nanobind 的 C++ 对象

            logger.info("音频资源已完全释放")
        except Exception as e:
            logger.error(f"关闭音频编解码器过程中发生错误: {e}")

    # G1特定功能方法
    async def play_g1_tts(self, text: str, speaker_id: int = 0) -> bool:
        """
        使用G1的TTS功能播放语音
        
        Args:
            text: 要播放的文本
            speaker_id: 说话人ID，0为中文，1为英文
            
        Returns:
            播放是否成功
        """
        if not self.use_g1_audio or not self.g1_adapter:
            logger.warning("G1音频设备未启用或未初始化")
            return False
            
        return await self.g1_adapter.play_audio(text, speaker_id)

    def set_g1_volume(self, volume: int) -> bool:
        """
        设置G1音量
        
        Args:
            volume: 音量值 (0-100)
            
        Returns:
            设置是否成功
        """
        if not self.use_g1_audio or not self.g1_adapter:
            logger.warning("G1音频设备未启用或未初始化")
            return False
            
        return self.g1_adapter.set_volume(volume)

    def get_g1_volume(self) -> int:
        """
        获取G1当前音量
        
        Returns:
            当前音量值 (0-100)
        """
        if not self.use_g1_audio or not self.g1_adapter:
            logger.warning("G1音频设备未启用或未初始化")
            return 85
            
        return self.g1_adapter.get_volume()

    def set_g1_led_color(self, r: int, g: int, b: int) -> bool:
        """
        设置G1的LED灯带颜色
        
        Args:
            r: 红色值 (0-255)
            g: 绿色值 (0-255)
            b: 蓝色值 (0-255)
            
        Returns:
            设置是否成功
        """
        if not self.use_g1_audio or not self.g1_adapter:
            logger.warning("G1音频设备未启用或未初始化")
            return False
            
        return self.g1_adapter.set_led_color(r, g, b)

    def is_g1_available(self) -> bool:
        """
        检查G1音频设备是否可用
        
        Returns:
            G1设备是否可用
        """
        return self.use_g1_audio and self.g1_adapter is not None

    def get_audio_device_info(self) -> dict:
        """
        获取音频设备信息
        
        Returns:
            包含音频设备信息的字典
        """
        if self.use_g1_audio and self.g1_adapter:
            return self.g1_adapter.get_audio_info()
        else:
            return {
                "type": "Standard",
                "input_sample_rate": self.device_input_sample_rate,
                "output_sample_rate": self.device_output_sample_rate,
                "initialized": self.opus_encoder is not None and self.opus_decoder is not None
            }

    def __del__(self):
        """
        析构函数，检查资源是否正确释放
        """
        if not self._is_closing:
            # 在析构函数中不能使用asyncio.create_task，改为记录警告
            logger.warning("AudioCodec对象被销毁但未正确关闭，请确保调用close()方法")

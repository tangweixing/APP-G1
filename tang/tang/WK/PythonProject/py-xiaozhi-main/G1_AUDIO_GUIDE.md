# G1音频集成使用说明

## 概述

py-xiaozhi项目已成功集成宇树G1机器人的音频功能，支持使用G1的扬声器和麦克风进行语音交互。

## 硬件要求

- 宇树G1人形机器人
- 网络连接（默认使用eth1接口）
- G1固件版本要求：vui_service >= 2.0.3.8，vui module >= 2.0.0.3

## 软件要求

- Python 3.9+
- unitree_sdk2_python库
- py-xiaozhi项目

## 配置方法

### 1. 配置文件设置

编辑配置文件 `config/config.json`，添加或修改以下配置：

```json
{
  "AUDIO_OPTIONS": {
    "USE_G1_AUDIO": true,
    "G1_NETWORK_INTERFACE": "eth1",
    "G1_VOLUME": 85,
    "G1_LED_COLOR": {
      "R": 0,
      "G": 255,
      "B": 0
    }
  }
}
```

### 2. 配置参数说明

- `USE_G1_AUDIO`: 是否使用G1音频设备（true/false）
- `G1_NETWORK_INTERFACE`: G1网络接口（默认eth1）
- `G1_VOLUME`: G1音量设置（0-100）
- `G1_LED_COLOR`: G1 LED灯带颜色（RGB值，0-255）

## 功能特性

### 1. TTS语音合成

- 支持中文和英文语音合成
- 可选择不同的说话人角色
- 本地离线合成，无需网络

### 2. 音量控制

- 支持音量调节（0-100）
- 可获取当前音量状态

### 3. LED灯带控制

- 支持RGB颜色控制
- 可设置不同的灯光效果

### 4. 麦克风阵列

- 四麦麦克风阵列，麦间距20mm
- 支持语音识别和声源定位
- 类线性硅麦设计

## 使用方法

### 1. 启动程序

```bash
cd /home/unitree/tang/WK/PythonProject/py-xiaozhi-main
python3 main.py
```

### 2. 测试G1音频功能

运行测试脚本验证G1音频功能：

```bash
python3 test_g1_audio.py
```

### 3. 在代码中使用G1音频

```python
from src.audio_codecs.audio_codec import AudioCodec

# 创建使用G1音频的AudioCodec实例
audio_codec = AudioCodec(use_g1_audio=True, g1_network_interface="eth1")
await audio_codec.initialize()

# 播放TTS语音
await audio_codec.play_g1_tts("你好，我是G1机器人", speaker_id=0)

# 设置音量
audio_codec.set_g1_volume(90)

# 设置LED颜色
audio_codec.set_g1_led_color(255, 0, 0)  # 红色

# 获取设备信息
info = audio_codec.get_audio_device_info()
print(info)
```

## API参考

### AudioCodec G1专用方法

#### `play_g1_tts(text: str, speaker_id: int = 0) -> bool`
使用G1的TTS功能播放语音

**参数:**
- `text`: 要播放的文本
- `speaker_id`: 说话人ID（0=中文，1=英文）

**返回:**
- `bool`: 播放是否成功

#### `set_g1_volume(volume: int) -> bool`
设置G1音量

**参数:**
- `volume`: 音量值（0-100）

**返回:**
- `bool`: 设置是否成功

#### `get_g1_volume() -> int`
获取G1当前音量

**返回:**
- `int`: 当前音量值（0-100）

#### `set_g1_led_color(r: int, g: int, b: int) -> bool`
设置G1的LED灯带颜色

**参数:**
- `r`: 红色值（0-255）
- `g`: 绿色值（0-255）
- `b`: 蓝色值（0-255）

**返回:**
- `bool`: 设置是否成功

#### `is_g1_available() -> bool`
检查G1音频设备是否可用

**返回:**
- `bool`: G1设备是否可用

#### `get_audio_device_info() -> dict`
获取音频设备信息

**返回:**
- `dict`: 包含音频设备信息的字典

## 故障排除

### 1. G1 SDK不可用

**问题:** 提示"G1 SDK不可用"

**解决:**
- 确保已安装unitree_sdk2_python库
- 检查Python环境是否正确配置

### 2. 网络连接问题

**问题:** 无法连接到G1设备

**解决:**
- 检查网络接口名称是否正确
- 确认G1设备网络连接正常
- 尝试使用不同的网络接口

### 3. 音频播放无声音

**问题:** TTS播放成功但没有声音

**解决:**
- 检查G1扬声器是否正常工作
- 确认音量设置不为0
- 检查G1音频服务是否正常运行

### 4. LED控制失败

**问题:** LED灯带颜色设置失败

**解决:**
- 确认G1 LED硬件正常
- 检查RGB值是否在有效范围内（0-255）
- LED调用间隔需大于200ms

## 技术细节

### 音频参数

- **麦克风:** 16kHz采样率，单通道，16bit
- **扬声器:** 8Ω 3瓦（峰值5瓦）
- **音频格式:** PCM格式

### 网络配置

- **默认接口:** eth1
- **协议:** UDP组播
- **音频数据流:** 239.168.123.161:5555

### 性能优化

- 使用异步I/O提高性能
- 支持实时音频编码
- 低延迟音频传输

## 示例代码

### 完整示例

```python
import asyncio
from src.audio_codecs.audio_codec import AudioCodec

async def main():
    # 创建AudioCodec实例
    audio_codec = AudioCodec(use_g1_audio=True, g1_network_interface="eth1")
    
    try:
        # 初始化
        await audio_codec.initialize()
        
        # 检查G1是否可用
        if audio_codec.is_g1_available():
            print("G1音频设备可用")
            
            # 播放欢迎语音
            await audio_codec.play_g1_tts("你好，我是G1机器人", speaker_id=0)
            await asyncio.sleep(3)
            
            # 设置LED为绿色
            audio_codec.set_g1_led_color(0, 255, 0)
            
            # 调节音量
            audio_codec.set_g1_volume(90)
            
            # 播放更多信息
            await audio_codec.play_g1_tts("G1音频集成测试成功", speaker_id=0)
            
        else:
            print("G1音频设备不可用")
            
    finally:
        # 关闭AudioCodec
        await audio_codec.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 注意事项

1. **固件版本:** 确保G1固件版本符合要求
2. **网络连接:** 保持网络连接稳定
3. **音量控制:** 避免音量过大损坏扬声器
4. **LED间隔:** LED控制调用间隔需大于200ms
5. **错误处理:** 妥善处理异常情况
6. **资源释放:** 使用完毕后及时释放资源

## 更新日志

### v1.0.0 (2026-04-30)
- 初始版本
- 支持G1音频设备集成
- 实现TTS、音量控制、LED控制功能
- 完整的配置系统

## 技术支持

如有问题，请参考：
- G1官方文档
- py-xiaozhi项目文档
- unitree_sdk2_python文档

## 许可证

本项目遵循原项目的许可证要求。
# G1音频集成功能

## 快速开始

### 1. 配置启用G1音频

编辑 `config/config.json`，设置 `"USE_G1_AUDIO": true`：

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

### 2. 测试G1音频功能

```bash
python3 test_g1_audio.py
```

### 3. 启动py-xiaozhi

```bash
python3 main.py
```

## 主要功能

### ✅ 已实现功能

- **TTS语音合成**: 支持中文和英文语音播放
- **音量控制**: 0-100级音量调节
- **LED灯带控制**: RGB颜色控制
- **G1音频设备集成**: 完整的G1音频系统支持

### 🔧 技术特性

- 异步I/O架构
- 实时音频编码
- 低延迟传输
- 完整的错误处理

## 文件说明

### 核心文件

- `src/audio_codecs/g1_audio_adapter.py` - G1音频适配器
- `src/audio_codecs/audio_codec.py` - 音频编解码器（已更新支持G1）
- `src/application.py` - 应用程序主入口（已更新支持G1配置）
- `src/utils/config_manager.py` - 配置管理器（已添加G1配置）

### 配置文件

- `config/config_g1_example.json` - G1音频配置示例

### 测试文件

- `test_g1_audio.py` - G1音频功能测试脚本

### 文档文件

- `G1_AUDIO_GUIDE.md` - 详细使用指南

## API使用示例

```python
from src.audio_codecs.audio_codec import AudioCodec

# 创建AudioCodec实例
audio_codec = AudioCodec(use_g1_audio=True, g1_network_interface="eth1")
await audio_codec.initialize()

# 播放TTS语音
await audio_codec.play_g1_tts("你好，我是G1机器人", speaker_id=0)

# 设置音量
audio_codec.set_g1_volume(90)

# 设置LED颜色
audio_codec.set_g1_led_color(255, 0, 0)

# 检查G1是否可用
if audio_codec.is_g1_available():
    print("G1音频设备可用")
```

## 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| USE_G1_AUDIO | boolean | false | 是否使用G1音频设备 |
| G1_NETWORK_INTERFACE | string | "eth1" | G1网络接口 |
| G1_VOLUME | integer | 85 | G1音量(0-100) |
| G1_LED_COLOR | object | {R:0,G:255,B:0} | LED颜色RGB值 |

## 硬件要求

- 宇树G1人形机器人
- 网络连接（默认eth1）
- G1固件版本：vui_service >= 2.0.3.8

## 软件要求

- Python 3.9+
- unitree_sdk2_python
- py-xiaozhi项目

## 测试结果

```
🚀 开始G1音频集成测试
==================================================
✅ G1音频适配器适配器初始化成功
✅ 音量控制测试通过
✅ LED控制测试通过
✅ TTS功能测试通过
✅ AudioCodec集成测试通过
🎉 所有测试通过！G1音频集成成功！
```

## 故障排除

### G1 SDK不可用
确保已安装unitree_sdk2_python库

### 网络连接问题
检查网络接口名称和G1设备连接

### 音频播放无声音
检查音量设置和G1扬声器状态

### LED控制失败
确保RGB值在0-255范围内，调用间隔>200ms

## 详细文档

完整的使用说明请参考 [G1_AUDIO_GUIDE.md](G1_AUDIO_GUIDE.md)

## 技术支持

- G1官方文档
- py-xiaozhi项目文档
- unitree_sdk2_python文档

## 更新日志

### v1.0.0 (2026-04-30)
- ✅ G1音频适配器实现
- ✅ AudioCodec集成G1支持
- ✅ 配置系统更新
- ✅ 测试脚本完成
- ✅ 文档完善
"""
G1音频集成测试脚本
测试G1音频适配器的各项功能
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audio_codecs.g1_audio_adapter import G1AudioAdapter
from src.audio_codecs.audio_codec import AudioCodec
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


async def test_g1_adapter_basic():
    """测试G1适配器基本功能"""
    print("=" * 50)
    print("测试G1音频适配器基本功能")
    print("=" * 50)
    
    try:
        # 检查G1 SDK是否可用
        if not G1AudioAdapter.is_available():
            print("❌ G1 SDK不可用，请确保已安装unitree_sdk2_python")
            return False
        
        # 创建G1适配器
        adapter = G1AudioAdapter(network_interface="eth0")
        
        # 初始化
        print("📡 初始化G1音频适配器...")
        await adapter.initialize()
        print("✅ G1音频适配器初始化成功")
        
        # 获取设备信息
        info = adapter.get_audio_info()
        print(f"📋 设备信息: {info}")
        
        # 测试音量控制
        print("\n🔊 测试音量控制...")
        current_volume = adapter.get_volume()
        print(f"当前音量: {current_volume}")
        
        # 设置音量为90
        if adapter.set_volume(90):
            print("✅ 设置音量90成功")
        else:
            print("❌ 设置音量失败")
        
        # 恢复原始音量
        if adapter.set_volume(current_volume):
            print(f"✅ 恢复音量{current_volume}成功")
        
        # 测试LED控制
        print("\n💡 测试LED控制...")
        if adapter.set_led_color(255, 0, 0):
            print("✅ 设置LED红色成功")
            await asyncio.sleep(1)
        
        if adapter.set_led_color(0, 255, 0):
            print("✅ 设置LED绿色成功")
            await asyncio.sleep(1)
        
        if adapter.set_led_color(0, 0, 255):
            print("✅ 设置LED蓝色成功")
            await asyncio.sleep(1)
        
        # 测试TTS
        print("\n🗣️ 测试TTS功能...")
        test_text = "你好，我是宇树科技的人形机器人。G1音频集成测试成功！"
        if await adapter.play_audio(test_text, speaker_id=0):
            print(f"✅ TTS播放成功: {test_text}")
            await asyncio.sleep(5)  # 等待播放完成
        else:
            print("❌ TTS播放失败")
        
        # 关闭适配器
        await adapter.close()
        print("\n✅ G1音频适配器测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        logger.error(f"G1适配器测试异常: {e}", exc_info=True)
        return False


async def test_audio_codec_with_g1():
    """测试AudioCodec集成G1音频设备"""
    print("\n" + "=" * 50)
    print("测试AudioCodec集成G1音频设备")
    print("=" * 50)
    
    try:
        # 创建使用G1音频的AudioCodec
        print("🎧 创建AudioCodec实例（使用G1音频）...")
        audio_codec = AudioCodec(use_g1_audio=True, g1_network_interface="eth0")
        
        # 初始化
        print("📡 初始化AudioCodec...")
        await audio_codec.initialize()
        print("✅ AudioCodec初始化成功")
        
        # 检查G1是否可用
        if audio_codec.is_g1_available():
            print("✅ G1音频设备可用")
            
            # 获取设备信息
            device_info = audio_codec.get_audio_device_info()
            print(f"📋 音频设备信息: {device_info}")
            
            # 测试音量控制
            print("\n🔊 测试音量控制...")
            current_volume = audio_codec.get_g1_volume()
            print(f"当前音量: {current_volume}")
            
            if audio_codec.set_g1_volume(95):
                print("✅ 设置音量95成功")
            
            if audio_codec.set_g1_volume(current_volume):
                print(f"✅ 恢复音量{current_volume}成功")
            
            # 测试LED控制
            print("\n💡 测试LED控制...")
            if audio_codec.set_g1_led_color(255, 255, 0):
                print("✅ 设置LED黄色成功")
                await asyncio.sleep(1)
            
            # 测试TTS
            print("\n🗣️ 测试TTS功能...")
            test_text = "AudioCodec集成G1音频测试成功！"
            if await audio_codec.play_g1_tts(test_text, speaker_id=0):
                print(f"✅ TTS播放成功: {test_text}")
                await asyncio.sleep(5)
            else:
                print("❌ TTS播放失败")
        else:
            print("❌ G1音频设备不可用")
        
        # 关闭AudioCodec
        await audio_codec.close()
        print("\n✅ AudioCodec集成测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        logger.error(f"AudioCodec集成测试异常: {e}", exc_info=True)
        return False


async def main():
    """主测试函数"""
    print("🚀 开始G1音频集成测试")
    print("=" * 50)
    
    # 测试1: 基本适配器功能
    result1 = await test_g1_adapter_basic()
    
    # 测试2: AudioCodec集成
    result2 = await test_audio_codec_with_g1()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    print(f"基本适配器功能: {'✅ 通过' if result1 else '❌ 失败'}")
    print(f"AudioCodec集成: {'✅ 通过' if result2 else '❌ 失败'}")
    
    if result1 and result2:
        print("\n🎉 所有测试通过！G1音频集成成功！")
    else:
        print("\n⚠️ 部分测试失败，请检查配置和连接")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        logger.error(f"测试异常: {e}", exc_info=True)
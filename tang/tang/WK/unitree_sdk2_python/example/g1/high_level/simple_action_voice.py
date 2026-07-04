#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G1 机器人 手部动作+语音 执行器

基于 multi_nav.py 简化版本
功能：执行手部动作 + 播放指定语音内容

特点：
  ✅ 无ROS依赖（直接使用Unitree SDK2）
  ✅ 16种预设手部动作
  ✅ 自定义语音输入
  ✅ 预设常用语音模板
  ✅ 自动手臂复位
  ✅ 简洁命令行交互

使用方法：
  python3 simple_action_voice.py eth0

示例：
  > 8 您好          # 执行"比心" + 说"您好"
  > c               # 进入组合模式（选择动作+语音）
  > q               # 退出
"""

import time
import sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map


# ============================================================
#  动作定义（与 multi_nav.py 完全一致）
# ============================================================
ACTIONS = {
    0: {"name": "释放手臂", "en": "release arm", "desc": "放松机械臂"},
    1: {"name": "握手", "en": "shake hand", "desc": "握手致意"},
    2: {"name": "击掌", "en": "high five", "desc": "高举击掌"},
    3: {"name": "拥抱", "en": "hug", "desc": "张开双臂"},
    4: {"name": "挥手", "en": "high wave", "desc": "高高挥手"},
    5: {"name": "鼓掌", "en": "clap", "desc": "双手鼓掌"},
    6: {"name": "面部挥手", "en": "face wave", "desc": "面前挥手"},
    7: {"name": "左亲吻", "en": "left kiss", "desc": "左边飞吻"},
    8: {"name": "比心", "en": "heart", "desc": "双手比心"},
    9: {"name": "右比心", "en": "right heart", "desc": "单手比心"},
    10: {"name": "举手", "en": "hands up", "desc": "双手高举"},
    11: {"name": "X光", "en": "x-ray", "desc": "X光扫描姿势"},
    12: {"name": "右手举起", "en": "right hand up", "desc": "右臂上扬"},
    13: {"name": "拒绝", "en": "reject", "desc": "拒绝手势"},
    14: {"name": "右亲吻", "en": "right kiss", "desc": "右边飞吻"},
    15: {"name": "双手吻", "en": "two-hand kiss", "desc": "双手飞吻"}
}

# 预设语音模板
PRESET_VOICES = [
    "您好，我是G1机器人！",
    "欢迎来到朝野科技！",
    "很高兴见到您！",
    "请跟随我参观。",
    "这是我们的产品展示区。",
    "请问有什么可以帮助您的？",
    "请让一让我通过，谢谢！",
    "再见，期待下次见面！",
    "感谢您的参观！",
    "祝您生活愉快！"
]


class SimpleActionVoice:
    """
    G1 手部动作+语音 控制器
    
    基于 multi_nav.py 的 RobotController 类简化而来
    移除ROS依赖，仅保留核心功能
    """
    
    def __init__(self, network_interface):
        self.network_interface = network_interface
        self.audio_client = None
        self.arm_client = None
        
        print("\n" + "=" * 60)
        print("  🤖 G1 手部动作+语音 执行器")
        print("  (基于 multi_nav.py)")
        print("=" * 60)
        print(f"\n  📍 网络接口: {network_interface}")
        
        self._init_systems()
    
    def _init_systems(self):
        """初始化音频和手臂系统"""
        print("  ⏳ 正在初始化...")
        
        # 初始化 SDK 通信层
        try:
            ChannelFactoryInitialize(0, self.network_interface)
            print("  ✅ SDK 通信层就绪")
        except Exception as e:
            raise RuntimeError(f"SDK初始化失败: {e}")
        
        # 初始化音频客户端
        try:
            self.audio_client = AudioClient()
            self.audio_client.Init()
            self.audio_client.SetTimeout(10.0)
            self._wakeup_audio()
            print("  ✅ 音频系统就绪")
        except Exception as e:
            raise RuntimeError(f"音频系统初始化失败: {e}")
        
        # 初始化手臂客户端
        try:
            self.arm_client = G1ArmActionClient()
            self.arm_client.Init()
            print("  ✅ 手臂控制系统就绪")
        except Exception as e:
            raise RuntimeError(f"手臂系统初始化失败: {e}")
        
        print("\n" + "-" * 60)
        print("  🎉 所有系统就绪！可以开始使用")
        print("-" * 60)
    
    def _wakeup_audio(self):
        """唤醒音频硬件"""
        for i in range(10):
            try:
                self.audio_client.GetVolume()
                break
            except Exception:
                if i < 9:
                    time.sleep(1)
        
        self.audio_client.SetVolume(100)
        time.sleep(0.5)
    
    def speak(self, text, smart_pause=False, pause_duration=0.5):
        """
        播放语音（支持智能分段停顿）
        
        Args:
            text: 要朗读的文本
            smart_pause: 是否启用智能停顿模式（识别空格作为停顿点）
            pause_duration: 停顿时长（秒），默认0.5秒
            
        Returns:
            bool: 是否成功
        """
        if not text or not text.strip():
            print("  ⚠️ 语音内容为空")
            return False
        
        text = text.strip()
        
        if smart_pause and ' ' in text:
            return self._speak_with_pauses(text, pause_duration)
        else:
            return self._speak_normal(text)
    
    def _speak_normal(self, text):
        """普通模式：一次性播放完整文本"""
        print(f"\n  🔊 播放语音:")
        print(f'     "{text}"')
        
        try:
            start_time = time.time()
            
            # 调用TTS播放（与 multi_nav.py 相同）
            self.audio_client.TtsMaker(text, 0)
            
            # 预计时长（与 multi_nav.py 一致：每个字约0.195秒）
            estimated_duration = len(text) * 0.195
            print(f"     ⏳  {estimated_duration:.1f}秒...", end="", flush=True)
            
            time.sleep(estimated_duration)
            
            actual_duration = time.time() - start_time
            print(f" ✓ ({actual_duration:.1f}s)")
            return True
            
        except Exception as e:
            print(f"\n  ❌ 语音播放失败: {e}")
            return False
    
    def _speak_with_pauses(self, text, pause_duration=0.5):
        """
        智能分段停顿模式：
        - 按空格分割文本为多个片段
        - 依次播放每个片段
        - 片段之间自动插入停顿（默认0.5秒）
        - 连续多个空格 = 多次停顿
        
        示例输入：
          "小野祝大家六一快乐 我来给大家分零食啦 让我看看人到齐没有"
          
        输出效果：
          [播放] "小野祝大家六一快乐"
          [停顿] 0.5秒
          [播放] "我来给大家分零食啦"
          [停顿] 0.5秒
          [播放] "让我看看人到齐没有"
        """
        print(f"\n  🔊 【智能分段模式】")
        print(f'     原文: "{text}"')
        print(f"     停顿时长: {pause_duration}秒/段\n")
        
        try:
            total_start_time = time.time()
            segment_count = 0
            pause_count = 0
            total_chars = 0
            
            # 使用正则表达式分割：保留连续空格信息
            import re
            parts = re.split(r'( +)', text)  # 分割文本和空格
            
            current_segment = ""
            
            for i, part in enumerate(parts):
                if part.startswith(' '):  # 这是空格部分
                    # 先播放当前累积的片段
                    if current_segment.strip():
                        segment_count += 1
                        total_chars += len(current_segment.strip())
                        
                        print(f"     [{segment_count}] 🎤 \"{current_segment.strip()}\"", end="", flush=True)
                        
                        seg_start = time.time()
                        self.audio_client.TtsMaker(current_segment.strip(), 0)
                        
                        seg_estimated = len(current_segment.strip()) * 0.195
                        time.sleep(seg_estimated)
                        
                        seg_actual = time.time() - seg_start
                        print(f" ✓ ({seg_actual:.1f}s)")
                    
                    current_segment = ""
                    
                    # 处理停顿（每个空格 = 一次停顿）
                    space_count = len(part)
                    for j in range(space_count):
                        pause_count += 1
                        print(f"     ⏸️  停顿 #{pause_count} ({pause_duration}秒)...", end="", flush=True)
                        time.sleep(pause_duration)
                        print(" ✓")
                
                else:  # 这是文本部分
                    current_segment += part
            
            # 播放最后一段
            if current_segment.strip():
                segment_count += 1
                total_chars += len(current_segment.strip())
                
                print(f"     [{segment_count}] 🎤 \"{current_segment.strip()}\"", end="", flush=True)
                
                seg_start = time.time()
                self.audio_client.TtsMaker(current_segment.strip(), 0)
                
                seg_estimated = len(current_segment.strip()) * 0.195
                time.sleep(seg_estimated)
                
                seg_actual = time.time() - seg_start
                print(f" ✓ ({seg_actual:.1f}s)")
            
            # 统计总时长
            total_elapsed = time.time() - total_start_time
            
            print(f"\n  ✅ 智能分段播放完成:")
            print(f"     总段数: {segment_count}")
            print(f"     总字数: {total_chars}")
            print(f"     停顿次数: {pause_count}")
            print(f"     总时长: {total_elapsed:.1f}秒")
            
            return True
            
        except Exception as e:
            print(f"\n  ❌ 语音播放失败: {e}")
            return False
    
    def execute_action(self, action_id):
        """
        执行单个动作
        
        Args:
            action_id: 动作ID (0-15)
            
        Returns:
            bool: 是否成功
        """
        if action_id not in ACTIONS:
            print(f"  ❌ 无效动作ID: {action_id} (有效范围: 0-{max(ACTIONS.keys())})")
            return False
        
        action_info = ACTIONS[action_id]
        action_en = action_info["en"]
        action_cn = action_info["name"]
        
        print(f"\n  🎬 执行动作 [{action_id}] {action_cn} ({action_en})...")
        print(f"     描述: {action_info['desc']}", end=" ", flush=True)
        
        try:
            start_time = time.time()
            
            # 调用手臂API执行动作（与 multi_nav.py 相同）
            self.arm_client.ExecuteAction(action_map.get(action_en))
            
            # 等待动作完成（与 multi_nav.py 一致：2秒）
            time.sleep(2.0)
            
            elapsed = time.time() - start_time
            print(f"✓ ({elapsed:.1f}s)")
            return True
            
        except Exception as e:
            print(f"\n  ❌ 动作执行失败: {e}")
            return False
    
    def perform_interaction(self, text, action_id):
        """
        执行动作+语音组合（与 multi_nav.py 的 perform_interaction 完全一致）
        
        流程：执行动作 → 播放语音 → 复位手臂
        
        Args:
            text: 语音内容
            action_id: 动作ID
            
        Returns:
            bool: 是否成功
        """
        print(f"\n{'='*60}")
        print(f"  🎭 组合执行: 动作 + 语音")
        print(f"{'='*60}")
        
        # Step 1: 执行动作
        self.execute_action(action_id)
        
        # Step 2: 播放语音
        if text and text.strip():
            self.speak(text)
        else:
            print("  ⏭️ 跳过语音\n")
        
        # Step 3: 复位手臂（与 multi_nav.py 一致：ExecuteAction(99)）
        print("  🔄 复位手臂...", end=" ", flush=True)
        try:
            self.arm_client.ExecuteAction(99)  # 99是复位动作ID
            time.sleep(3.0)  # 复位等待时间（与multi_nav.py一致）
            print("✓\n")
        except Exception as e:
            print(f"\n  ⚠️ 复位失败: {e}\n")
        
        print(f"{'='*60}")
        print("  ✅ 组合执行完成！\n")
        return True
    
    def reset_arm(self):
        """复位手臂到初始位置"""
        print("\n  🔄 复位手臂...", end=" ", flush=True)
        try:
            self.arm_client.ExecuteAction(99)
            time.sleep(3.0)
            print("✓\n")
            return True
        except Exception as e:
            print(f"\n  ❌ 复位失败: {e}\n")
            return False


def display_actions():
    """显示可用动作列表"""
    print("\n┌──────────────────────────────────────────────────┐")
    print("│  📋 可用动作列表 (来自 multi_nav.py)              │")
    print("├──────┬─────────────────┬──────────┬───────────────┤")
    print("│  ID  │  动作名称       │  英文名   │  描述         │")
    print("├──────┼─────────────────┼──────────┼───────────────┤")
    
    for aid, info in ACTIONS.items():
        print(f"│  {aid:<2}  │  {info['name']:<13} │  {info['en']:<8} │  {info['desc']:<11} │")
    
    print("└──────────────────────────────────────────────────┘")


def display_presets():
    """显示预设语音"""
    print("\n┌──────────────────────────────────────────────────┐")
    print("│  📝 预设语音模板                                   │")
    print("├──────────────────────────────────────────────────┤")
    for idx, voice in enumerate(PRESET_VOICES, 1):
        print(f"│  {idx:2d}. {voice:<46} │")
    print("└──────────────────────────────────────────────────┘")


def display_help():
    """显示帮助信息"""
    help_text = """
  ┌────────────────────────────────────────────────────────┐
  │  🎮 操作指南                                          │
  ├────────────────────────────────────────────────────────┤
  │                                                        │
  │  快捷操作:                                              │
  │    • 数字 (0-15)       → 仅执行该动作                  │
  │    • 文本               → 仅播放该语音                  │
  │                                                        │
  │  高级操作:                                              │
  │    • v                 → 🆕 智能语音模式（空格自动停顿）│
  │    • c                 → 组合模式 (动作+语音)           │
  │    • r                 → 复位手臂                      │
  │    • p                 → 显示预设语音                   │
  │    • h                 → 显示此帮助                     │
  │    • q / Ctrl+C        → 退出                          │
  │                                                        │
  │  示例:                                                  │
  │    > 8                # 执行"比心"                      │
  │    > 您好             # 说"您好"                        │
  │    > v                # 进入智能语音模式                │
  │    > c                # 进入详细选择模式               │
  │                                                        │
  └────────────────────────────────────────────────────────┘
"""
    print(help_text)


def enter_smart_voice_mode(controller):
    """
    智能语音模式：输入文本时自动识别空格作为停顿点
    
    特点：
      - 空格 = 停顿0.5秒（可自定义）
      - 多个空格 = 多次停顿
      - 实时显示每段播放进度
    
    适用场景：
      - 需要节奏感的讲解/表演
      - 分段式对话
      - 强调重点内容
    """
    print("\n" + "=" * 60)
    print("  🔊 【智能语音模式】")
    print("=" * 60)
    
    print("\n  💡 使用说明:")
    print("     • 输入文本中的【空格】会被识别为停顿点")
    print("     • 每个【空格】= 自动停顿 0.5 秒")
    print("     • 【多个空格】= 多次停顿（如3个空格=1.5秒）")
    print("     • 输入完成后按回车播放\n")
    
    print("  ⚙️  可选设置:")
    pause_input = input("     停顿时长 [默认0.5秒，直接回车]: ").strip()
    
    try:
        if pause_input:
            pause_duration = float(pause_input)
            if pause_duration < 0.1:
                print("     ⚠️ 最小0.1秒，已调整为0.1")
                pause_duration = 0.1
            elif pause_duration > 5.0:
                print("     ⚠️ 最大5秒，已调整为5.0")
                pause_duration = 5.0
        else:
            pause_duration = 0.5
    except ValueError:
        print("     ⚠️ 无效输入，使用默认值0.5秒")
        pause_duration = 0.5
    
    print(f"\n  ✅ 停顿时长: {pause_duration}秒")
    print("\n  " + "-" * 60)
    print("  ✏️ 请输入文本（空格=停顿）:")
    print("-" * 60)
    
    text = input("  📝 ").strip()
    
    if not text:
        print("  ❌ 文本为空，取消播放\n")
        return
    
    if ' ' not in text:
        print("  ⚠️ 未检测到空格，将使用普通模式播放\n")
    
    print(f"\n  📋 待播放文本:")
    print(f'     "{text}"')
    
    confirm = input(f"\n  ▶️  开始播放? (停顿{pause_duration}秒) [Y/n]: ").strip().lower()
    
    if confirm == 'n':
        print("  ❌ 已取消\n")
        return
    
    # 调用智能分段播放
    controller.speak(text, smart_pause=True, pause_duration=pause_duration)
    print()


def main():
    """主程序"""
    
    # 参数检查
    if len(sys.argv) < 2:
        print("\n❌ 使用方法: python3 simple_action_voice.py <网络接口>")
        print("   示例: python3 simple_action_voice.py eth0\n")
        sys.exit(1)
    
    network_interface = sys.argv[1]
    
    # 初始化控制器
    try:
        controller = SimpleActionVoice(network_interface)
    except Exception as e:
        print(f"\n  ❌ 初始化失败: {e}")
        print("  请检查:")
        print("    1. 网络接口是否正确 (eth0/wlan0)")
        print("    2. G1机器人是否开机并连接\n")
        sys.exit(1)
    
    # 显示可用选项
    display_actions()
    display_presets()
    display_help()
    
    print("\n  💡 准备就绪！请输入指令:\n")
    
    # 主循环
    while True:
        try:
            user_input = input("  👉 ").strip()
            
            if not user_input:
                continue
            
            # ===== 退出 =====
            if user_input.lower() == 'q':
                print("\n  👋 再见！\n")
                break
            
            # ===== 帮助 =====
            elif user_input.lower() == 'h':
                display_help()
                continue
            
            # ===== 复位 =====
            elif user_input.lower() == 'r':
                controller.reset_arm()
                continue
            
            # ===== 预设语音 =====
            elif user_input.lower() == 'p':
                display_presets()
                continue
            
            # ===== 智能语音模式 =====
            elif user_input.lower() == 'v':
                enter_smart_voice_mode(controller)
                continue
            
            # ===== 组合模式 =====
            elif user_input.lower() == 'c':
                enter_combination_mode(controller)
                continue
            
            # ===== 快捷格式: "数字 文本" 或 "数字" =====
            parts = user_input.split(None, 1)  # 分割为最多2部分
            
            if parts[0].isdigit():
                action_id = int(parts[0])
                
                if action_id in ACTIONS:
                    # 有文本 → 组合执行
                    if len(parts) > 1 and parts[1]:
                        controller.perform_interaction(parts[1], action_id)
                    else:
                        # 无文本 → 仅执行动作
                        controller.execute_action(action_id)
                        
                        # 询问复位
                        reset_choice = input("  🔄 复位? [Y/n]: ").strip().lower()
                        if reset_choice != 'n':
                            controller.reset_arm()
                else:
                    print(f"  ❌ 无效动作ID: {action_id}\n")
            else:
                # 纯文本 → 仅播放语音
                controller.speak(user_input)
            
        except KeyboardInterrupt:
            print("\n\n  ⚠️  Ctrl+C 检测，退出中...\n")
            break
        except Exception as e:
            print(f"\n  ❌ 错误: {e}\n")


def enter_combination_mode(controller):
    """进入详细的组合模式"""
    print("\n" + "=" * 60)
    print("  🎭 【组合模式】选择动作和语音")
    print("=" * 60)
    
    # 步骤1: 选择动作
    print("\n  [步骤 1/2] 选择动作")
    display_actions()
    
    action_input = input("\n  🎬 输入动作ID (0-15): ").strip()
    
    try:
        action_id = int(action_input)
        if action_id not in ACTIONS:
            print(f"  ❌ 无效ID: {action_id}\n")
            return
    except ValueError:
        print("  ❌ 请输入数字\n")
        return
    
    selected = ACTIONS[action_id]
    print(f"  ✓ 已选: [{action_id}] {selected['name']}")
    
    # 步骤2: 选择语音
    print("\n  [步骤 2/2] 选择语音")
    print("    1. 从预设模板选择")
    print("    2. 自定义输入")
    print("    3. 跳过（仅动作）")
    
    choice = input("  🔊 选择 [1/2/3]: ").strip()
    
    text = None
    
    if choice == '1':
        display_presets()
        vinput = input("  👉 输入预设编号: ").strip()
        try:
            vidx = int(vinput) - 1
            if 0 <= vidx < len(PRESET_VOICES):
                text = PRESET_VOICES[vidx]
                print(f'  ✓ 已选: "{text}"')
            else:
                print("  ⚠️ 无效编号，切换到自定义")
                text = input("  ✏️ 输入语音: ").strip()
        except ValueError:
            text = PRESET_VOICES[0]
    
    elif choice == '2':
        text = input("  ✏️ 输入语音内容: ").strip()
        if text:
            print(f'  ✓ 已输入: "{text}"')
    
    elif choice == '3':
        print("  ⏭️ 将仅执行动作")
    
    else:
        print("  ⚠️ 默认跳过语音")
    
    # 确认执行
    print("\n  ──────────────────────────────────────")
    print(f"  动作: [{action_id}] {selected['name']}")
    print(f"  语音: {repr(text)}")
    
    confirm = input("\n  ▶️  执行? [Y/n]: ").strip().lower()
    
    if confirm == 'n':
        print("  ❌ 已取消\n")
        return
    
    # 执行
    if text:
        controller.perform_interaction(text, action_id)
    else:
        controller.execute_action(action_id)
        controller.reset_arm()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，程序退出\n")
    except Exception as e:
        print(f"\n💥 异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

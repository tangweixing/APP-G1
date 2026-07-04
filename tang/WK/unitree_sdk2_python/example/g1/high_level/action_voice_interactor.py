#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G1 机器人 动作+语音 交互式控制器
基于 multi_nav_hys.py

功能特性：
  ✅ 16种预设动作一键选择
  ✅ 自定义语音内容输入
  ✅ 预设语音模板库（问候/讲解/互动/告别）
  ✅ 单独执行动作 或 动作+语音组合
  ✅ 手臂自动复位
  ✅ 实时状态反馈

使用方法：
  python3 action_voice_interactor.py eth0

作者：基于 multi_nav_hys.py 改编
日期：2026-05-27
"""

import rospy
import time
import sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map

# ============================================================
#  动作定义（与 multi_nav_hys.py 保持一致）
# ============================================================
ACTIONS = {
    0: {
        "name": "释放手臂",
        "en_name": "release arm",
        "desc": "放松机械臂到自然下垂位置"
    },
    1: {
        "name": "握手",
        "en_name": "shake hand",
        "desc": "伸出右手握手致意"
    },
    2: {
        "name": "击掌",
        "en_name": "high five",
        "desc": "高举右手准备击掌"
    },
    3: {
        "name": "拥抱",
        "en_name": "hug",
        "desc": "张开双臂做出拥抱姿势"
    },
    4: {
        "name": "挥手",
        "en_name": "high wave",
        "desc": "高高挥动手臂打招呼"
    },
    5: {
        "name": "鼓掌",
        "en_name": "clap",
        "desc": "双手鼓掌表示赞赏"
    },
    6: {
        "name": "面部挥手",
        "en_name": "face wave",
        "desc": "在面前挥手示意"
    },
    7: {
        "name": "左亲吻",
        "en_name": "left kiss",
        "desc": "向左侧飞吻"
    },
    8: {
        "name": "比心",
        "en_name": "heart",
        "desc": "双手比出爱心形状"
    },
    9: {
        "name": "右比心",
        "en_name": "right heart",
        "desc": "单手比出爱心形状"
    },
    10: {
        "name": "举手",
        "en_name": "hands up",
        "desc": "双手高举过头顶"
    },
    11: {
        "name": "X光",
        "en_name": "x-ray",
        "desc": "做出X射线扫描姿势"
    },
    12: {
        "name": "右手举起",
        "en_name": "right hand up",
        "desc": "右臂向上伸展"
    },
    13: {
        "name": "拒绝",
        "en_name": "reject",
        "desc": "做出拒绝/否定的手势"
    },
    14: {
        "name": "右亲吻",
        "en_name": "right kiss",
        "desc": "向右侧飞吻"
    },
    15: {
        "name": "双手吻",
        "en_name": "two-hand kiss",
        "desc": "双手同时飞吻"
    }
}

# ============================================================
#  预设语音模板库
# ============================================================
PRESET_VOICES = {
    "greeting": {
        "label": "👋 问候语",
        "voices": [
            "您好，我是G1机器人！",
            "欢迎来到朝野科技！",
            "很高兴见到您！",
            "大家好，我是您的智能助手。",
            "Hello! Nice to meet you!"
        ]
    },
    "introduction": {
        "label": "📖 讲解介绍",
        "voices": [
            "让我为您介绍一下这里...",
            "这是我们的产品展示区。",
            "请跟随我参观。",
            "这里是公司的核心区域。",
            "接下来我将为您详细讲解。"
        ]
    },
    "interaction": {
        "label": "💬 互动交流",
        "voices": [
            "请问有什么可以帮助您的？",
            "请让一让我通过，谢谢！",
            "请注意安全。",
            "您想了解更多信息吗？",
            "好的，我明白了。"
        ]
    },
    "farewell": {
        "label": "👋 告别道别",
        "voices": [
            "再见，期待下次见面！",
            "感谢您的参观！",
            "有需要随时找我！",
            "祝您生活愉快！",
            "Bye bye! See you next time!"
        ]
    },
    "entertainment": {
        "label": "🎭 娱乐表演",
        "voices": [
            "看我给大家表演个节目！",
            "准备好了吗？我要开始啦！",
            "是不是很厉害？",
            "哈哈，好玩吧！",
            "再来一次好不好？"
        ]
    }
}


class ActionVoiceController:
    """
    G1机器人 动作+语音 控制器
    
    封装了音频系统和机械臂控制系统的初始化和操作，
    提供简洁的API供上层调用。
    """
    
    def __init__(self, network_interface):
        """
        初始化控制器
        
        Args:
            network_interface: 网络接口名称 (如 eth0, wlan0)
        """
        self.network_interface = network_interface
        self.audio_client = None
        self.arm_client = None
        self._initialized = False
        
        self._init_systems()
    
    def _init_systems(self):
        """初始化所有硬件系统"""
        print("\n" + "=" * 65)
        print("  🤖 G1 机器人 动作+语音 交互式控制器")
        print("=" * 65)
        print(f"\n  📍 网络接口: {self.network_interface}")
        print("  ⏳ 正在初始化系统...\n")
        
        # 1. 初始化 SDK 通信层
        try:
            ChannelFactoryInitialize(0, self.network_interface)
            print("  ✅ [1/3] SDK 通信层初始化完成")
        except Exception as e:
            raise RuntimeError(f"SDK初始化失败: {e}")
        
        # 2. 初始化音频客户端
        try:
            self.audio_client = AudioClient()
            self.audio_client.Init()
            self.audio_client.SetTimeout(10.0)
            self._wakeup_audio_hardware()
            print("  ✅ [2/3] 音频系统初始化完成")
        except Exception as e:
            raise RuntimeError(f"音频系统初始化失败: {e}")
        
        # 3. 初始化机械臂客户端
        try:
            self.arm_client = G1ArmActionClient()
            self.arm_client.Init()
            print("  ✅ [3/3] 机械臂控制系统初始化完成")
        except Exception as e:
            raise RuntimeError(f"机械臂系统初始化失败: {e}")
        
        self._initialized = True
        
        print("\n" + "-" * 65)
        print("  🎉 所有系统初始化成功！可以开始使用")
        print("-" * 65)
    
    def _wakeup_audio_hardware(self):
        """唤醒音频硬件（预热）"""
        print("    🔊 唤醒音频硬件中...", end=" ", flush=True)
        
        for i in range(10):
            try:
                self.audio_client.GetVolume()
                break
            except Exception:
                if i < 9:
                    time.sleep(1)
        
        self.audio_client.SetVolume(100)
        time.sleep(0.5)
        print("✓")
    
    def speak(self, text):
        """
        播放语音
        
        Args:
            text: 要朗读的文本内容
            
        Returns:
            bool: 是否播放成功
        """
        if not text or not text.strip():
            print("  ⚠️ 语音内容为空，跳过播放")
            return False
        
        text = text.strip()
        print(f"\n  🔊 语音输出:")
        print(f"     内容: \"{text}\"")
        print(f"     长度: {len(text)} 字符")
        
        try:
            start_time = time.time()
            self.audio_client.TtsMaker(text, 0)
            
            estimated_duration = len(text) * 0.195
            print(f"     ⏳  预计时长: {estimated_duration:.1f} 秒", end="", flush=True)
            
            time.sleep(estimated_duration)
            
            actual_duration = time.time() - start_time
            print(f" ✓ ({actual_duration:.1f}s)")
            print("  ✅ 语音播放完成\n")
            return True
            
        except Exception as e:
            print(f"  ❌ 语音播放失败: {e}\n")
            return False
    
    def execute_action(self, action_id):
        """
        执行单个动作（不包含语音）
        
        Args:
            action_id: 动作ID (0-15)
            
        Returns:
            bool: 是否执行成功
        """
        if action_id not in ACTIONS:
            print(f"  ❌ 无效的动作ID: {action_id}")
            print(f"     有效范围: 0 - {max(ACTIONS.keys())}")
            return False
        
        action_info = ACTIONS[action_id]
        action_en_name = action_info["en_name"]
        action_cn_name = action_info["name"]
        action_desc = action_info["desc"]
        
        print(f"\n  🎬 执行动作:")
        print(f"     ID: {action_id}")
        print(f"     名称: {action_cn_name} ({action_en_name})")
        print(f"     描述: {action_desc}")
        print(f"     ⏳  执行中...", end=" ", flush=True)
        
        try:
            start_time = time.time()
            
            # 调用机械臂API执行动作
            self.arm_client.ExecuteAction(action_map.get(action_en_name))
            
            # 等待动作完成（标准动作约需2秒）
            time.sleep(2.0)
            
            elapsed = time.time() - start_time
            print(f"✓ ({elapsed:.1f}s)")
            print("  ✅ 动作执行完成\n")
            return True
            
        except Exception as e:
            print(f"✗\n  ❌ 动作执行失败: {e}\n")
            return False
    
    def perform_interaction(self, text, action_id):
        """
        执行动作+语音组合（先动作后语音，最后复位）
        
        Args:
            text: 语音内容
            action_id: 动作ID
            
        Returns:
            bool: 整体是否成功
        """
        print(f"\n{'=' * 65}")
        print(f"  🎭 组合执行: 动作 + 语音")
        print(f"{'=' * 65}")
        
        # Step 1: 执行动作
        if not self.execute_action(action_id):
            print("  ⚠️ 动作执行失败，但继续尝试播放语音...")
        
        # Step 2: 播放语音
        if text and text.strip():
            self.speak(text)
        else:
            print("  ⚠️ 跳过语音播放（内容为空）\n")
        
        # Step 3: 自动复位手臂
        print("  🔄 正在复位手臂到初始位置...", end=" ", flush=True)
        try:
            self.arm_client.ExecuteAction(99)  # 99是复位动作ID
            time.sleep(3.0)
            print("✓")
            print("  ✅ 手臂复位完成\n")
        except Exception as e:
            print(f"✗\n  ⚠️ 手臂复位失败: {e}\n")
        
        print(f"{'=' * 65}")
        print("  ✅ 组合执行完成！\n")
        return True
    
    def reset_arm(self):
        """
        复位手臂到初始位置
        
        Returns:
            bool: 是否成功
        """
        print("\n  🔄 复位手臂...", end=" ", flush=True)
        try:
            self.arm_client.ExecuteAction(99)
            time.sleep(3.0)
            print("✓\n  ✅ 手臂已复位到初始位置\n")
            return True
        except Exception as e:
            print(f"✗\n  ❌ 复位失败: {e}\n")
            return False
    
    def test_all_actions(self):
        """
        测试所有动作（依次执行每个动作）
        用于调试和演示
        """
        print("\n" + "=" * 65)
        print("  🧪 开始测试所有动作（共 {} 个）".format(len(ACTIONS)))
        print("=" * 65 + "\n")
        
        for action_id in sorted(ACTIONS.keys()):
            action_info = ACTIONS[action_id]
            print(f"  [{action_id:2d}] {action_info['name']:<12}", end="")
            
            try:
                self.arm_client.ExecuteAction(action_map.get(action_info['en_name']))
                time.sleep(2.5)
                print(" ✓")
            except Exception as e:
                print(f" ✗ ({e})")
        
        print("\n  🔄 最后复位...")
        self.reset_arm()
        print("\n  ✅ 全部动作测试完成！\n")


# ============================================================
#  UI 显示函数
# ============================================================

def display_banner():
    """显示程序横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     🤖 G1 机器人  动作+语音  交互式控制器 v1.0           ║
║                                                           ║
║     基于 multi_nav_hys.py | 支持16种动作 + 自定义语音      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)


def display_actions_table():
    """显示动作列表表格"""
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  📋 可用动作列表                                            │")
    print("├─────────────────────────────────────────────────────────────┤")
    print("│  ID  │  动作名称       │  英文名          │  描述         │")
    print("├──────┼─────────────────┼──────────────────┼───────────────┤")
    
    for action_id, info in ACTIONS.items():
        line = f"│  {action_id:<2}  │  {info['name']:<13} │  {info['en_name']:<14} │  {info['desc']:<11} │"
        print(line)
    
    print("└─────────────────────────────────────────────────────────────┘")


def display_preset_voices():
    """显示预设语音库"""
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│  📝 预设语音模板库                                          │")
    print("├─────────────────────────────────────────────────────────────┤")
    
    for category, data in PRESET_VOICES.items():
        print(f"│  【{data['label']}】")
        for idx, voice in enumerate(data['voices'], 1):
            print(f"│    {idx}. {voice}")
        print("│")
    
    print("└─────────────────────────────────────────────────────────────┘")


def display_help():
    """显示帮助信息"""
    help_text = """
  ┌──────────────────────────────────────────────────────────────┐
  │  🎮 操作指南                                                 │
  ├──────────────────────────────────────────────────────────────┤
  │                                                              │
  │  基本操作:                                                    │
  │    • 输入数字 (0-15)     → 执行对应动作                       │
  │    • 输入文本            → 仅播放语音                         │
  │                                                              │
  │  高级操作:                                                    │
  │    • c                   → 进入【组合模式】(动作+语音)         │
  │    • r                   → 复位手臂                           │
  │    • t                   → 测试所有动作（依次执行）            │
  │    • h                   → 显示此帮助                         │
  │    • q / Ctrl+C          → 退出程序                          │
  │                                                              │
  │  示例:                                                        │
  │    > 8              # 执行"比心"动作                          │
  │    > 您好           # 播放语音"您好"                          │
  │    > c              # 进入组合模式                            │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
"""
    print(help_text)


def get_valid_input(prompt, validator=None, error_msg="无效输入"):
    """
    获取有效的用户输入
    
    Args:
        prompt: 提示文字
        validator: 验证函数 (str -> bool)
        error_msg: 错误提示
        
    Returns:
        str: 用户输入
    """
    while True:
        user_input = input(prompt).strip()
        
        if validator is None or validator(user_input):
            return user_input
        
        print(f"  ❌ {error_msg}")


# ============================================================
#  主程序
# ============================================================

def main():
    """主交互循环"""
    
    # 检查参数
    if len(sys.argv) < 2:
        print("\n❌ 使用方法: python3 action_voice_interactor.py <网络接口>")
        print("   示例: python3 action_voice_interactor.py eth0")
        print("   可用接口: eth0, wlan0, lo 等\n")
        sys.exit(1)
    
    network_interface = sys.argv[1]
    
    # 显示UI
    display_banner()
    
    # 初始化ROS节点（如果尚未初始化）
    try:
        rospy.init_node('action_voice_interactor', anonymous=True)
    except Exception as e:
        print(f"  ⚠️ ROS节点初始化警告: {e}")
    
    # 初始化控制器
    try:
        controller = ActionVoiceController(network_interface)
    except Exception as e:
        print(f"\n  ❌ 系统初始化失败: {e}")
        print("  请检查:")
        print("    1. 网络接口是否正确 (eth0/wlan0)")
        print("    2. G1机器人是否开机并连接")
        print("    3. ROS环境是否正常运行\n")
        sys.exit(1)
    
    # 显示动作列表和预设语音
    display_actions_table()
    display_preset_voices()
    display_help()
    
    # 主循环
    print("\n  💡 准备就绪！请输入操作指令 (h=帮助, q=退出):\n")
    
    while True:
        try:
            user_input = input("  👉 ").strip()
            
            # 空输入处理
            if not user_input:
                continue
            
            # ===== 退出程序 =====
            if user_input.lower() == 'q':
                print("\n  👋 感谢使用 G1 动作+语音控制器！再见！\n")
                break
            
            # ===== 显示帮助 =====
            elif user_input.lower() == 'h':
                display_help()
                continue
            
            # ===== 复位手臂 =====
            elif user_input.lower() == 'r':
                controller.reset_arm()
                continue
            
            # ===== 测试所有动作 =====
            elif user_input.lower() == 't':
                confirm = input("  ⚠️  确定要测试所有动作吗? 这会依次执行16个动作 [y/N]: ").strip().lower()
                if confirm == 'y':
                    controller.test_all_actions()
                else:
                    print("  已取消\n")
                continue
            
            # ===== 组合模式 (动作 + 语音) =====
            elif user_input.lower() == 'c':
                enter_combination_mode(controller)
                continue
            
            # ===== 执行单独动作 (输入数字) =====
            elif user_input.isdigit():
                action_id = int(user_input)
                if action_id in ACTIONS:
                    controller.execute_action(action_id)
                    
                    # 询问是否复位
                    auto_reset = input("  🔄 是否自动复位? [Y/n]: ").strip().lower()
                    if auto_reset != 'n':
                        controller.reset_arm()
                else:
                    print(f"  ❌ 无效的动作ID: {action_id} (有效范围: 0-{max(ACTIONS.keys())})\n")
                continue
            
            # ===== 仅播放语音 (输入文本) =====
            else:
                controller.speak(user_input)
                continue
                
        except KeyboardInterrupt:
            print("\n\n  ⚠️  检测到 Ctrl+C，正在安全退出...\n")
            break
        except Exception as e:
            print(f"\n  ❌ 发生未预期的错误: {e}\n")
            import traceback
            traceback.print_exc()
            continue


def enter_combination_mode(controller):
    """
    进入组合模式：选择动作 + 选择/输入语音
    
    Args:
        controller: ActionVoiceController实例
    """
    print("\n" + "=" * 65)
    print("  🎭 【组合模式】动作 + 语音")
    print("=" * 65)
    
    # ---- 步骤1: 选择动作 ----
    print("\n  步骤 1/2: 选择动作")
    print("  " + "-" * 40)
    
    action_input = input("  🎬 请输入动作ID (0-15, h=查看列表): ").strip()
    
    if action_input.lower() == 'h':
        display_actions_table()
        action_input = input("  🎬 请输入动作ID: ").strip()
    
    try:
        action_id = int(action_input)
        if action_id not in ACTIONS:
            print(f"  ❌ 无效的动作ID: {action_id}\n")
            return
    except ValueError:
        print("  ❌ 请输入有效的数字\n")
        return
    
    selected_action = ACTIONS[action_id]
    print(f"  ✅ 已选择: [{action_id}] {selected_action['name']} - {selected_action['desc']}")
    
    # ---- 步骤2: 选择/输入语音 ----
    print("\n  步骤 2/2: 选择语音内容")
    print("  " + "-" * 40)
    print("  语音来源:")
    print("    1. 使用预设语音模板")
    print("    2. 自定义输入语音内容")
    print("    3. 跳过（仅执行动作）")
    
    voice_choice = input("  🔊 请选择 [1/2/3]: ").strip()
    
    text = None
    
    if voice_choice == '1':
        # 使用预设语音
        print("\n  📂 可用预设分类:")
        categories = list(PRESET_VOICES.keys())
        for idx, cat in enumerate(categories, 1):
            label = PRESET_VOICES[cat]['label']
            print(f"    {idx}. {label}")
        
        cat_input = input("  👉 请选择分类编号: ").strip()
        
        try:
            cat_idx = int(cat_input) - 1
            if 0 <= cat_idx < len(categories):
                selected_cat = categories[cat_idx]
                voices = PRESET_VOICES[selected_cat]['voices']
                
                print(f"\n  📝 [{PRESET_VOICES[selected_cat]['label']}] 可选语音:")
                for idx, voice in enumerate(voices, 1):
                    print(f"    {idx}. {voice}")
                
                voice_input = input("  👉 请选择语音编号: ").strip()
                
                try:
                    v_idx = int(voice_input) - 1
                    if 0 <= v_idx < len(voices):
                        text = voices[v_idx]
                        print(f"  ✅ 已选择: \"{text}\"")
                    else:
                        print(f"  ⚠️ 无效编号，使用默认第一条")
                        text = voices[0]
                except ValueError:
                    text = voices[0]
            else:
                print("  ⚠️ 无效分类，切换到自定义输入")
                text = input("  ✏️ 请输入语音内容: ").strip()
        except ValueError:
            text = input("  ✏️ 请输入语音内容: ").strip()
    
    elif voice_choice == '2':
        # 自定义输入
        text = input("  ✏️ 请输入语音内容: ").strip()
        if text:
            print(f"  ✅ 已输入: \"{text}\"")
    
    elif voice_choice == '3':
        # 跳过语音
        print("  ⏭️  将仅执行动作，跳过语音播放")
    
    else:
        print("  ⚠️ 无效选择，默认跳过语音")
    
    # ---- 确认执行 ----
    print("\n  " + "-" * 40)
    print("  📋 执行确认:")
    print(f"     动作: [{action_id}] {selected_action['name']}")
    if text:
        print(f"     语音: \"{text}\"")
    else:
        print(f"     语音: (无)")
    
    confirm = input("\n  ▶️  确认执行? [Y/n]: ").strip().lower()
    
    if confirm == 'n':
        print("  ❌ 已取消执行\n")
        return
    
    # ---- 执行组合 ----
    if text:
        controller.perform_interaction(text, action_id)
    else:
        controller.execute_action(action_id)
        controller.reset_arm()


# ============================================================
#  程序入口
# ============================================================

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        print("\n  ⚠️ ROS节点被中断，程序退出\n")
    except Exception as e:
        print(f"\n  💥 程序异常终止: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

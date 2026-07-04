#!/usr/bin/env python3
"""
G1 键盘遥控器 (运动 + 机械臂 + 模式切换)
- 功能：通过键盘控制机器人运动、机械臂动作、FSM模式切换
- 用法：python3 g1_keyboard_teleop.py eth0

运动控制：
  W/S    - 前进/后退
  A/D    - 左移/右移
  Q/E    - 左转/右转
  Space  - 急停
  ,/.    - 降档/升档
  R      - 复位速度归零

模式切换（按F进入FSM模式后按数字键）：
  F      - 切换 Arm/FSM 模式
  FSM模式下：
    0-零力矩  1-阻尼  3-坐下  4-预备  5-走路  6-启动  7-躺起  8-蹲站  9-走跑

机械臂动作（Arm模式下按数字键，默认Arm模式）：
  0      - 释放手臂        1  - 握手
  2      - 举手你好        3  - 拥抱
  4      - 拜拜挥手        5  - 鼓掌
  6      - 低位挥手        7  - 左飞吻
  8      - 比心            9  - 右比心
  Z      - 双手举起       X  - 迪迦光线
  C      - 右手举起       V  - 拒绝
  B      - 右飞吻         N  - 双手飞吻
  Ctrl+C - 退出
"""

import sys
import time
import select
import termios
import tty
import threading
import json

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_


ARM_ACTIONS = [
    {"id": 0,  "key": "0", "name": "release arm",    "map": "release arm",    "need_release": False, "desc": "释放手臂"},
    {"id": 1,  "key": "1", "name": "shake hand",     "map": "shake hand",     "need_release": True,  "desc": "握手"},
    {"id": 2,  "key": "2", "name": "high five",      "map": "high five",      "need_release": True,  "desc": "举手你好"},
    {"id": 3,  "key": "3", "name": "hug",            "map": "hug",            "need_release": True,  "desc": "拥抱"},
    {"id": 4,  "key": "4", "name": "high wave",      "map": "high wave",      "need_release": False, "desc": "拜拜挥手"},
    {"id": 5,  "key": "5", "name": "clap",           "map": "clap",           "need_release": False, "desc": "鼓掌"},
    {"id": 6,  "key": "6", "name": "face wave",      "map": "face wave",      "need_release": False, "desc": "低位挥手"},
    {"id": 7,  "key": "7", "name": "left kiss",      "map": "left kiss",      "need_release": False, "desc": "左飞吻"},
    {"id": 8,  "key": "8", "name": "heart",          "map": "heart",          "need_release": True,  "desc": "比心"},
    {"id": 9,  "key": "9", "name": "right heart",    "map": "right heart",    "need_release": True,  "desc": "右比心"},
    {"id": 10, "key": "z", "name": "hands up",       "map": "hands up",       "need_release": True,  "desc": "双手举起"},
    {"id": 11, "key": "x", "name": "x-ray",          "map": "x-ray",          "need_release": True,  "desc": "迪迦光线"},
    {"id": 12, "key": "c", "name": "right hand up",  "map": "right hand up",  "need_release": True,  "desc": "右手举起"},
    {"id": 13, "key": "v", "name": "reject",         "map": "reject",         "need_release": True,  "desc": "拒绝"},
    {"id": 14, "key": "b", "name": "right kiss",     "map": "right kiss",     "need_release": False, "desc": "右飞吻"},
    {"id": 15, "key": "n", "name": "two-hand kiss",  "map": "two-hand kiss",  "need_release": False, "desc": "双手飞吻"},
]

KEY_TO_ACTION = {}
for a in ARM_ACTIONS:
    KEY_TO_ACTION[a["key"]] = a

FSM_MODES = {
    "0": {"id": 0,   "desc": "零力矩",     "name": "ZeroTorque"},
    "1": {"id": 1,   "desc": "阻尼模式",   "name": "Damp"},
    "3": {"id": 3,   "desc": "坐下",       "name": "Sit"},
    "4": {"id": 4,   "desc": "预备模式",   "name": "Ready"},
    "5": {"id": 501, "desc": "常规走路",   "name": "Walk"},
    "6": {"id": 200, "desc": "启动运动",   "name": "Start"},
    "7": {"id": 702, "desc": "躺→站",     "name": "Lie2StandUp"},
    "8": {"id": 706, "desc": "蹲↔站",     "name": "Squat2Stand"},
    "9": {"id": 802, "desc": "走跑模式",   "name": "Run"},
}


class KeyboardTeleop:
    def __init__(self, network_interface):
        print("=" * 55)
        print("   G1 键盘遥控器 (运动+机械臂+模式)")
        print("=" * 55)

        try:
            ChannelFactoryInitialize(0, network_interface)
        except Exception as e:
            print(f"[ERROR] 网络初始化失败: {e}")
            sys.exit(-1)

        self.sport_client = LocoClient()
        self.sport_client.SetTimeout(10.0)
        try:
            self.sport_client.Init()
        except Exception as e:
            print(f"[ERROR] 运动客户端连接失败: {e}")
            sys.exit(-1)

        self.arm_client = G1ArmActionClient()
        self.arm_client.SetTimeout(10.0)
        try:
            self.arm_client.Init()
            print("  ✅ 机械臂客户端初始化成功")
        except Exception as e:
            print(f"  ⚠️  机械臂客户端初始化失败: {e}")
            self.arm_client = None

        self.odom_dds_sub = ChannelSubscriber("rt/odommodestate", SportModeState_)
        self.odom_dds_sub.Init(self._dds_odom_callback)

        self.current_vx = 0.0
        self.current_vy = 0.0
        self.current_wz = 0.0

        self.target_vx = 0.0
        self.target_vy = 0.0
        self.target_wz = 0.0

        self.gear_speeds = {
            1: {"vx": 0.3, "vy": 0.2, "wz": 0.4},
            2: {"vx": 0.6, "vy": 0.3, "wz": 0.8},
            3: {"vx": 1.0, "vy": 0.5, "wz": 1.2},
        }
        self.current_gear = 1

        self.smoothing = 0.15
        self.stop_threshold = 0.005
        self.running = True
        self.arm_executing = False
        self.arm_lock = threading.Lock()

        self.key_mode = "arm"

        self._print_help()

    def _dds_odom_callback(self, msg: SportModeState_):
        self.current_vx = msg.velocity[0]
        self.current_vy = msg.velocity[1]
        self.current_wz = msg.yaw_speed

    def _print_help(self):
        print("\n  ┌─ 运动控制 ──────────────────────┐")
        print("  │ W/S    前进/后退                 │")
        print("  │ A/D    左移/右移                 │")
        print("  │ Q/E    左转/右转                 │")
        print("  │ Space  急停                      │")
        print("  │ ,/.    降档/升档                 │")
        print("  │ R      速度归零                  │")
        print("  ├─ 模式切换 (按F切换) ────────────┤")
        print("  │ F      切换 Arm/FSM 模式         │")
        print("  │ FSM模式:                         │")
        print("  │   0零力矩 1阻尼 3坐下 4预备      │")
        print("  │   5走路   6启动 7躺起 8蹲站 9走跑│")
        print("  ├─ 机械臂 (Arm模式，默认) ────────┤")
        print("  │ 0释放 1握手 2举手 3拥抱 4拜拜    │")
        print("  │ 5鼓掌 6低位 7飞吻 8比心 9右比心  │")
        print("  │ Z双手 X迪迦 C右手 V拒绝          │")
        print("  │ B右飞吻 N双手飞吻                │")
        print("  └──────────────────────────────────┘\n")

    def _get_key(self):
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None

    def _smooth_step(self, current, target):
        if abs(target - current) < self.stop_threshold:
            return target
        return current + (target - current) * self.smoothing

    def _execute_arm_action(self, action_info):
        if self.arm_client is None:
            print("  ⚠️  机械臂未初始化，无法执行动作")
            return

        with self.arm_lock:
            if self.arm_executing:
                print("  ⏳ 机械臂正在执行动作，请稍候...")
                return
            self.arm_executing = True

        def _run():
            try:
                action_name = action_info["name"]
                action_map_key = action_info["map"]
                need_release = action_info["need_release"]
                desc = action_info["desc"]

                print(f"\n  🤖 执行动作: {desc} ({action_name})")

                self.arm_client.ExecuteAction(action_map.get(action_map_key))

                if need_release:
                    time.sleep(2.0)
                    self.arm_client.ExecuteAction(action_map.get("release arm"))
                    print("  🔄 手臂已复位")

            except Exception as e:
                print(f"  ❌ 动作执行失败: {e}")
            finally:
                with self.arm_lock:
                    self.arm_executing = False

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _set_fsm(self, key: str):
        mode = FSM_MODES.get(key)
        if mode is None:
            print(f"  ❌ 无FSM映射: {key}")
            return

        fsm_id = mode["id"]
        desc = mode["desc"]
        name = mode["name"]

        print(f"\n  🔄 FSM → {fsm_id} ({desc}/{name})")
        code = self.sport_client.SetFsmId(fsm_id)
        if code == 0:
            print(f"  ✅ 切换成功")
        else:
            print(f"  ❌ 切换失败 (code: {code})")

    def process_key(self, key):
        key_lower = key.lower()

        if key_lower == 'f':
            if self.key_mode == "arm":
                self.key_mode = "fsm"
                print("\n  🔀 切换到 FSM 模式 (数字键切换运动状态)")
            else:
                self.key_mode = "arm"
                print("\n  🔀 切换到 Arm 模式 (数字键执行手臂动作)")
            return

        if self.key_mode == "fsm" and key_lower in FSM_MODES:
            self._set_fsm(key_lower)
            return

        if self.key_mode == "arm":
            action_info = KEY_TO_ACTION.get(key_lower)
            if action_info:
                self._execute_arm_action(action_info)
                return

        gear = self.gear_speeds[self.current_gear]

        if key == 'w' or key == 'W':
            self.target_vx = gear["vx"]
        elif key == 's' or key == 'S':
            self.target_vx = -gear["vx"]
        elif key == 'a' or key == 'A':
            self.target_vy = gear["vy"]
        elif key == 'd' or key == 'D':
            self.target_vy = -gear["vy"]
        elif key == 'q' or key == 'Q':
            self.target_wz = gear["wz"]
        elif key == 'e' or key == 'E':
            self.target_wz = -gear["wz"]
        elif key == ' ':
            self.target_vx = 0.0
            self.target_vy = 0.0
            self.target_wz = 0.0
            self.sport_client.StopMove()
            print("  🛑 急停！")
        elif key == ',':
            if self.current_gear > 1:
                self.current_gear -= 1
                gear_names = {1: "低速", 2: "中速", 3: "高速"}
                print(f"  ⚙️  档位: {self.current_gear} ({gear_names[self.current_gear]})")
        elif key == '.':
            if self.current_gear < 3:
                self.current_gear += 1
                gear_names = {1: "低速", 2: "中速", 3: "高速"}
                print(f"  ⚙️  档位: {self.current_gear} ({gear_names[self.current_gear]})")
        elif key == 'r' or key == 'R':
            self.target_vx = 0.0
            self.target_vy = 0.0
            self.target_wz = 0.0
            print("  🔄 速度归零")

    def _print_status(self):
        gear_names = {1: "低速", 2: "中速", 3: "高速"}
        arm_status = "🤖执行中" if self.arm_executing else "🤖空闲"
        mode_tag = "FSM" if self.key_mode == "fsm" else "Arm"
        print(
            f"\r  "
            f"[{mode_tag}] "
            f"档位:{self.current_gear}({gear_names[self.current_gear]}) | "
            f"目标:({self.target_vx:+.2f},{self.target_vy:+.2f},{self.target_wz:+.2f}) | "
            f"实际:({self.current_vx:+.2f},{self.current_vy:+.2f},{self.current_wz:+.2f}) | "
            f"{arm_status}   ",
            end="", flush=True
        )

    def run(self):
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())

            send_vx = 0.0
            send_vy = 0.0
            send_wz = 0.0

            last_key_time = time.time()
            key_timeout = 0.3

            print("  🚀 键盘遥控已启动，请按键控制...\n")

            while self.running:
                key = self._get_key()

                if key:
                    if key == '\x03':
                        break
                    self.process_key(key)
                    last_key_time = time.time()
                else:
                    now = time.time()
                    if now - last_key_time > key_timeout:
                        self.target_vx *= 0.85
                        self.target_vy *= 0.85
                        self.target_wz *= 0.85
                        if (abs(self.target_vx) < 0.02 and
                                abs(self.target_vy) < 0.02 and
                                abs(self.target_wz) < 0.02):
                            self.target_vx = 0.0
                            self.target_vy = 0.0
                            self.target_wz = 0.0

                send_vx = self._smooth_step(send_vx, self.target_vx)
                send_vy = self._smooth_step(send_vy, self.target_vy)
                send_wz = self._smooth_step(send_wz, self.target_wz)

                if (abs(send_vx) < self.stop_threshold and
                        abs(send_vy) < self.stop_threshold and
                        abs(send_wz) < self.stop_threshold):
                    self.sport_client.StopMove()
                else:
                    self.sport_client.Move(send_vx, send_vy, send_wz)

                self._print_status()
                time.sleep(0.02)

        except Exception as e:
            print(f"\n  [ERROR] {e}")
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self.sport_client.StopMove()
            if self.arm_client:
                try:
                    self.arm_client.ExecuteAction(action_map.get("release arm"))
                except:
                    pass
            print("\n\n  👋 键盘遥控已退出，机器人已停止。")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 g1_keyboard_teleop.py <network_interface>")
        print("Example: python3 g1_keyboard_teleop.py eth0")
        sys.exit(-1)

    teleop = KeyboardTeleop(sys.argv[1])
    teleop.run()

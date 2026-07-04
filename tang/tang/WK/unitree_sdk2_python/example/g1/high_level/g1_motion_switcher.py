#!/usr/bin/env python3
"""
G1 运动模式切换工具
- 功能：通过FSM ID切换机器人运动模式
- 用法：python3 g1_motion_switcher.py eth0

模式说明：
  0   - 零力矩 (ZeroTorque)
  1   - 阻尼模式 (Damp)
  3   - 坐下 (Sit)
  4   - 预备模式 (Ready)
  200 - 启动运动 (Start)
  501 - 常规走路模式 (Walk)
  702 - 躺→站 (Lie2StandUp)
  706 - 蹲↔站 (Squat2StandUp)
  802 - 走跑模式 (Run)
"""

import sys
import json
import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient


FSM_MODES = {
    0:   {"name": "ZeroTorque",  "desc": "零力矩",     "group": "基础"},
    1:   {"name": "Damp",        "desc": "阻尼模式",   "group": "基础"},
    3:   {"name": "Sit",         "desc": "坐下",       "group": "姿态"},
    4:   {"name": "Ready",       "desc": "预备模式",   "group": "姿态"},
    200: {"name": "Start",       "desc": "启动运动",   "group": "运动"},
    501: {"name": "Walk",        "desc": "常规走路",   "group": "运动"},
    702: {"name": "Lie2StandUp", "desc": "躺→站",     "group": "姿态"},
    706: {"name": "Squat2Stand", "desc": "蹲↔站",     "group": "姿态"},
    802: {"name": "Run",         "desc": "走跑模式",   "group": "运动"},
}


def print_banner():
    print("=" * 50)
    print("   G1 运动模式切换工具")
    print("=" * 50)


def print_modes():
    print("\n  可用模式:")
    print("  " + "-" * 46)
    last_group = None
    for fid, info in sorted(FSM_MODES.items()):
        if info["group"] != last_group:
            print(f"  [{info['group']}]")
            last_group = info["group"]
        print(f"    {fid:<6} {info['desc']:<12} ({info['name']})")
    print("  " + "-" * 46)


def print_commands():
    print("\n  命令:")
    print("  " + "-" * 46)
    print("  <数字>   切换到对应FSM模式")
    print("  check    查询当前FSM ID")
    print("  list     列出所有模式")
    print("  quit     退出")
    print("  " + "-" * 46 + "\n")


def check_fsm(loco: LocoClient):
    try:
        code, data = loco._Call(7001, json.dumps({}))
        if code == 0 and data:
            parsed = json.loads(data) if isinstance(data, str) else data
            fsm_id = parsed.get("data", parsed) if isinstance(parsed, dict) else parsed
            fsm_id = int(fsm_id) if isinstance(fsm_id, (int, float)) else fsm_id
            info = FSM_MODES.get(fsm_id)
            if info:
                print(f"  📋 当前: FSM ID = {fsm_id} → {info['desc']} ({info['name']})")
            else:
                print(f"  📋 当前: FSM ID = {fsm_id} (未知)")
            return fsm_id
        else:
            print(f"  ❌ 查询失败 (code: {code})")
            return None
    except Exception as e:
        print(f"  ❌ 查询失败: {e}")
        return None


def set_fsm(loco: LocoClient, fsm_id: int):
    info = FSM_MODES.get(fsm_id)
    if info:
        desc = f"{info['desc']} ({info['name']})"
    else:
        desc = "未知模式"

    print(f"  🔄 切换到 FSM ID = {fsm_id} ({desc})...")
    code = loco.SetFsmId(fsm_id)

    if code == 0:
        print(f"  ✅ 切换成功")
    else:
        print(f"  ❌ 切换失败 (code: {code})")

    time.sleep(0.3)
    check_fsm(loco)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <network_interface>")
        print(f"Example: python3 {sys.argv[0]} eth0")
        sys.exit(-1)

    print_banner()

    try:
        ChannelFactoryInitialize(0, sys.argv[1])
    except Exception as e:
        print(f"[ERROR] 网络初始化失败: {e}")
        sys.exit(-1)

    loco = LocoClient()
    loco.SetTimeout(10.0)
    try:
        loco.Init()
        print("  ✅ LocoClient 初始化成功")
    except Exception as e:
        print(f"[ERROR] 初始化失败: {e}")
        sys.exit(-1)

    print_modes()
    print_commands()

    print("  🔍 当前状态:")
    check_fsm(loco)
    print()

    while True:
        try:
            cmd = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue

        if cmd in ("quit", "exit", "q"):
            break
        elif cmd in ("check", "c"):
            check_fsm(loco)
        elif cmd in ("list", "l"):
            print_modes()
        else:
            try:
                fsm_id = int(cmd)
                set_fsm(loco, fsm_id)
            except ValueError:
                print(f"  ❌ 无效输入: {cmd}")

        print()

    print("  👋 已退出")


if __name__ == "__main__":
    main()

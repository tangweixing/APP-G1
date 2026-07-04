#!/usr/bin/env python3
"""
G1 FSM ID 实时监听器
- 功能：持续监听当前FSM ID变化并打印
- 用法：python3 g1_fsm_explorer.py eth0
- 使用：启动后用官方遥控器切换模式，脚本会自动显示当前FSM ID
"""

import sys
import json
import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient


KNOWN_IDS = {
    0: "ZeroTorque (零力矩)",
    1: "Damp (阻尼)",
    3: "Sit (坐下)",
    200: "Start (启动运动)",
    702: "Lie2StandUp (躺→站)",
    706: "Squat2StandUp (蹲↔站)",
}


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <network_interface>")
        sys.exit(-1)

    print("=" * 45)
    print("  G1 FSM ID 实时监听器")
    print("  用遥控器切换模式，ID变化会自动显示")
    print("  Ctrl+C 退出")
    print("=" * 45)

    try:
        ChannelFactoryInitialize(0, sys.argv[1])
    except Exception as e:
        print(f"[ERROR] 网络初始化失败: {e}")
        sys.exit(-1)

    loco = LocoClient()
    loco.SetTimeout(10.0)
    try:
        loco.Init()
    except Exception as e:
        print(f"[ERROR] 初始化失败: {e}")
        sys.exit(-1)

    last_id = None

    while True:
        try:
            code, data = loco._Call(7001, json.dumps({}))
            if code == 0 and data:
                parsed = json.loads(data) if isinstance(data, str) else data
                fsm_id = parsed.get("data", parsed) if isinstance(parsed, dict) else parsed
                fsm_id = int(fsm_id) if isinstance(fsm_id, (int, float)) else fsm_id

                if fsm_id != last_id:
                    known = KNOWN_IDS.get(fsm_id, "")
                    tag = f" → {known}" if known else " (未知)"
                    print(f"  FSM ID: {fsm_id}{tag}")
                    last_id = fsm_id
        except KeyboardInterrupt:
            break
        except:
            pass

        time.sleep(0.1)

    print("\n  退出监听")


if __name__ == "__main__":
    main()

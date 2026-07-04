#!/usr/bin/env python3
"""
G1 简单手臂动作 - 左臂微弯（极简稳定版）
- 只控制左臂(7个关节)，右臂/腰部/腿部完全不碰
- 低刚度(kp=30)柔和运动，减少对平衡器的冲击
- 动作幅度极小，避免重心偏移引起腿部调整
- 用法: python3 g1_simple_arm.py eth0
"""

import time
import sys
import signal
import numpy as np

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from unitree_sdk2py.core.channel import ChannelSubscriber
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_
from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread

# ==================== 关节索引 ====================
class J:
    LeftHipPitch = 0;   LeftHipRoll = 1;    LeftHipYaw = 2
    LeftKnee = 3;       LeftAnklePitch = 4;  LeftAnkleRoll = 5
    RightHipPitch = 6;  RightHipRoll = 7;    RightHipYaw = 8
    RightKnee = 9;      RightAnklePitch = 10; RightAnkleRoll = 11
    WaistYaw = 12;      WaistRoll = 13;      WaistPitch = 14
    LShoulderPitch = 15; LShoulderRoll = 16; LShoulderYaw = 17
    LElbow = 18;        LWristRoll = 19;     LWristPitch = 20; LWristYaw = 21
    RShoulderPitch = 22; RShoulderRoll = 23; RShoulderYaw = 24
    RElbow = 25;        RWristRoll = 26;     RWristPitch = 27; RWristYaw = 28
    kNotUsedJoint = 29


class SimpleArmController:
    """只控制左臂7个关节，其他全由G1内部控制"""

    # 左臂关节索引
    ARM_JOINTS = [
        J.LShoulderPitch, J.LShoulderRoll, J.LShoulderYaw,
        J.LElbow,
        J.LWristRoll, J.LWristPitch, J.LWristYaw,
    ]

    def __init__(self):
        self.ctrl_dt = 0.02
        self.kp = 30.0       # 低刚度 = 柔和运动
        self.kd = 1.0        # 低阻尼
        self.low_cmd = unitree_hg_msg_dds__LowCmd_()
        self.low_state = None
        self.first_update = False
        self.crc = CRC()
        self.done = False
        self.time_ = 0.0
        self._arm_init = None   # 左臂初始位置

    def Init(self, network_interface):
        ChannelFactoryInitialize(0, network_interface)
        self.pub = ChannelPublisher("rt/arm_sdk", LowCmd_)
        self.pub.Init()
        self.sub = ChannelSubscriber("rt/lowstate", LowState_)
        self.sub.Init(self._state_cb, 10)

    def _state_cb(self, msg):
        self.low_state = msg
        if not self.first_update:
            self._arm_init = {j: msg.motor_state[j].q for j in self.ARM_JOINTS}
            self.first_update = True

    def Start(self):
        print("等待机器人状态...")
        while not self.first_update:
            time.sleep(0.1)
        print("状态已同步，开始执行")
        self.thread = RecurrentThread(
            interval=self.ctrl_dt, target=self._control_loop, name="arm_ctrl"
        )
        self.thread.Start()

    def emergency_release(self):
        """紧急释放控制权"""
        self.done = True
        self.low_cmd.motor_cmd[J.kNotUsedJoint].q = 0
        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.pub.Write(self.low_cmd)
        print("[紧急] 已释放控制权")

    def _control_loop(self):
        self.time_ += self.ctrl_dt
        t = self.time_

        if t < 3.0:
            # Stage 1: 获取控制权 (0~3s), 左臂保持原位不动
            self.low_cmd.motor_cmd[J.kNotUsedJoint].q = np.clip(t / 3.0, 0, 1)
            for joint in self.ARM_JOINTS:
                q = self._arm_init.get(joint, 0)
                self.low_cmd.motor_cmd[joint].tau = 0
                self.low_cmd.motor_cmd[joint].q = q
                self.low_cmd.motor_cmd[joint].dq = 0
                self.low_cmd.motor_cmd[joint].kp = self.kp
                self.low_cmd.motor_cmd[joint].kd = self.kd

        elif t < 6.0:
            # Stage 2: 左臂微弯 (3~6s)
            ratio = np.clip((t - 3.0) / 3.0, 0, 1)
            init = self._arm_init
            targets = {
                J.LShoulderPitch: init[J.LShoulderPitch] + 0.10,
                J.LShoulderRoll:  init[J.LShoulderRoll] + 0.15,
                J.LShoulderYaw:   init[J.LShoulderYaw] - 0.05,
                J.LElbow:         init[J.LElbow] - 0.35,
                J.LWristRoll:     init[J.LWristRoll],
                J.LWristPitch:    init[J.LWristPitch],
                J.LWristYaw:      init[J.LWristYaw],
            }
            for joint in self.ARM_JOINTS:
                target = targets[joint]
                current = self.low_state.motor_state[joint].q
                self.low_cmd.motor_cmd[joint].tau = 0
                self.low_cmd.motor_cmd[joint].q = ratio * target + (1 - ratio) * current
                self.low_cmd.motor_cmd[joint].dq = 0
                self.low_cmd.motor_cmd[joint].kp = self.kp
                self.low_cmd.motor_cmd[joint].kd = self.kd

        elif t < 8.0:
            # Stage 3: 保持 (6~8s)
            for joint in self.ARM_JOINTS:
                self.low_cmd.motor_cmd[joint].tau = 0
                self.low_cmd.motor_cmd[joint].q = self.low_state.motor_state[joint].q
                self.low_cmd.motor_cmd[joint].dq = 0
                self.low_cmd.motor_cmd[joint].kp = self.kp
                self.low_cmd.motor_cmd[joint].kd = self.kd

        elif t < 11.0:
            # Stage 4: 回到原位 + 释放 (8~11s)
            ratio = np.clip((t - 8.0) / 3.0, 0, 1)
            for joint in self.ARM_JOINTS:
                current = self.low_state.motor_state[joint].q
                init_q = self._arm_init.get(joint, 0)
                self.low_cmd.motor_cmd[joint].tau = 0
                self.low_cmd.motor_cmd[joint].q = (1 - ratio) * current + ratio * init_q
                self.low_cmd.motor_cmd[joint].dq = 0
                self.low_cmd.motor_cmd[joint].kp = self.kp
                self.low_cmd.motor_cmd[joint].kd = self.kd
            self.low_cmd.motor_cmd[J.kNotUsedJoint].q = 1 - ratio

        else:
            self.done = True

        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.pub.Write(self.low_cmd)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"用法: python3 {sys.argv[0]} <网络接口>")
        print(f"示例: python3 {sys.argv[0]} eth0")
        sys.exit(-1)

    ctrl = SimpleArmController()

    def on_signal(signum, frame):
        ctrl.emergency_release()
        sys.exit(0)
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    print("=" * 45)
    print("  G1 简单手臂动作 - 左臂微弯")
    print("  只控左臂(7关节)，其他全由G1控制")
    print("=" * 45)
    print("\nWARNING: 请确保机器人周围无障碍物!")
    input("按 Enter 开始...")

    ctrl.Init(sys.argv[1])
    ctrl.Start()

    while True:
        time.sleep(0.5)
        if ctrl.done:
            print("\n完成！")
            break

#!/usr/bin/env python3
"""
G1 动作控制器 (Python版)
- 功能：在机器人站立时控制上半身做动作（如比耶、抬手）
- 支持：按ID加载/保存/执行动作，JSON持久化存储
- 安全：自动锁定腿部关节，保持站立姿态
- 用法：
    python3 g1_action.py eth0                    # 执行默认动作序列
    python3 g1_action.py eth0 --action peace_sign # 按ID执行单个动作
    python3 g1_action.py eth0 --list              # 列出所有已保存动作
    python3 g1_action.py eth0 --save-builtin      # 保存预置动作到文件
"""

import sys
import time
import math
import numpy as np

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber, ChannelPublisher
from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_  # 默认初始化函数

from action_manager import ActionManager, Action, save_builtin_actions


# ==================== 常量定义 ====================
TOPIC_ARM_SDK = "rt/arm_sdk"
TOPIC_LOWSTATE = "rt/lowstate"
CTRL_DT = 0.02  # 20ms 控制周期

# 关节索引 (与 C++ 版本一致)
class JointIndex:
    # 左腿
    LeftHipPitch = 0
    LeftHipRoll = 1
    LeftHipYaw = 2
    LeftKnee = 3
    LeftAnkle = 4
    LeftAnkleRoll = 5
    # 右腿
    RightHipPitch = 6
    RightHipRoll = 7
    RightHipYaw = 8
    RightKnee = 9
    RightAnkle = 10
    RightAnkleRoll = 11
    # 腰部
    WaistYaw = 12
    WaistRoll = 13
    WaistPitch = 14
    # 左臂
    LeftShoulderPitch = 15
    LeftShoulderRoll = 16
    LeftShoulderYaw = 17
    LeftElbowPitch = 18
    LeftElbowRoll = 19
    # 右臂
    RightShoulderPitch = 22
    RightShoulderRoll = 23
    RightShoulderYaw = 24
    RightElbowPitch = 25
    RightElbowRoll = 26
    # 权重控制
    NotUsedJoint = 29


# ==================== 动作控制器类 ====================
class G1ActionController:
    def __init__(self, network_interface, skip_channel_init=False, action_dir="./actions"):
        print("=" * 50)
        print("Initializing G1 Action Controller...")
        print("=" * 50)

        # 【修改】支持跳过 ChannelFactory 初始化（避免重复初始化冲突）
        if not skip_channel_init:
            ChannelFactoryInitialize(0, network_interface)

        # 创建发布者
        self.publisher = ChannelPublisher(TOPIC_ARM_SDK, LowCmd_)
        self.publisher.Init()

        # 创建订阅者
        self.subscriber = ChannelSubscriber(TOPIC_LOWSTATE, LowState_)
        self.subscriber.Init(self._state_callback)

        # 【关键】状态变量初始化
        self.current_state = None
        self.weight = 0.0
        self.crc = CRC()

        # 【新增】动作管理器
        self.action_manager = ActionManager(action_dir)

        # 【关键】可调参数
        self.kp_upper = 60.0    # 上半身刚度
        self.kd_upper = 1.5     # 上半身阻尼
        self.kp_lower = 80.0    # 下半身刚度 (站立保持)
        self.kd_lower = 2.0     # 下半身阻尼
        self.max_joint_velocity = 0.5  # 最大关节速度
        
        # 【关键】关节分组
        self.arm_joints = [
            JointIndex.LeftShoulderPitch, JointIndex.LeftShoulderRoll,
            JointIndex.LeftShoulderYaw, JointIndex.LeftElbowPitch,
            JointIndex.LeftElbowRoll,
            JointIndex.RightShoulderPitch, JointIndex.RightShoulderRoll,
            JointIndex.RightShoulderYaw, JointIndex.RightElbowPitch,
            JointIndex.RightElbowRoll,
            JointIndex.WaistYaw, JointIndex.WaistRoll, JointIndex.WaistPitch
        ]
        
        self.leg_joints = [
            JointIndex.LeftHipPitch, JointIndex.LeftHipRoll,
            JointIndex.LeftHipYaw, JointIndex.LeftKnee,
            JointIndex.LeftAnkle, JointIndex.LeftAnkleRoll,
            JointIndex.RightHipPitch, JointIndex.RightHipRoll,
            JointIndex.RightHipYaw, JointIndex.RightKnee,
            JointIndex.RightAnkle, JointIndex.RightAnkleRoll
        ]
        
        print("🚀 初始化完成，等待状态同步...")
        time.sleep(0.5)

    
    def _state_callback(self, msg: LowState_):
        """状态回调"""
        self.current_state = msg
    
    def _send_cmd(self, msg: LowCmd_):
        """发送指令并计算CRC"""
        msg.crc = self.crc.Crc(msg)
        self.publisher.Write(msg)  # 大写 Write
    
    def _create_empty_cmd(self):
        # 【修正】使用默认初始化函数，自动填充所有字段
        return unitree_hg_msg_dds__LowCmd_()
    
    def get_current_positions(self):
        """获取所有关节当前位置"""
        positions = {}
        if self.current_state is None:
            return positions
            
        for i in range(len(self.current_state.motor_state)):
            positions[i] = self.current_state.motor_state[i].q
        return positions
    
    def smooth_interpolate(self, current, target, max_delta):
        """平滑插值"""
        delta = target - current
        if abs(delta) > max_delta:
            delta = max_delta if delta > 0 else -max_delta
        return current + delta
    
    def set_weight(self, weight, duration=2.0):
        """设置控制权重"""
        steps = int(duration / CTRL_DT)
        delta = (weight - self.weight) / steps
        
        msg = self._create_empty_cmd()
        
        for i in range(steps):
            self.weight += delta
            msg.motor_cmd[JointIndex.NotUsedJoint].q = self.weight
            
            # 保持所有关节当前状态
            current_pos = self.get_current_positions()
            for joint_idx in range(29):
                if joint_idx in current_pos:
                    msg.motor_cmd[joint_idx].q = current_pos[joint_idx]
                msg.motor_cmd[joint_idx].dq = 0.0
                msg.motor_cmd[joint_idx].kp = self.kp_lower
                msg.motor_cmd[joint_idx].kd = self.kd_lower
                msg.motor_cmd[joint_idx].tau = 0.0
            
            self._send_cmd(msg)
            time.sleep(CTRL_DT)
        
        self.weight = weight
    
    def move_to_pose(self, target_poses, duration=3.0):
        """
        移动到目标姿态
        target_poses: dict {JointIndex: target_angle}
        """
        steps = int(duration / CTRL_DT)
        max_delta = self.max_joint_velocity * CTRL_DT
        
        # 记录起始位置
        start_poses = self.get_current_positions()
        
        # 当前插值位置
        current_poses = {k: v for k, v in start_poses.items()}
        
        msg = self._create_empty_cmd()
        
        for step in range(steps):
            # 更新目标关节
            for joint_idx, target_angle in target_poses.items():
                current_poses[joint_idx] = self.smooth_interpolate(
                    current_poses[joint_idx], target_angle, max_delta
                )
            
            # 填充所有关节指令
            for joint_idx in range(29):
                # 设置目标位置
                if joint_idx in current_poses:
                    msg.motor_cmd[joint_idx].q = current_poses[joint_idx]
                
                # 设置刚度和阻尼
                if joint_idx in self.leg_joints:
                    # 腿部：高刚度保持站立
                    msg.motor_cmd[joint_idx].kp = self.kp_lower
                    msg.motor_cmd[joint_idx].kd = self.kd_lower
                elif joint_idx in self.arm_joints:
                    # 手臂：正常刚度
                    msg.motor_cmd[joint_idx].kp = self.kp_upper
                    msg.motor_cmd[joint_idx].kd = self.kd_upper
                else:
                    # 其他关节
                    msg.motor_cmd[joint_idx].kp = self.kp_upper
                    msg.motor_cmd[joint_idx].kd = self.kd_upper
                
                msg.motor_cmd[joint_idx].dq = 0.0
                msg.motor_cmd[joint_idx].tau = 0.0
            
            # 权重
            msg.motor_cmd[JointIndex.NotUsedJoint].q = self.weight
            
            self._send_cmd(msg)
            time.sleep(CTRL_DT)
                # 【新增】打印最终误差

        print("\n--- 姿态到达检查 ---")
        final_positions = self.get_current_positions()
        for joint_idx, target_angle in target_poses.items():
            if joint_idx in final_positions:
                error = abs(final_positions[joint_idx] - target_angle)
                if error > 0.1:
                    print(f"  关节{joint_idx}: 目标={target_angle:.2f}, 实际={final_positions[joint_idx]:.2f}, 误差={error:.2f}")
        print("-------------------\n")

        
        return current_poses
    
    def run_action_sequence(self):
        """执行动作序列"""
        print("\n" + "=" * 50)
        print("开始动作序列")
        print("=" * 50)
        
        # 等待状态数据到达
        print("等待机器人状态数据...")
        timeout = 5.0
        start_time = time.time()
        while self.current_state is None:
            time.sleep(0.1)
            if time.time() - start_time > timeout:
                print("[ERROR] 未收到状态数据！请检查网络连接或 DDS 话题。")
                return

        # 读取当前位置
        current = self.get_current_positions()
        print("当前关节位置已读取")
        
        # 阶段 1: 获取控制权 (权重 0 -> 1)
        print("\n[1/5] 获取控制权...")
        self.set_weight(1.0, duration=2.0)
        
        # 阶段 2: 初始化姿态 (归零)
        print("\n[2/5] 初始化姿态...")
        init_poses = {idx: 0.0 for idx in self.arm_joints}
        init_poses.update({idx: current[idx] for idx in self.leg_joints})
        self.move_to_pose(init_poses, duration=2.0)
        
        # 阶段 3: 抬起手臂
        print("\n[3/5] 抬起手臂...")
        half_pi = math.pi / 2
        raise_poses = {
            JointIndex.LeftShoulderPitch: 0.0,
            JointIndex.LeftShoulderRoll: half_pi,
            JointIndex.LeftShoulderYaw: 0.0,
            JointIndex.LeftElbowPitch: half_pi,
            JointIndex.LeftElbowRoll: 0.0,
            JointIndex.RightShoulderPitch: 0.0,
            JointIndex.RightShoulderRoll: -half_pi,
            JointIndex.RightShoulderYaw: 0.0,
            JointIndex.RightElbowPitch: half_pi,
            JointIndex.RightElbowRoll: 0.0,
            JointIndex.WaistYaw: 0.0,
            JointIndex.WaistRoll: 0.0,
            JointIndex.WaistPitch: 0.0,
        }
        # 保持腿部位置
        raise_poses.update({idx: current[idx] for idx in self.leg_joints})
        self.move_to_pose(raise_poses, duration=3.0)
        
        # 阶段 4: 比耶动作
        print("\n[4/5] 比耶动作...")
        peace_poses = {
            JointIndex.LeftShoulderPitch: 0.0,
            JointIndex.LeftShoulderRoll: -0.50,
            JointIndex.LeftShoulderYaw: 0.0,
            JointIndex.LeftElbowPitch: half_pi,
            JointIndex.LeftElbowRoll: 0.0,
            # 右臂比耶
            JointIndex.RightShoulderPitch: -half_pi,
            JointIndex.RightShoulderRoll: -half_pi,
            JointIndex.RightShoulderYaw: 0.0,
            JointIndex.RightElbowPitch: -half_pi,    # 肘部微弯
            JointIndex.RightElbowRoll: 1.0,    # 手腕旋转
            JointIndex.WaistYaw: 0.0,
            JointIndex.WaistRoll: 0.0,
            JointIndex.WaistPitch: 0.0,
        }
        peace_poses.update({idx: current[idx] for idx in self.leg_joints})
        self.move_to_pose(peace_poses, duration=2.0)


        # 保持动作 2 秒
        print("保持动作...")
        time.sleep(2.0)
        
        # 阶段 5: 放下手臂
        print("\n[5/5] 放下手臂...")
        final_poses = {idx: 0.0 for idx in self.arm_joints}
        final_poses.update({idx: current[idx] for idx in self.leg_joints})
        self.move_to_pose(final_poses, duration=3.0)
        
        # 阶段 6: 释放控制权
        print("\n释放控制权...")
        self.set_weight(0.0, duration=2.0)
        
        print("\n动作序列完成！")

    # ==================== 动作管理功能 ====================

    def execute_action_by_id(self, action_id, hold_time=2.0):
        """
        按 ID 执行已保存的动作
        Args:
            action_id: 动作ID (如 "peace_sign", "wave_hand")
            hold_time: 到达目标后保持时间（秒）
        Returns:
            bool: 是否执行成功
        """
        print(f"\n[ActionManager] 加载动作: {action_id}")

        # 从文件加载动作
        action = self.action_manager.load_action(action_id)
        if action is None:
            print(f"[ERROR] 动作不存在: {action_id}")
            print("可用动作列表:")
            self.action_manager.print_action_list()
            return False

        print(f"[ActionManager] 执行动作: {action.name} (ID: {action.action_id})")
        print(f"  - 持续时间: {action.duration}s")
        print(f"  - 关节数量: {len(action.poses)}")
        print(f"  - 描述: {action.description}")

        # 等待状态数据
        if self.current_state is None:
            print("等待机器人状态数据...")
            timeout = 5.0
            start_time = time.time()
            while self.current_state is None:
                time.sleep(0.1)
                if time.time() - start_time > timeout:
                    print("[ERROR] 未收到状态数据！")
                    return False

        # 获取当前位置
        current = self.get_current_positions()

        # 获取控制权
        print("[1/3] 获取控制权...")
        self.set_weight(1.0, duration=2.0)

        # 合并腿部位置（保持站立）
        target_poses = dict(action.poses)
        target_poses.update({idx: current[idx] for idx in self.leg_joints if idx in current})

        # 执行动作
        print(f"[2/3] 执行动作 [{action.name}]...")
        self.move_to_pose(target_poses, duration=action.duration)

        # 保持
        if hold_time > 0:
            print(f"[3/3] 保持姿态 {hold_time}s...")
            time.sleep(hold_time)

        print(f"\n[ActionManager] 动作执行完成: {action.action_id}")
        return True

    def save_current_pose(self, action_id, name="", duration=3.0, description=""):
        """
        将当前机器人姿态保存为动作
        Args:
            action_id: 动作ID
            name: 动作名称
            duration: 默认持续时间
            description: 描述
        Returns:
            bool: 是否保存成功
        """
        if self.current_state is None:
            print("[ERROR] 无状态数据，无法保存姿态")
            return False

        # 获取上半身关节位置
        current = self.get_current_positions()
        poses = {}
        for joint_idx in self.arm_joints:
            if joint_idx in current:
                poses[joint_idx] = round(current[joint_idx], 4)

        if not poses:
            print("[ERROR] 无法获取关节位置")
            return False

        # 创建并保存动作
        action = Action(
            action_id=action_id,
            name=name or action_id,
            poses=poses,
            duration=duration,
            description=description or f"录制于 {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        success = self.action_manager.save_action(action)
        if success:
            print(f"[ActionManager] 姿态已保存为动作:")
            print(f"  ID: {action.action_id}")
            print(f"  名称: {action.name}")
            print(f"  关节: {poses}")

        return success

    def list_actions(self):
        """列出所有已保存的动作"""
        self.action_manager.print_action_list()

    def delete_action(self, action_id):
        """删除指定动作"""
        return self.action_manager.delete_action(action_id)

    def run_action_sequence_from_ids(self, action_ids, hold_time=2.0, release_control=True):
        """
        按顺序执行多个动作（通过ID列表）
        Args:
            action_ids: 动作ID列表，如 ["init_pose", "raise_arms", "peace_sign"]
            hold_time: 每个动作的保持时间
            release_control: 执行完后是否释放控制权
        """
        print("\n" + "=" * 50)
        print(f"开始执行动作序列 ({len(action_ids)} 个动作)")
        print("=" * 50)

        # 等待状态数据
        if self.current_state is None:
            print("等待机器人状态数据...")
            timeout = 5.0
            start_time = time.time()
            while self.current_state is None:
                time.sleep(0.1)
                if time.time() - start_time > timeout:
                    print("[ERROR] 未收到状态数据！")
                    return

        # 获取控制权（只获取一次）
        print("\n[准备] 获取控制权...")
        self.set_weight(1.0, duration=2.0)

        # 依次执行每个动作
        for i, action_id in enumerate(action_ids):
            print(f"\n[{i+1}/{len(action_ids)}] 执行动作: {action_id}")

            action = self.action_manager.load_action(action_id)
            if action is None:
                print(f"[WARNING] 跳过不存在的动作: {action_id}")
                continue

            current = self.get_current_positions()
            target_poses = dict(action.poses)
            target_poses.update({idx: current[idx] for idx in self.leg_joints if idx in current})

            self.move_to_pose(target_poses, duration=action.duration)

            if hold_time > 0 and i < len(action_ids) - 1:
                time.sleep(hold_time)

        # 最后一个动作保持更久
        if hold_time > 0:
            print(f"\n保持最终姿态 {hold_time}s...")
            time.sleep(hold_time)

        # 释放控制权
        if release_control:
            print("\n释放控制权...")
            self.set_weight(0.0, duration=2.0)

        print("\n动作序列执行完成！")


# ==================== 主函数 ====================
def main():
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <network_interface> [options]")
        print("")
        print("Options:")
        print("  (无参数)                执行默认动作序列")
        print("  --action <id>           按ID执行单个动作")
        print("  --sequence <id1,id2,...> 按ID列表顺序执行多个动作")
        print("  --list                  列出所有已保存的动作")
        print("  --save-builtin          保存预置动作到文件")
        print("  --delete <id>           删除指定动作")
        print("")
        print("Examples:")
        print(f"  python3 {sys.argv[0]} eth0")
        print(f"  python3 {sys.argv[0]} eth0 --action peace_sign")
        print(f"  python3 {sys.argv[0]} eth0 --sequence init_pose,raise_arms,peace_sign")
        print(f"  python3 {sys.argv[0]} eth0 --list")
        sys.exit(-1)

    network_interface = sys.argv[1]
    action_dir = "./actions"

    # 解析命令行参数
    mode = "default"  # default, action, sequence, list, save_builtin, delete
    action_id = None
    action_ids = None

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--action":
            mode = "single"
            i += 1
            if i < len(sys.argv):
                action_id = sys.argv[i]
        elif arg == "--sequence":
            mode = "sequence"
            i += 1
            if i < len(sys.argv):
                action_ids = sys.argv[i].split(",")
        elif arg == "--list":
            mode = "list"
        elif arg == "--save-builtin":
            mode = "save_builtin"
        elif arg == "--delete":
            mode = "delete"
            i += 1
            if i < len(sys.argv):
                action_id = sys.argv[i]
        else:
            print(f"[WARNING] 未知参数: {arg}")
        i += 1

    # 初始化控制器
    controller = G1ActionController(network_interface, action_dir=action_dir)

    # 根据模式执行
    if mode == "list":
        # 仅列出动作，不需要连接机器人
        print("\n=== 已保存的动作列表 ===")
        controller.list_actions()

    elif mode == "save_builtin":
        # 保存预置动作
        print("\n=== 保存预置动作 ===")
        save_builtin_actions(controller.action_manager)

    elif mode == "delete":
        # 删除动作
        if action_id:
            controller.delete_action(action_id)
        else:
            print("[ERROR] 请指定要删除的动作ID: --delete <action_id>")

    elif mode == "single":
        # 执行单个动作
        if not action_id:
            print("[ERROR] 请指定动作ID: --action <action_id>")
            sys.exit(-1)

        print(f"\n准备执行动作: {action_id}")
        print("按 Enter 开始...")
        input()
        controller.execute_action_by_id(action_id)
        # 释放控制权
        print("\n释放控制权...")
        controller.set_weight(0.0, duration=2.0)

    elif mode == "sequence":
        # 执行动作序列
        if not action_ids:
            print("[ERROR] 请指定动作ID列表: --sequence id1,id2,id3")
            sys.exit(-1)

        print(f"\n准备执行动作序列: {action_ids}")
        print("按 Enter 开始...")
        input()
        controller.run_action_sequence_from_ids(action_ids)

    else:
        # 默认：执行原始硬编码动作序列
        print("\n按 Enter 开始执行默认动作序列...")
        input()
        controller.run_action_sequence()

if __name__ == "__main__":
    main()
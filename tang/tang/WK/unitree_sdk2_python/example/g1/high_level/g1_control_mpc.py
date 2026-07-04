#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Path
import sys
import numpy as np
import osqp
import scipy.sparse as sp

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_

class MPCController:
    def __init__(self, network_interface):
        rospy.loginfo("========================================")
        rospy.loginfo("Initializing MPC Controller (Locked Stop Mode)...")
        rospy.loginfo("========================================")

        # 1. 初始化 SDK
        try:
            ChannelFactoryInitialize(0, network_interface)
        except Exception as e:
            print(f"[ERROR] 网络初始化失败: {e}")
            sys.exit(-1)

        # 2. 初始化客户端
        self.sport_client = LocoClient()
        self.sport_client.SetTimeout(10.0)
        try:
            self.sport_client.Init()
        except Exception as e:
            print(f"[ERROR] 机器人连接失败: {e}")
            sys.exit(-1)

        self.can_move = False
        self.control_freq = 50.0
        self.dt = 1.0 / self.control_freq
        
        # --- MPC 物理约束 ---
        self.max_vx = 1.5
        self.max_vy = 0.6
        self.max_wz = 1.5
        
        # 加速度设置较大，解决起步慢的问题
        self.max_acc_v = 5.0   
        self.max_acc_w = 5.0   

        # --- MPC 权重参数 ---
        self.Q_v = 10.0
        self.R_v = 2.0
        
        # --- 状态变量 ---
        self.target_vx = 0.0
        self.target_vy = 0.0
        self.target_wz = 0.0
        
        # 真实反馈速度 (来自 DDS)
        self.current_vx = 0.0
        self.current_vy = 0.0
        self.current_wz = 0.0
        
        self.last_cmd_vx = 0.0
        self.last_cmd_vy = 0.0
        self.last_cmd_wz = 0.0

        # --- 【移植自 V4】到位锁定机制参数 ---
        self.is_stopped = False
        self.stop_velocity_threshold = 0.03  # 判定停止的速度阈值
        
        # 订阅
        self.cmd_vel_sub = rospy.Subscriber("/cmd_vel", Twist, self.cmd_vel_callback)
        self.path_sub = rospy.Subscriber("/move_base/GlobalPlanner/plan", Path, self.path_callback)
        
        # DDS 订阅
        self.odom_dds_sub = ChannelSubscriber("rt/odommodestate", SportModeState_)
        self.odom_dds_sub.Init(self.dds_odom_callback)

        self.control_timer = rospy.Timer(rospy.Duration(self.dt), self.control_loop)
        
        rospy.loginfo("🚀 控制器已启动 (MPC + 锁定停止)")

    def dds_odom_callback(self, msg: SportModeState_):
        self.current_vx = msg.velocity[0]
        self.current_vy = msg.velocity[1]
        self.current_wz = msg.yaw_speed

    def path_callback(self, msg: Path):
        self.can_move = len(msg.poses) > 0

    def cmd_vel_callback(self, msg: Twist):
        # 【移植自 V4】如果处于锁定状态，忽略微小指令，防止抖动
        if self.is_stopped:
            if abs(msg.linear.x) < 0.05 and abs(msg.linear.y) < 0.05 and abs(msg.angular.z) < 0.1:
                return # 保持锁定，不更新目标
            else:
                # 收到明显的运动指令，解锁
                self.is_stopped = False
                rospy.loginfo("🔓 解锁：开始新运动")

        self.target_vx = msg.linear.x
        self.target_vy = msg.linear.y
        self.target_wz = msg.angular.z

    def solve_mpc_step(self, v_current, v_target, v_last_cmd, max_v, max_acc):
        v_current = np.clip(v_current, -max_v, max_v)
        
        P = sp.csc_matrix([[2 * (self.Q_v + self.R_v)]])
        q = np.array([-2 * (self.Q_v * v_target + self.R_v * v_last_cmd)])
        
        acc_limit = max_acc * self.dt
        lower_bound = np.array([max(-max_v, v_current - acc_limit)])
        upper_bound = np.array([min(max_v, v_current + acc_limit)])
        
        A_box = sp.csc_matrix([[1.0]])
        
        prob = osqp.OSQP()
        prob.setup(P, q, A_box, lower_bound, upper_bound, verbose=False, eps_abs=1e-3, eps_rel=1e-3)
        res = prob.solve()
        
        if res.info.status != 'solved':
            return 0.0
        return res.x[0]

    def control_loop(self, event):
        # 1. 路径安全检查
        if not self.can_move:
            self.target_vx = 0.0
            self.target_vy = 0.0
            self.target_wz = 0.0

        # 2.【移植自 V4】到位检测与锁定逻辑
        # 条件：目标速度接近0 且 当前速度很小
        if (abs(self.target_vx) < 0.01 and 
            abs(self.target_vy) < 0.01 and 
            abs(self.target_wz) < 0.01 and
            abs(self.current_vx) < self.stop_velocity_threshold and
            abs(self.current_vy) < self.stop_velocity_threshold and
            abs(self.current_wz) < self.stop_velocity_threshold):
            
            if not self.is_stopped:
                rospy.loginfo("🔒 锁定：到达目标点，停止运动")
            self.is_stopped = True

        # 3. 根据锁定状态执行控制
        if self.is_stopped:
            # 【关键】锁定状态下，强制发送 0，跳过 MPC 计算
            self.sport_client.Move(0.0, 0.0, 0.0)
            # 重置指令记录，防止下次启动时突变
            self.last_cmd_vx = 0.0
            self.last_cmd_vy = 0.0
            self.last_cmd_wz = 0.0
        else:
            # 正常 MPC 计算流程
            cmd_vx = self.solve_mpc_step(self.current_vx, self.target_vx, self.last_cmd_vx, self.max_vx, self.max_acc_v)
            cmd_vy = self.solve_mpc_step(self.current_vy, self.target_vy, self.last_cmd_vy, self.max_vy, self.max_acc_v)
            cmd_wz = self.solve_mpc_step(self.current_wz, self.target_wz, self.last_cmd_wz, self.max_wz, self.max_acc_w)

            # 发送指令
            if abs(cmd_vx) < 0.01 and abs(cmd_vy) < 0.01 and abs(cmd_wz) < 0.01:
                # 直接发送零速度，避免频繁调用StopMove
                self.sport_client.Move(0.0, 0.0, 0.0)
            else:
                self.sport_client.Move(cmd_vx, cmd_vy, cmd_wz)
            
            self.last_cmd_vx = cmd_vx
            self.last_cmd_vy = cmd_vy
            self.last_cmd_wz = cmd_wz

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 g1_control_mpc_final.py <network_interface>")
        sys.exit(-1)

    network_interface = sys.argv[1]
    rospy.init_node("unitree_mpc_controller", anonymous=False)
    
    try:
        controller = MPCController(network_interface)
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

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
        rospy.loginfo("Initializing Unitree MPC Controller (Debug Mode)...")
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
        
        # 约束参数
        self.max_vx = 1.5
        self.max_vy = 0.6
        self.max_wz = 1.5
        self.max_acc_v = 1.0
        self.max_acc_w = 1.2
        self.Q_v = 10.0
        self.R_v = 3.0
        
        # 状态变量
        self.target_vx = 0.0
        self.target_vy = 0.0
        self.target_wz = 0.0
        self.current_vx = 0.0
        self.current_vy = 0.0
        self.current_wz = 0.0
        self.last_cmd_vx = 0.0
        self.last_cmd_vy = 0.0
        self.last_cmd_wz = 0.0

        # 订阅
        self.cmd_vel_sub = rospy.Subscriber("/cmd_vel", Twist, self.cmd_vel_callback)
        self.path_sub = rospy.Subscriber("/move_base/GlobalPlanner/plan", Path, self.path_callback)
        
        # DDS 订阅
        self.odom_dds_sub = ChannelSubscriber("rt/odommodestate", SportModeState_)
        self.odom_dds_sub.Init(self.dds_odom_callback)

        self.control_timer = rospy.Timer(rospy.Duration(self.dt), self.control_loop)
        
        rospy.loginfo("🚀 控制器已启动。等待导航路径...")

    def dds_odom_callback(self, msg: SportModeState_):
        self.current_vx = msg.velocity[0]
        self.current_vy = msg.velocity[1]
        self.current_wz = msg.yaw_speed

    def path_callback(self, msg: Path):
        # 打印路径接收情况 (调试用)
        # rospy.loginfo(f"收到路径，点数: {len(msg.poses)}")
        self.can_move = len(msg.poses) > 0

    def cmd_vel_callback(self, msg: Twist):
        self.target_vx = msg.linear.x
        self.target_vy = msg.linear.y
        self.target_wz = msg.angular.z

    def solve_mpc_step(self, v_current, v_target, v_last_cmd, max_v, max_acc):
        # 【重要修复】钳位限制，防止 OSQP 崩溃
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
        # --- 调试打印区 ---
        # 每秒打印一次状态，确认数据流
        if int(rospy.get_time() * 10) % 5 == 0: 
            state_str = "LOCKED" if not self.can_move else "ACTIVE"
            print(f"[State: {state_str}] "
                  f"Target: ({self.target_vx:.2f}, {self.target_wz:.2f}) | "
                  f"Current: ({self.current_vx:.2f}, {self.current_wz:.2f})")
        # ------------------

        if not self.can_move:
            self.target_vx = 0.0
            self.target_vy = 0.0
            self.target_wz = 0.0

        cmd_vx = self.solve_mpc_step(self.current_vx, self.target_vx, self.last_cmd_vx, self.max_vx, self.max_acc_v)
        cmd_vy = self.solve_mpc_step(self.current_vy, self.target_vy, self.last_cmd_vy, self.max_vy, self.max_acc_v)
        cmd_wz = self.solve_mpc_step(self.current_wz, self.target_wz, self.last_cmd_wz, self.max_wz, self.max_acc_w)

        if abs(cmd_vx) < 0.01 and abs(cmd_vy) < 0.01 and abs(cmd_wz) < 0.01:
            self.sport_client.StopMove()
        else:
            self.sport_client.Move(cmd_vx, cmd_vy, cmd_wz)
        
        self.last_cmd_vx = cmd_vx
        self.last_cmd_vy = cmd_vy
        self.last_cmd_wz = cmd_wz

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 g1_control_mpc_debug.py <network_interface>")
        sys.exit(-1)

    network_interface = sys.argv[1]
    rospy.init_node("unitree_mpc_controller", anonymous=False)
    
    try:
        controller = MPCController(network_interface)
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

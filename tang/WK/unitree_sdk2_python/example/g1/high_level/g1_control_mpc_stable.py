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

class AdaptiveMPCController:
    def __init__(self, network_interface):
        rospy.loginfo("========================================")
        rospy.loginfo("Initializing MPC Controller (v9 - Final Optimized)...")
        rospy.loginfo("========================================")

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
            print(f"[ERROR] 机器人连接失败: {e}")
            sys.exit(-1)

        self.can_move = False
        self.control_freq = 50.0
        self.dt = 1.0 / self.control_freq
        
        # --- MPC 物理约束 ---
        self.max_vx = 1.5
        self.max_vy = 0.6
        self.max_wz = 1.5
        
        # Fast 模式参数 (调整: 提升转向响应)
        self.max_acc_w_fast = 3.5   # 3.0 -> 3.5
        self.R_v_ang_fast = 2.5     # 3.0 -> 2.5 (稍微降低平滑度，提升响应)

        # Slow 模式参数
        self.max_acc_w_slow = 4.0
        self.R_v_ang_slow = 2.0
        
        self.max_acc_v = 5.0   

        # --- MPC 权重参数 ---
        self.Q_v = 10.0
        self.R_v_lin = 2.0     
        
        # --- 自适应模式参数 ---
        self.adaptive_mode = "auto"
        self.deadzone_threshold = 0.05
        
        # --- 状态变量 ---
        self.target_vx = 0.0
        self.target_vy = 0.0
        self.target_wz = 0.0
        
        self.current_vx = 0.0
        self.current_vy = 0.0
        self.current_wz = 0.0
        
        self.last_cmd_vx = 0.0
        self.last_cmd_vy = 0.0
        self.last_cmd_wz = 0.0
        
        # 滞回逻辑状态
        self.last_mode = "slow"
        self.mode_switch_count = 0

        # --- 到位锁定机制 ---
        self.is_stopped = False
        self.stop_velocity_threshold = 0.03
        
        # 订阅
        self.cmd_vel_sub = rospy.Subscriber("/cmd_vel", Twist, self.cmd_vel_callback)
        self.path_sub = rospy.Subscriber("/move_base/GlobalPlanner/plan", Path, self.path_callback)
        
        # DDS 订阅
        self.odom_dds_sub = ChannelSubscriber("rt/odommodestate", SportModeState_)
        self.odom_dds_sub.Init(self.dds_odom_callback)

        self.control_timer = rospy.Timer(rospy.Duration(self.dt), self.control_loop)
        
        rospy.loginfo("🚀 MPC 控制器已启动 (全局防倒车 + 优化滞回)")

    def dds_odom_callback(self, msg: SportModeState_):
        self.current_vx = msg.velocity[0]
        self.current_vy = msg.velocity[1]
        self.current_wz = msg.yaw_speed

    def path_callback(self, msg: Path):
        self.can_move = len(msg.poses) > 0

    def get_adaptive_mode(self):
        if self.adaptive_mode != "auto":
            return self.adaptive_mode
        
        # 【修改】调整阈值，让 Fast 模式更"粘"
        # 只要是正常前进 (>0.4)，就进 Fast
        # 只有速度很低 (<0.15) 才退回 Slow
        enter_fast_threshold = 0.4
        exit_fast_threshold = 0.15  # 大幅降低，防止减速时过早切 Slow
        
        if self.last_mode == "fast":
            if self.target_vx < exit_fast_threshold:
                return "slow"
            else:
                return "fast"
        else:
            if self.target_vx > enter_fast_threshold:
                return "fast"
            else:
                return "slow"

    def cmd_vel_callback(self, msg: Twist):
        if self.is_stopped:
            if abs(msg.linear.x) < 0.05 and abs(msg.linear.y) < 0.05 and abs(msg.angular.z) < 0.1:
                return
            else:
                self.is_stopped = False
                rospy.loginfo("🔓 解锁：开始新运动")

        # 【核心修改】全局禁止倒车
        # 无论 Fast 还是 Slow，只要是参观导览，倒车通常是非预期行为
        if msg.linear.x < 0.0:
            self.target_vx = 0.0
            # 仅在初次检测到倒车时报警，避免刷屏
            if self.last_cmd_vx >= 0: 
                 rospy.logwarn("⛔ 拦截倒车指令，改为原地调整")
        else:
            self.target_vx = msg.linear.x
            
        self.target_vy = msg.linear.y
        
        mode = self.get_adaptive_mode()
        raw_wz = msg.angular.z
        
        if mode == "fast":
            if abs(raw_wz) < self.deadzone_threshold:
                self.target_wz = 0.0
            else:
                if self.current_vx > 0.2:
                    # 【修改】放宽角速度公式：0.8 -> 1.0
                    # 允许在高速时转得更快一点
                    max_allowed_wz = 1.0 / (self.current_vx + 1.0)
                    max_allowed_wz = max(0.2, min(0.6, max_allowed_wz)) # 下限稍微提高
                    
                    self.target_wz = np.clip(raw_wz, -max_allowed_wz, max_allowed_wz)
                else:
                    self.target_wz = raw_wz
        else:
            # Slow 模式：信任转向
            self.target_wz = raw_wz

    def solve_mpc_step(self, v_current, v_target, v_last_cmd, max_v, max_acc, R_weight):
        v_current = np.clip(v_current, -max_v, max_v)
        
        P = sp.csc_matrix([[2 * (self.Q_v + R_weight)]])
        q = np.array([-2 * (self.Q_v * v_target + R_weight * v_last_cmd)])
        
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
        if not self.can_move:
            self.target_vx = 0.0
            self.target_vy = 0.0
            self.target_wz = 0.0

        # 到位检测
        if (abs(self.target_vx) < 0.01 and 
            abs(self.target_vy) < 0.01 and 
            abs(self.target_wz) < 0.01 and
            abs(self.current_vx) < self.stop_velocity_threshold and
            abs(self.current_vy) < self.stop_velocity_threshold and
            abs(self.current_wz) < self.stop_velocity_threshold):
            
            if not self.is_stopped:
                rospy.loginfo("🔒 锁定：到达目标点")
            self.is_stopped = True

        if self.is_stopped:
            self.sport_client.Move(0.0, 0.0, 0.0)
            self.last_cmd_vx = 0.0
            self.last_cmd_vy = 0.0
            self.last_cmd_wz = 0.0
        else:
            mode = self.get_adaptive_mode()
            
            if mode != self.last_mode:
                self.mode_switch_count += 1
                mode_name = "高速巡航" if mode == "fast" else "低速精准"
                rospy.loginfo(f"🔄 模式切换: {mode_name} (第{self.mode_switch_count}次)")
                self.last_mode = mode
            
            if mode == "fast":
                R_ang = self.R_v_ang_fast
                acc_w = self.max_acc_w_fast
            else:
                R_ang = self.R_v_ang_slow
                acc_w = self.max_acc_w_slow
            
            cmd_vx = self.solve_mpc_step(self.current_vx, self.target_vx, self.last_cmd_vx, 
                                         self.max_vx, self.max_acc_v, self.R_v_lin)
            cmd_vy = self.solve_mpc_step(self.current_vy, self.target_vy, self.last_cmd_vy, 
                                         self.max_vy, self.max_acc_v, self.R_v_lin)
            
            cmd_wz = self.solve_mpc_step(self.current_wz, self.target_wz, self.last_cmd_wz, 
                                         self.max_wz, acc_w, R_ang)

            if int(rospy.get_time() * 5) % 1 == 0: 
                mode_tag = "F" if mode == "fast" else "S"
                print(f"[{mode_tag}] Target: ({self.target_vx:.2f}, {self.target_wz:.2f}) | "
                      f"Current: ({self.current_vx:.2f}, {self.current_wz:.2f}) -> "
                      f"Send: ({cmd_vx:.2f}, {cmd_wz:.2f})")

            if abs(cmd_vx) < 0.01 and abs(cmd_vy) < 0.01 and abs(cmd_wz) < 0.01:
                self.sport_client.StopMove()
            else:
                self.sport_client.Move(cmd_vx, cmd_vy, cmd_wz)
            
            self.last_cmd_vx = cmd_vx
            self.last_cmd_vy = cmd_vy
            self.last_cmd_wz = cmd_wz

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 g1_control_mpc_stable9.py <network_interface>")
        sys.exit(-1)

    network_interface = sys.argv[1]
    rospy.init_node("unitree_mpc_controller", anonymous=False)
    
    try:
        controller = AdaptiveMPCController(network_interface)
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

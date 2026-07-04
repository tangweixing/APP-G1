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
        rospy.loginfo("Initializing MPC Controller (Bidirectional)...")
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
        
        # 加速度参数
        self.max_acc_v = 5.0
        self.max_acc_w_fast = 3.0
        self.max_acc_w_slow = 2.5

        # 权重
        self.R_v_lin = 1.0        
        self.R_v_ang_fast = 5
        self.R_v_ang_slow = 4.0
        self.Q_v = 8.0
        
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
        
        rospy.loginfo("🚀 MPC 控制器已启动 (允许倒车，全向移动)")

    def dds_odom_callback(self, msg: SportModeState_):
        self.current_vx = msg.velocity[0]
        self.current_vy = msg.velocity[1]
        self.current_wz = msg.yaw_speed

    def path_callback(self, msg: Path):
        self.can_move = len(msg.poses) > 0

    def get_adaptive_mode(self):
        # 阈值设置
        enter_fast_threshold = 0.4
        exit_fast_threshold = 0.3
        abs_target = abs(self.target_vx)
        
        if self.last_mode == "fast":
            if abs_target < exit_fast_threshold:
                return "slow"
            else:
                return "fast"
        else:
            if abs_target > enter_fast_threshold:
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

        # 允许倒车，不再拦截负速度
        self.target_vx = msg.linear.x
        self.target_vy = msg.linear.y
        
        mode = self.get_adaptive_mode()
        raw_wz = msg.angular.z
        
        # 角速度限幅逻辑保持不变
        if mode == "fast":
            if abs(raw_wz) > 0.05:
                # 高速转向限制
                max_allowed_wz = 1.0 / (abs(self.current_vx) + 1.8)
                max_allowed_wz = max(0.2, min(0.7, max_allowed_wz))
                self.target_wz = np.clip(raw_wz, -max_allowed_wz, max_allowed_wz)
            else:
                self.target_wz = 0.0
        else:
            self.target_wz = raw_wz

    def solve_mpc_step(self, v_current, v_target, v_last_cmd, max_v, max_acc, mode, is_angular=False):
        # 1. 输入截断
        v_current = np.clip(v_current, -max_v * 1.2, max_v * 1.2)
        v_target = np.clip(v_target, -max_v, max_v)
        
        # 2. 【修复】根据类型选择权重
        if is_angular:
            R_v = self.R_v_ang_fast if mode == "fast" else self.R_v_ang_slow
        else:
            R_v = self.R_v_lin

        # 【修复】使用计算好的 R_v，而不是 self.R_v_lin
        P = sp.csc_matrix([[2 * (self.Q_v + R_v)]])
        q = np.array([-2 * (self.Q_v * v_target + R_v * v_last_cmd)])
        
        acc_limit = max_acc * self.dt
        
        # 3. 【核心改进】角速度的特殊处理
        if is_angular:
            # 角速度减速阈值更大（惯性更大）
            decel_threshold = 0.20  # 0.05 -> 0.15
            
            same_direction = (v_current * v_target >= 0)
            need_decel = abs(v_current) > abs(v_target) + decel_threshold
            
            # 【新增】提前停止机制
            # 当目标接近0且当前速度较大时，提前开始减速
            approaching_zero = abs(v_target) < 0.1 and abs(v_current) > 0.1
            
            if approaching_zero:
                # 提前停止：使用更小的v_base，强制减速
                # 让MPC的约束下限更接近0，实现"提前刹车"
                v_base = v_current * 0.7  # 强制拉低基准
            elif same_direction and need_decel:
                # 正常减速：信任实际速度
                v_base = v_current
            else:
                # 加速：使用加权策略
                v_base = 0.6 * v_current + 0.4 * v_last_cmd
        else:
            # 线速度逻辑
            same_direction = (v_current * v_target >= 0)
            need_decel = abs(v_current) > abs(v_target) + 0.05
            
            if mode == "fast":
                if same_direction and need_decel:
                    # 同向减速：信任实际速度
                    v_base = v_current
                else:
                    # 加速或反向：使用加权策略
                    v_base = 0.6 * v_current + 0.4 * v_last_cmd
            else:
                # Slow模式：精准控制
                if same_direction and need_decel:
                    v_base = v_current
                else:
                    # 起步或反向时，混合基准
                    v_base = 0.7 * v_current + 0.3 * v_last_cmd
        
        # 4. 计算边界
        lower_val = v_base - acc_limit
        upper_val = v_base + acc_limit
        
        # 5. 物理极限截断
        lower_val = max(-max_v, lower_val)
        upper_val = min(max_v, upper_val)
        
        # 6. 边界合法性检查
        if lower_val > upper_val:
            lower_val = -max_v
            upper_val = max_v
            
        lower_bound = np.array([lower_val])
        upper_bound = np.array([upper_val])
        
        # 7. 求解
        A_box = sp.csc_matrix([[1.0]])
        
        prob = osqp.OSQP()
        prob.setup(P, q, A_box, lower_bound, upper_bound, verbose=False, eps_abs=1e-3, eps_rel=1e-3)
        res = prob.solve()
        
        if res.info.status != 'solved':
            return v_last_cmd
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
                strategy = "加权(快速)" if mode == "fast" else "混合(精准)"
                rospy.loginfo(f"🔄 模式切换: {mode} ({strategy})")
                self.last_mode = mode
            
            if mode == "fast":
                acc_w = self.max_acc_w_fast
            else:
                acc_w = self.max_acc_w_slow
            
            # 线速度求解 - is_angular=False (默认)
            cmd_vx = self.solve_mpc_step(self.current_vx, self.target_vx, self.last_cmd_vx, 
                                         self.max_vx, self.max_acc_v, mode)
            cmd_vy = self.solve_mpc_step(self.current_vy, self.target_vy, self.last_cmd_vy, 
                                         self.max_vy, self.max_acc_v, mode)
            
            # 【关键】角速度求解 - is_angular=True
            cmd_wz = self.solve_mpc_step(self.current_wz, self.target_wz, self.last_cmd_wz, 
                                         self.max_wz, acc_w, mode, is_angular=True)

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
        print("Usage: python3 g1_control_mpc_final.py <network_interface>")
        sys.exit(-1)

    network_interface = sys.argv[1]
    rospy.init_node("unitree_mpc_controller", anonymous=False)
    
    try:
        controller = AdaptiveMPCController(network_interface)
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

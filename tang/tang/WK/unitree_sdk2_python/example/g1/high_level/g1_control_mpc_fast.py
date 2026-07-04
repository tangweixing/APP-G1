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
        rospy.loginfo("Initializing MPC Controller (Asymmetric Logic)...")
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
        self.max_acc_w_fast = 4.0
        self.max_acc_w_slow = 3.0

        # 权重
        self.R_v_lin = 1.0        
        self.R_v_ang_fast = 2.5
        self.R_v_ang_slow = 2.0
        self.Q_v = 10.0
        
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
        
        rospy.loginfo("🚀 MPC 控制器已启动 (不对称闭环策略)")

    def dds_odom_callback(self, msg: SportModeState_):
        self.current_vx = msg.velocity[0]
        self.current_vy = msg.velocity[1]
        self.current_wz = msg.yaw_speed

    def path_callback(self, msg: Path):
        self.can_move = len(msg.poses) > 0

    def get_adaptive_mode(self):
        if self.adaptive_mode != "auto":
            return self.adaptive_mode
        
        # 【修改】提高退出阈值，0.26 属于低速，应该切回 Slow
        enter_fast_threshold = 0.4
        exit_fast_threshold = 0.3  # 0.15 -> 0.3
        
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

        # 全局禁止倒车
        if msg.linear.x < 0.0:
            self.target_vx = 0.0
            if self.last_cmd_vx >= 0:
                 rospy.logwarn_throttle(1.0, "⛔ 拦截倒车指令")
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
                    max_allowed_wz = 1.0 / (self.current_vx + 1.0)
                    max_allowed_wz = max(0.2, min(0.8, max_allowed_wz))
                    self.target_wz = np.clip(raw_wz, -max_allowed_wz, max_allowed_wz)
                else:
                    self.target_wz = raw_wz
        else:
            self.target_wz = raw_wz

    def solve_mpc_step(self, v_current, v_target, v_last_cmd, max_v, max_acc):
        # 1. 输入截断
        v_current = np.clip(v_current, -max_v * 1.2, max_v * 1.2)
        v_target = np.clip(v_target, -max_v, max_v)
        
        # 2. 构建目标函数
        P = sp.csc_matrix([[2 * (self.Q_v + self.R_v_lin)]])
        q = np.array([-2 * (self.Q_v * v_target + self.R_v_lin * v_last_cmd)])
        
        acc_limit = max_acc * self.dt
        
        # 【核心修改】不对称基准策略
        # 情况A: 需要减速 (v_current > v_target)
        # 此时不能使用加权基准，否则 last_cmd 的惯性会让下限过高，导致刹不住车
        # 必须强制使用 v_current，确保刹车约束范围合理
        if v_current > v_target + 0.05: # 加一点死区防止抖动
            v_base = v_current
        # 情况B: 需要加速或保持
        # 使用加权基准，克服延迟，提升响应速度
        else:
            v_base = 0.6 * v_current + 0.4 * v_last_cmd
        
        # 4. 计算边界数值
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
                mode_name = "高速巡航" if mode == "fast" else "低速精准"
                rospy.loginfo(f"🔄 模式切换: {mode_name} (第{self.mode_switch_count}次)")
                self.last_mode = mode
            
            if mode == "fast":
                acc_w = self.max_acc_w_fast
            else:
                acc_w = self.max_acc_w_slow
            
            # 调用不对称 MPC
            cmd_vx = self.solve_mpc_step(self.current_vx, self.target_vx, self.last_cmd_vx, 
                                         self.max_vx, self.max_acc_v)
            cmd_vy = self.solve_mpc_step(self.current_vy, self.target_vy, self.last_cmd_vy, 
                                         self.max_vy, self.max_acc_v)
            
            cmd_wz = self.solve_mpc_step(self.current_wz, self.target_wz, self.last_cmd_wz, 
                                         self.max_wz, acc_w)

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
        print("Usage: python3 g1_control_mpc_asymmetric.py <network_interface>")
        sys.exit(-1)

    network_interface = sys.argv[1]
    rospy.init_node("unitree_mpc_controller", anonymous=False)
    
    try:
        controller = AdaptiveMPCController(network_interface)
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

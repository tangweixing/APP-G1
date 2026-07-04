#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Path
import sys

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient

class CmdVelController:
    def __init__(self, network_interface):
        rospy.loginfo("Initializing Unitree LocoClient...")
        ChannelFactoryInitialize(0, network_interface)

        self.sport_client = LocoClient()
        self.sport_client.SetTimeout(10.0)
        self.sport_client.Init()

        self.can_move = False
        
        # --- 控制参数（关键修改）---
        self.control_freq = 50.0      
        
        # 【核心修改1】超软刹车系数，防止急刹触发平衡
        self.smoothing_factor_v = 0.2  # 从1改成0.05，刹车时间延长到约2秒
        self.smoothing_factor_w = 0.4   # 角速度保持较快
        
        # 【核心修改2】到位锁定机制
        self.is_stopped = False
        self.stop_counter = 0
        self.stop_threshold_cycles = 100 # 50Hz * 5秒 = 锁定5秒
        self.stop_velocity_threshold = 0.02  # 停止阈值
        
        # --- 状态变量 ---
        self.target_vx = 0.0
        self.target_vy = 0.0
        self.target_wz = 0.0
        
        self.current_vx = 0.0 
        self.current_vy = 0.0
        self.current_wz = 0.0

        # 订阅话题
        self.cmd_vel_sub = rospy.Subscriber("/cmd_vel", Twist, self.cmd_vel_callback)
        self.path_sub = rospy.Subscriber("/move_base/GlobalPlanner/plan", Path, self.path_callback)
        
        # 定时器循环
        self.control_timer = rospy.Timer(rospy.Duration(1.0/self.control_freq), self.control_loop)

    def path_callback(self, msg: Path):
        if len(msg.poses) > 0:
            self.can_move = True
        else:
            self.can_move = False

    def cmd_vel_callback(self, msg: Twist):
        """速度回调：支持锁定机制"""
        # 如果处于锁定状态，忽略微小指令
        if self.is_stopped:
            if abs(msg.linear.x) < 0.05 and abs(msg.linear.y) < 0.05 and abs(msg.angular.z) < 0.1:
                return
            else:
                # 收到大指令，解锁
                self.is_stopped = False
                self.stop_counter = 0
                rospy.loginfo("🔓 解锁：开始新运动")

        self.target_vx = msg.linear.x
        self.target_vy = msg.linear.y
        self.target_wz = msg.angular.z

    def control_loop(self, event):
        """控制循环（50Hz）"""
        # 如果没有路径，目标速度归零
        if not self.can_move:
            self.target_vx = 0.0
            self.target_vy = 0.0
            self.target_wz = 0.0

        # 【核心修改3】到位检测与锁定
        # 当目标速度为0，且当前速度很小时，进入锁定状态
        if (abs(self.target_vx) < 0.001 and 
            abs(self.target_vy) < 0.001 and 
            abs(self.target_wz) < 0.001 and
            abs(self.current_vx) < self.stop_velocity_threshold and
            abs(self.current_vy) < self.stop_velocity_threshold and
            abs(self.current_wz) < self.stop_velocity_threshold):
            
            if not self.is_stopped:
                rospy.loginfo("🔒 锁定：进入 2 秒静止稳定期")
            self.is_stopped = True
            self.stop_counter = self.stop_threshold_cycles

        # 如果处于锁定状态，只发送0，不执行滤波
        if self.is_stopped:
            if self.stop_counter > 0:
                self.sport_client.Move(0.0, 0.0, 0.0)
                self.stop_counter -= 1
            else:
                # 锁定时间结束，恢复正常控制
                self.is_stopped = False
        else:
            # 正常滤波
            self.current_vx = (1 - self.smoothing_factor_v) * self.current_vx + self.smoothing_factor_v * self.target_vx
            self.current_vy = (1 - self.smoothing_factor_v) * self.current_vy + self.smoothing_factor_v * self.target_vy
            self.current_wz = (1 - self.smoothing_factor_w) * self.current_wz + self.smoothing_factor_w * self.target_wz
            
            self.sport_client.Move(self.current_vx, self.current_vy, self.current_wz)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: rosrun your_package g1_control_v3.py networkInterface")
        sys.exit(-1)

    network_interface = sys.argv[1]

    rospy.init_node("unitree_cmd_vel_controller", anonymous=False)
    # 只修改这一行提示信息
    rospy.logwarn("⚠️ 已启用中等平滑(0.2) + 2秒到位锁定 + 分段速度控制")


    controller = CmdVelController(network_interface)
    rospy.spin()

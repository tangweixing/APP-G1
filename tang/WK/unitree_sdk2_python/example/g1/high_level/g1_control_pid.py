#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Path, Odometry
import sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient

class PIDController:
    def __init__(self, network_interface):
        rospy.loginfo("Initializing Unitree PID Controller...")
        ChannelFactoryInitialize(0, network_interface)

        self.sport_client = LocoClient()
        self.sport_client.SetTimeout(10.0)
        self.sport_client.Init()

        self.can_move = False
        
        # --- 控制参数 ---
        self.control_freq = 50.0
        self.dt = 1.0 / self.control_freq
        
        # PID 参数 (三个方向独立控制)
        # X方向 (前进)
        self.kp_vx = 2.0    # 比例系数：响应速度
        self.ki_vx = 0.1    # 积分系数：消除稳态误差
        self.kd_vx = 0.05   # 微分系数：抑制震荡
        
        # Y方向 (横移)
        self.kp_vy = 2.0
        self.ki_vy = 0.1
        self.kd_vy = 0.05
        
        # 角速度 (旋转)
        self.kp_wz = 2.5
        self.ki_wz = 0.15
        self.kd_wz = 0.08
        
        # 速度限幅 (安全约束)
        self.max_vx = 0.8
        self.max_vy = 0.4
        self.max_wz = 1.0
        
        # 积分限幅 (防止积分饱和)
        self.max_integral_v = 0.5
        self.max_integral_w = 0.8
        
        # --- 状态变量 ---
        self.target_vx = 0.0
        self.target_vy = 0.0
        self.target_wz = 0.0
        
        # 当前实际速度 (通过 Odom 反馈)
        self.current_vx = 0.0
        self.current_vy = 0.0
        self.current_wz = 0.0
        
        # 上一次的误差 (用于微分项)
        self.last_error_vx = 0.0
        self.last_error_vy = 0.0
        self.last_error_wz = 0.0
        
        # 积分累积
        self.integral_vx = 0.0
        self.integral_vy = 0.0
        self.integral_wz = 0.0
        
        # 上一次发送的指令 (用于平滑过渡)
        self.last_cmd_vx = 0.0
        self.last_cmd_vy = 0.0
        self.last_cmd_wz = 0.0

        # 订阅话题
        self.cmd_vel_sub = rospy.Subscriber("/cmd_vel", Twist, self.cmd_vel_callback)
        self.path_sub = rospy.Subscriber("/move_base/GlobalPlanner/plan", Path, self.path_callback)
        
        # 订阅里程计，获取真实速度反馈
        # 如果没有odom话题，可以注释掉这行，代码会自动退化为开环模式
        self.odom_sub = rospy.Subscriber("/odom", Odometry, self.odom_callback, queue_size=1)

        # 定时器循环
        self.control_timer = rospy.Timer(rospy.Duration(self.dt), self.control_loop)

    def odom_callback(self, msg: Odometry):
        """更新机器人当前真实速度"""
        self.current_vx = msg.twist.twist.linear.x
        self.current_vy = msg.twist.twist.linear.y
        self.current_wz = msg.twist.twist.angular.z

    def path_callback(self, msg: Path):
        if len(msg.poses) > 0:
            self.can_move = True
        else:
            self.can_move = False

    def cmd_vel_callback(self, msg: Twist):
        self.target_vx = msg.linear.x
        self.target_vy = msg.linear.y
        self.target_wz = msg.angular.z

    def pid_compute(self, target, current, last_error, integral, kp, ki, kd, max_integral):
        """
        单个PID计算单元
        :param target: 目标值
        :param current: 当前值
        :param last_error: 上一次误差
        :param integral: 积分累积值
        :param kp/ki/kd: PID参数
        :param max_integral: 积分限幅
        :return: (控制输出, 当前误差, 更新后的积分)
        """
        # 1. 计算误差
        error = target - current
        
        # 2. 比例项
        p_term = kp * error
        
        # 3. 积分项 (带抗饱和)
        integral = integral + error * self.dt
        # 限制积分范围，防止积分饱和导致超调
        if integral > max_integral:
            integral = max_integral
        elif integral < -max_integral:
            integral = -max_integral
        i_term = ki * integral
        
        # 4. 微分项
        derivative = (error - last_error) / self.dt
        d_term = kd * derivative
        
        # 5. 总输出
        output = p_term + i_term + d_term
        
        return output, error, integral

    def control_loop(self, event):
        """PID 控制循环"""
        
        # 安全检查：如果没有路径，目标速度归零
        if not self.can_move:
            self.target_vx = 0.0
            self.target_vy = 0.0
            self.target_wz = 0.0

        # --- X方向 PID 控制 ---
        cmd_vx, error_vx, self.integral_vx = self.pid_compute(
            self.target_vx, self.current_vx, self.last_error_vx,
            self.integral_vx, self.kp_vx, self.ki_vx, self.kd_vx,
            self.max_integral_v
        )
        self.last_error_vx = error_vx
        
        # --- Y方向 PID 控制 ---
        cmd_vy, error_vy, self.integral_vy = self.pid_compute(
            self.target_vy, self.current_vy, self.last_error_vy,
            self.integral_vy, self.kp_vy, self.ki_vy, self.kd_vy,
            self.max_integral_v
        )
        self.last_error_vy = error_vy
        
        # --- 角速度 PID 控制 ---
        cmd_wz, error_wz, self.integral_wz = self.pid_compute(
            self.target_wz, self.current_wz, self.last_error_wz,
            self.integral_wz, self.kp_wz, self.ki_wz, self.kd_wz,
            self.max_integral_w
        )
        self.last_error_wz = error_wz

        # --- 速度限幅 (安全约束) ---
        cmd_vx = max(min(cmd_vx, self.max_vx), -self.max_vx)
        cmd_vy = max(min(cmd_vy, self.max_vy), -self.max_vy)
        cmd_wz = max(min(cmd_wz, self.max_wz), -self.max_wz)

        # --- 发送指令 ---
        self.sport_client.Move(cmd_vx, cmd_vy, cmd_wz)
        
        # 记录本次指令
        self.last_cmd_vx = cmd_vx
        self.last_cmd_vy = cmd_vy
        self.last_cmd_wz = cmd_wz

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: rosrun your_package g1_control_pid.py networkInterface")
        sys.exit(-1)

    network_interface = sys.argv[1]

    rospy.init_node("unitree_pid_controller", anonymous=False)
    rospy.logwarn("🎮 PID 控制器已启动")
    rospy.loginfo("参数: Kp=2.0, Ki=0.1, Kd=0.05 (线速度)")
    
    controller = PIDController(network_interface)
    rospy.spin()

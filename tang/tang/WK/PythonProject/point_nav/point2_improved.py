#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import actionlib
import math
import os
import threading
import sys
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from tf.transformations import quaternion_from_euler
from actionlib_msgs.msg import GoalStatus

class NavPointPlayer:
    def __init__(self, target_x, target_y, target_theta, audio_file, threshold=0.5):
        self.target_x = target_x
        self.target_y = target_y
        self.target_theta = target_theta
        self.audio_file = audio_file
        self.threshold = threshold
        self.reached = False
        self.goal_sent = False

        # 使用 actionlib 发送导航目标
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        rospy.loginfo("等待move_base服务器启动...")
        
        # 增加超时检查
        if not self.client.wait_for_server(rospy.Duration(10.0)):
            rospy.logerr("move_base服务器启动超时！")
            rospy.signal_shutdown("move_base服务器未启动")
            return
        
        rospy.loginfo("move_base服务器已连接")
        rospy.sleep(1.0)  # 等待连接稳定
        
        # 获取当前位置
        self.get_current_position()
        
        # 计算距离
        self.calculate_distance()
        
        # 发布目标
        self.publish_goal()
        
        # 启动状态监控
        self.start_status_monitor()

    def get_current_position(self):
        """获取机器人当前位置"""
        try:
            # 尝试获取当前位置
            from nav_msgs.msg import Odometry
            self.current_pose = None
            self.odom_sub = rospy.Subscriber('/amcl_pose', Odometry, self.odom_callback)
            rospy.sleep(2.0)  # 等待获取位置
            
            if self.current_pose:
                rospy.loginfo(f"[当前位置] x={self.current_pose.pose.pose.position.x:.3f}, "
                           f"y={self.current_pose.pose.pose.position.y:.3f}")
            else:
                rospy.logwarn("无法获取当前位置，使用默认值 (0, 0)")
        except Exception as e:
            rospy.logerr(f"获取位置失败: {e}")

    def odom_callback(self, msg):
        """位置回调"""
        if self.current_pose is None:
            self.current_pose = msg

    def calculate_distance(self):
        """计算到目标点的距离"""
        if self.current_pose:
            current_x = self.current_pose.pose.pose.position.x
            current_y = self.current_pose.pose.pose.position.y
            
            distance = math.sqrt((self.target_x - current_x)**2 + 
                             (self.target_y - current_y)**2)
            
            rospy.loginfo(f"[距离计算] 当前位置({current_x:.3f}, {current_y:.3f}) -> "
                        f"目标位置({self.target_x:.3f}, {self.target_y:.3f}) = {distance:.3f}m")
            
            if distance < self.threshold:
                rospy.logwarn(f"[警告] 距离目标点太近 ({distance:.3f}m < {self.threshold}m)，"
                            "可能不会移动！")
        else:
            rospy.logwarn("无法计算距离，当前位置未知")

    def publish_goal(self):
        """发布导航目标"""
        if self.goal_sent:
            rospy.logwarn("目标已发送，跳过重复发送")
            return
            
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = self.target_x
        goal.target_pose.pose.position.y = self.target_y
        q = quaternion_from_euler(0, 0, self.target_theta)
        goal.target_pose.pose.orientation.x = q[0]
        goal.target_pose.pose.orientation.y = q[1]
        goal.target_pose.pose.orientation.z = q[2]
        goal.target_pose.pose.orientation.w = q[3]

        rospy.loginfo(f"[导航目标] x={self.target_x}, y={self.target_y}, θ={self.target_theta}")
        rospy.loginfo("[发送目标] 开始导航...")
        
        # 发送目标，设置反馈回调
        self.client.send_goal(goal, 
                         done_cb=self.goal_done_callback,
                         active_cb=self.goal_active_callback,
                         feedback_cb=self.goal_feedback_callback)
        
        self.goal_sent = True

    def goal_active_callback(self):
        """目标激活回调"""
        rospy.loginfo("[导航状态] 目标已激活，开始导航...")

    def goal_feedback_callback(self, feedback):
        """反馈回调"""
        # 可以在这里记录导航进度
        pass

    def goal_done_callback(self, status, result):
        """目标完成回调"""
        rospy.loginfo(f"[导航完成] 状态码: {status}")
        
        # 详细的状态码解释
        status_map = {
            GoalStatus.PENDING: "待处理",
            GoalStatus.ACTIVE: "执行中",
            GoalStatus.PREEMPTED: "被抢占",
            GoalStatus.SUCCEEDED: "成功",
            GoalStatus.ABORTED: "中止",
            GoalStatus.REJECTED: "被拒绝",
            GoalStatus.PREEMPTING: "正在抢占",
            GoalStatus.RECALLING: "正在召回",
            GoalStatus.RECALLED: "已召回",
            GoalStatus.LOST: "丢失"
        }
        
        status_name = status_map.get(status, f"未知状态({status})")
        rospy.loginfo(f"[导航状态] {status_name}")
        
        if status == GoalStatus.SUCCEEDED:
            rospy.loginfo("[到达目标] 导航成功完成！")
            self.reached = True
            self.play_audio()
        else:
            rospy.logerr(f"[导航失败] 状态: {status_name}")
            # 不退出程序，让用户看到错误信息

    def start_status_monitor(self):
        """启动状态监控线程"""
        def monitor():
            while not rospy.is_shutdown() and not self.reached:
                rospy.sleep(1.0)
                
                # 检查客户端状态
                if self.client.get_state() == GoalStatus.ABORTED:
                    rospy.logwarn("[状态监控] 导航被中止")
                    break
                elif self.client.get_state() == GoalStatus.REJECTED:
                    rospy.logwarn("[状态监控] 导航被拒绝")
                    break
        
        monitor_thread = threading.Thread(target=monitor)
        monitor_thread.daemon = True
        monitor_thread.start()

    def play_audio(self):
        """播放音频"""
        def _play():
            abs_path = os.path.abspath(self.audio_file)
            try:
                rospy.loginfo(f"[音频] 准备播放: {abs_path}")
                # 这里可以添加实际的音频播放代码
                rospy.loginfo("[完成] 音频播放结束，退出程序。")
                rospy.signal_shutdown("任务完成")
            except Exception as e:
                rospy.logerr(f"[错误] 音频播放失败: {e}")

        t = threading.Thread(target=_play)
        t.start()

if __name__ == "__main__":
    rospy.init_node("nav_point_player")

    # ===== 修改这里即可 =====
    # 注意：这些坐标需要根据实际电梯位置修改
    target_x = 2.0  # 修改为实际电梯位置的x坐标
    target_y = 1.0  # 修改为实际电梯位置的y坐标
    target_theta = 0.0  # 修改为实际朝向
    audio_file = "/home/harry/unitree/WK/PythonProject/point_nav/audio/dianti.mp3"
    threshold = 0.5

    rospy.loginfo("=" * 50)
    rospy.loginfo("导航点播放器启动")
    rospy.loginfo(f"目标点: ({target_x}, {target_y}, {target_theta})")
    rospy.loginfo(f"音频文件: {audio_file}")
    rospy.loginfo("=" * 50)

    try:
        node = NavPointPlayer(target_x, target_y, target_theta, audio_file, threshold)
        rospy.spin()
    except Exception as e:
        rospy.logerr(f"[异常] 程序异常: {e}")
        import traceback
        traceback.print_exc()

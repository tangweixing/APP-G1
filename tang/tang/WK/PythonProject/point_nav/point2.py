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

class NavPointPlayer:
    def __init__(self, target_x, target_y, target_theta, audio_file, threshold=0.5):
        self.target_x = target_x
        self.target_y = target_y
        self.target_theta = target_theta
        self.audio_file = audio_file
        self.threshold = threshold
        self.reached = False

        # 使用 actionlib 发送导航目标
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        rospy.loginfo("等待move_base服务器启动...")
        self.client.wait_for_server()
        
        rospy.sleep(1.0)  # 等待连接
        self.publish_goal()

    def publish_goal(self):
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
        self.client.send_goal(goal, done_cb=self.goal_done_callback)

    def goal_done_callback(self, status, result):
        rospy.loginfo(f"[导航完成] 状态: {status}")
        if status == actionlib.GoalStatus.SUCCEEDED:
            rospy.loginfo("[到达目标] 播放音频...")
            self.reached = True
            self.play_audio()

    def play_audio(self):
        def _play():
            abs_path = os.path.abspath(self.audio_file)
            try:
                rospy.loginfo("[完成] 音频播放结束，退出程序。")
                rospy.signal_shutdown("任务完成")
            except Exception as e:
                rospy.logerr(f"[错误] 音频播放失败: {e}")

        t = threading.Thread(target=_play)
        t.start()

if __name__ == "__main__":
    rospy.init_node("nav_point_player")

    # ===== 修改这里即可 =====
    target_x = -18.9
    target_y = 2.41
    target_theta = 3.14231
    audio_file = "/home/unitree/tang/WK/PythonProject/point_nav/audio/dianti.mp3"
    threshold = 0.5

    node = NavPointPlayer(target_x, target_y, target_theta, audio_file, threshold)
    rospy.spin()
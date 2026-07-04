#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import math
import os
import threading
import tf.transformations as tft
from move_base_msgs.msg import MoveBaseActionGoal, MoveBaseActionFeedback
from std_msgs.msg import Header
from playsound import playsound


class NavPointPlayer:
    def __init__(self, target_x, target_y, target_theta, audio_file, threshold=0.5):
        self.target_x = target_x
        self.target_y = target_y
        self.target_theta = target_theta
        self.audio_file = audio_file
        self.threshold = threshold
        self.reached = False

        # 发布导航目标（MoveBaseActionGoal）
        self.goal_pub = rospy.Publisher("/move_base/goal", MoveBaseActionGoal, queue_size=1)
        # 订阅 /move_base/feedback 获取当前位姿
        self.feedback_sub = rospy.Subscriber("/move_base/feedback", MoveBaseActionFeedback, self.feedback_callback)

        rospy.sleep(1.0)  # 等待topic连接
        self.publish_goal()

    def publish_goal(self):
        goal = MoveBaseActionGoal()
        goal.goal.target_pose.header.frame_id = "map"
        goal.goal.target_pose.header.stamp = rospy.Time.now()
        goal.goal.target_pose.pose.position.x = self.target_x
        goal.goal.target_pose.pose.position.y = self.target_y
        q = tft.quaternion_from_euler(0, 0, self.target_theta)
        goal.goal.target_pose.pose.orientation.x = q[0]
        goal.goal.target_pose.pose.orientation.y = q[1]
        goal.goal.target_pose.pose.orientation.z = q[2]
        goal.goal.target_pose.pose.orientation.w = q[3]

        rospy.loginfo(f"[导航目标] x={self.target_x}, y={self.target_y}, θ={self.target_theta}")
        self.goal_pub.publish(goal)

    def feedback_callback(self, msg):
        if self.reached:
            return

        current_pose = msg.feedback.base_position.pose
        dx = current_pose.position.x - self.target_x
        dy = current_pose.position.y - self.target_y
        dist = math.hypot(dx, dy)  # 欧氏距离

        rospy.loginfo_throttle(2, f"[当前位置] ({current_pose.position.x:.2f}, {current_pose.position.y:.2f}) -> 距离目标 {dist:.2f} m")

        if dist <= self.threshold:
            rospy.loginfo("[到达目标] 播放音频...")
            self.reached = True
            self.play_audio()

    def play_audio(self):
        def _play():
            abs_path = os.path.abspath(self.audio_file)
            try:
                playsound(abs_path)  # 阻塞直到播放完成
                rospy.loginfo("[完成] 音频播放结束，退出程序。")
                rospy.signal_shutdown("任务完成")
            except Exception as e:
                rospy.logerr(f"[错误] 音频播放失败: {e}")

        t = threading.Thread(target=_play)
        t.start()

if __name__ == "__main__":
    rospy.init_node("nav_point_player")

    # ===== 修改这里即可 =====
    target_x = 2.0573
    target_y = -1.1618
    target_theta = -2.63
    audio_file = "audio/introduce_3.mp3"
    threshold = 0.5

    node = NavPointPlayer(target_x, target_y, target_theta, audio_file, threshold)
    rospy.spin()

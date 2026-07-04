#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path

class PathStreamer:
    def __init__(self):
        rospy.init_node('path_streamer', anonymous=True)

        # 发布完整路径
        self.pub = rospy.Publisher('teach_path', Path, queue_size=10)

        # 路径文件参数，支持 rosparam 设置
        path_file = rospy.get_param('~path_file', '/home/nvidia/Go2Nav2D/src/FASTLIO2_SAM_LC/path/teaching_paths.txt')
        self.path_data = self.load_path(path_file)

        # 构造 Path 消息
        self.path_msg = Path()
        self.path_msg.header.frame_id = "map"
        self.path_msg.poses = []

        for x, y, z, qx, qy, qz, qw in self.path_data:
            pose = PoseStamped()
            pose.header.frame_id = "map"
            pose.pose.position.x = x
            pose.pose.position.y = y
            pose.pose.position.z = z
            pose.pose.orientation.x = qx
            pose.pose.orientation.y = qy
            pose.pose.orientation.z = qz
            pose.pose.orientation.w = qw
            self.path_msg.poses.append(pose)

        # 定时发布完整路径
        self.timer_period = 0.5  # 秒
        self.timer = rospy.Timer(rospy.Duration(self.timer_period), self.timer_callback)

        # rospy.loginfo("PathStreamer started. Path loaded with %d poses.", len(self.path_msg.poses))

    def load_path(self, path_file):
        poses = []
        try:
            with open(path_file, 'r') as f:
                for line in f:
                    if 'EOP' in line or not line.strip():
                        continue
                    parts = list(map(float, line.strip().split()))
                    if len(parts) == 7:
                        poses.append(parts)
                    else:
                        rospy.logwarn("Invalid line skipped: %s", line.strip())
        except Exception as e:
            rospy.logerr("Failed to load path: %s", e)
        return poses

    def timer_callback(self, event):
        # 更新时间戳
        current_time = rospy.Time.now()
        self.path_msg.header.stamp = current_time
        for pose in self.path_msg.poses:
            pose.header.stamp = current_time

        self.pub.publish(self.path_msg)
        rospy.loginfo("Published full path with %d poses", len(self.path_msg.poses))

if __name__ == '__main__':
    try:
        PathStreamer()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

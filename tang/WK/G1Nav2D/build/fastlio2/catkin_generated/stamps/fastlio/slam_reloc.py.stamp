#!/usr/bin/env python3
import rospy
import tf
from geometry_msgs.msg import PoseWithCovarianceStamped
from fastlio.srv import SlamReLoc  # 替换为实际服务路径

class SlamRelocFromRViz:
    def __init__(self):
        self.pose_received = False
        self.pcd_path = rospy.get_param("~pcd_path", "/home/nvidia/Go2Nav2D/src/FAST_LIO_LOCALIZATION/PCD/three_floors.pcd")

        rospy.wait_for_service('/slam_reloc')
        self.reloc_service = rospy.ServiceProxy('/slam_reloc', SlamReLoc)

        rospy.Subscriber('/initialpose', PoseWithCovarianceStamped, self.pose_callback)
        rospy.loginfo("Waiting for /initialpose from RViz...")

    def pose_callback(self, msg):
        # if  self.pose_received:
        #     return  # 只处理一次
        self.pose_received = True

        position = msg.pose.pose.position
        orientation = msg.pose.pose.orientation
        (roll, pitch, yaw) = tf.transformations.euler_from_quaternion(
            [orientation.x, orientation.y, orientation.z, orientation.w]
        )

        rospy.loginfo("Received pose from RViz: x=%.2f, y=%.2f, yaw=%.2f", position.x, position.y, yaw)

        try:
            resp = self.reloc_service(
                self.pcd_path,
                position.x, position.y, position.z,
                roll, pitch, yaw
            )
            rospy.loginfo("SlamReLoc service called successfully.")
            rospy.loginfo("Response: %s", resp)
        except rospy.ServiceException as e:
            rospy.logerr("Service call failed: %s", e)

if __name__ == '__main__':
    rospy.init_node('slam_reloc_from_rviz')
    SlamRelocFromRViz()
    rospy.spin()

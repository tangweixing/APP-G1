#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Twist
from DogControllerSDK import DogControllerSDK
import threading

class CmdVelController:
    def __init__(self):
        self.dog = DogControllerSDK("http://192.168.58.21:5000", robot_ip="192.168.58.126")
        self.dog.__enter__()
        rospy.on_shutdown(self.cleanup)

        # 缓存的 cmd_vel 消息
        self.latest_cmd = Twist()

        # 互斥锁保护 cmd_vel 数据
        self.lock = threading.Lock()

        # 订阅 cmd_vel
        rospy.Subscriber("/cmd_vel_smooth", Twist, self.cmd_vel_callback)
        rospy.loginfo("CmdVelController initialized. Subscribed to /cmd_vel.")

        # 设置发送频率（Hz）
        self.rate_hz = 10
        self.running = True
        self.sender_thread = threading.Thread(target=self.send_loop)
        self.sender_thread.start()

    def cmd_vel_callback(self, msg: Twist):
        with self.lock:
            self.latest_cmd = msg

    def send_loop(self):
        rate = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown() and self.running:
            with self.lock:
                cmd = self.latest_cmd
            try:
                self.dog.move(cmd.linear.x, cmd.linear.y, cmd.angular.z)
                rospy.loginfo(f"Sending cmd_vel to dog: linear=({cmd.linear.x:.2f}, {cmd.linear.y:.2f}), angular=({cmd.angular.z:.2f})")

            except Exception as e:
                rospy.logerr(f"[DogControllerSDK] Failed to send move command: {e}")
            rate.sleep()

    def cleanup(self):
        rospy.loginfo("Shutting down CmdVelController...")
        self.running = False
        self.sender_thread.join()
        self.dog.__exit__(None, None, None)

if __name__ == "__main__":
    rospy.init_node("cmd_vel_dog_controller")
    controller = CmdVelController()
    rospy.spin()


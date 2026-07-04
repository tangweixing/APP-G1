#!/usr/bin/env python3
import rospy
import tf
from nav_msgs.msg import Odometry, Path  # ← 加入 Path 类型
from geometry_msgs.msg import PoseStamped
import threading

class PathRecorder:
    def __init__(self):
        self.console_command_hint()
        self.lock = threading.Lock()
        self.current_path = []
        self.all_paths = []

        self.is_recording = False
        self.file_path = rospy.get_param("~file_path", "/home/nvidia/Go2Nav2D/src/FASTLIO2_SAM_LC/path/teaching_paths.txt")
        self.dist_thresh = rospy.get_param("~distance_threshold", 0.1)  # ← 设定最小记录间隔（米）

        rospy.Subscriber("/slam_odom", Odometry, self.odom_callback)

        self.path_pub = rospy.Publisher("/teaching_path", Path, queue_size=1)  # ← 实时路径发布器
        self.fixed_frame = rospy.get_param("~frame_id", "map")  # 默认为 map，可以改为 odom 或 base_link
        self.tf_listener = tf.TransformListener()

        rospy.loginfo("PathRecorder initialized.")
        # rospy.Timer(rospy.Duration(0.5), self.console_command_hint)

    def odom_callback(self, msg):
        if not self.is_recording:
            return

        try:
            # 创建原始 PoseStamped（来自 msg）
            raw_pose = PoseStamped()
            raw_pose.header = msg.header
            raw_pose.pose = msg.pose.pose

            # 等待 TF 可用（最多 0.5 秒）
            self.tf_listener.waitForTransform(self.fixed_frame, raw_pose.header.frame_id, raw_pose.header.stamp, rospy.Duration(0.5))

            # 进行坐标变换
            transformed_pose = self.tf_listener.transformPose(self.fixed_frame, raw_pose)

        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException) as e:
            rospy.logwarn("TF transform failed: %s", str(e))
            return

        with self.lock:
            if not self.current_path:
                self.current_path.append(transformed_pose)
            else:
                last_pose = self.current_path[-1]
                dx = transformed_pose.pose.position.x - last_pose.pose.position.x
                dy = transformed_pose.pose.position.y - last_pose.pose.position.y
                dz = transformed_pose.pose.position.z - last_pose.pose.position.z
                distance = (dx**2 + dy**2 + dz**2)**0.5

                if distance >= self.dist_thresh:
                    self.current_path.append(transformed_pose)

            # 实时发布路径
            path_msg = Path()
            path_msg.header.frame_id = self.fixed_frame
            path_msg.header.stamp = rospy.Time.now()
            path_msg.poses = self.current_path.copy()
            self.path_pub.publish(path_msg)


    def start_recording(self):
        with self.lock:
            self.current_path = []
            self.is_recording = True
        rospy.loginfo("Recording started.")

    def stop_recording(self):
        with self.lock:
            self.is_recording = False
            if self.current_path:
                self.all_paths.append(self.current_path)
                rospy.loginfo("Recording stopped. Path with %d points saved.", len(self.current_path))
            else:
                rospy.logwarn("No data recorded.")
            self.current_path = []

    def save_to_file(self):
        with self.lock:
            try:
                with open(self.file_path, "w") as f:
                    for path in self.all_paths:
                        for p in path:
                            x = p.pose.position.x
                            y = p.pose.position.y
                            z = p.pose.position.z
                            rx = p.pose.orientation.x
                            ry = p.pose.orientation.y
                            rz = p.pose.orientation.z
                            rw = p.pose.orientation.w
                            f.write(f"{x} {y} {z} {rx} {ry} {rz} {rw}\n")
                        f.write("EOP\n")
                rospy.loginfo("Paths written to file: %s", self.file_path)
            except Exception as e:
                rospy.logerr("Failed to write file: %s", e)

    def console_command_hint(self):
        print("\n--- Path Recorder Console ---")
        print("[s] Start Recording")
        print("[e] End Recording")
        print("[w] Write to File")
        print("[q] Quit")
        print("-----------------------------")

    def run_console(self):
        while not rospy.is_shutdown():
            cmd = input("Enter command: ").strip().lower()
            if cmd == "s":
                self.start_recording()
            elif cmd == "e":
                self.stop_recording()
            elif cmd == "w":
                self.save_to_file()
            elif cmd == "q":
                rospy.signal_shutdown("User Exit")
            else:
                print("Unknown command.")

if __name__ == "__main__":
    rospy.init_node("record_teaching_path")
    recorder = PathRecorder()
    recorder.run_console()

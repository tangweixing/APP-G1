#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重定位调试脚本 - 结合方案1和方案3
功能：
1. 检测 IMU 初始化状态
2. 获取当前位姿作为初始猜测
3. 智能调用重定位服务
"""

import rospy
import rosservice
import fastlio
import sys
import time
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from fastlio.srv import SlamReLoc

try:
    from fastlio.srv import SlamRelocCheck
    HAS_RELOC_CHECK = True
except ImportError:
    HAS_RELOC_CHECK = False
    print("⚠️  警告: SlamRelocCheck 服务不可用，将跳过IMU状态检测")


class RelocDebugger:
    def __init__(self):
        self.imu_ready = False
        self.current_pose = None
        self.odom_received = False
        
    def check_imu_status(self):
        """检测 IMU 是否初始化完成"""
        print("\n" + "="*60)
        print("📋 步骤 1: 检测 IMU 初始化状态")
        print("="*60)
        
        # 如果 SlamRelocCheck 服务不可用，跳过检测
        if not HAS_RELOC_CHECK:
            print("⚠️  SlamRelocCheck 服务不可用，跳过IMU状态检测")
            print("   提示: IMU 初始化通常需要5-10秒，请确保机器人静止\n")
            self.imu_ready = False
            return True
        
        # 检查服务是否存在
        try:
            services = rosservice.get_service_list()
            if '/slam_reloc_check' not in services:
                print("❌ 错误: /slam_reloc_check 服务不存在")
                print("   请确保已启动: roslaunch fastlio navigation.launch")
                return False
                
            # 调用重定位检查服务
            rospy.wait_for_service('/slam_reloc_check', timeout=5.0)
            check_proxy = rospy.ServiceProxy('/slam_reloc_check', fastlio.srv.SlamRelocCheck)
            
            # 多次检测，等待IMU初始化
            max_wait = 15  # 最大等待15秒
            wait_interval = 1
            waited = 0
            
            print(f"\n⏳ 等待 IMU 初始化 (最多 {max_wait} 秒)...")
            print("   提示: 请确保机器人静止，IMU 正在采集数据\n")
            
            while waited < max_wait:
                try:
                    result = check_proxy()
                    if result.status:
                        print(f"✅ IMU 已初始化完成! (等待 {waited} 秒)")
                        self.imu_ready = True
                        return True
                    else:
                        if waited % 3 == 0:
                            print(f"   ⏳ IMU 初始化中... ({waited}/{max_wait}秒)")
                            print("      提示: 如果长时间未初始化，请检查:")
                            print("           - Livox 雷达是否正常工作")
                            print("           - IMU 数据话题 /livox/imu 是否有数据")
                except Exception as e:
                    print(f"   ⚠️  检测异常: {e}")
                
                time.sleep(wait_interval)
                waited += wait_interval
            
            print(f"\n❌ IMU 在 {max_wait} 秒内未完成初始化")
            print("   可能原因:")
            print("   1. 雷达/IMU 未启动或数据异常")
            print("   2. 机器人移动过快")
            print("   3. 需要更长的初始化时间")
            return False
            
        except Exception as e:
            print(f"❌ 检测失败: {e}")
            return False
    
    def get_current_pose(self):
        """获取当前位姿"""
        print("\n" + "="*60)
        print("📋 步骤 2: 获取当前位姿")
        print("="*60)
        
        pose_data = {'received': False}
        
        def odom_callback(msg):
            if not pose_data['received']:
                pose_data['received'] = True
                pose_data['pose'] = msg.pose.pose
                pos = msg.pose.pose.position
                ori = msg.pose.pose.orientation
                print(f"\n✅ 获取到当前位姿 (/slam_odom):")
                print(f"   位置: x={pos.x:.3f}, y={pos.y:.3f}, z={pos.z:.3f}")
                
                # 转换为 RPY 角度
                import tf.transformations as tfs
                quat = [ori.x, ori.y, ori.z, ori.w]
                roll, pitch, yaw = tfs.euler_from_quaternion(quat)
                print(f"   姿态: roll={roll:.3f}, pitch={pitch:.3f}, yaw={yaw:.3f} ({yaw*180/3.14159:.1f}°)")
                
                self.current_pose = {
                    'x': pos.x,
                    'y': pos.y,
                    'z': pos.z,
                    'roll': roll,
                    'pitch': pitch,
                    'yaw': yaw
                }
        
        # 订阅 odom 话题
        sub = rospy.Subscriber('/slam_odom', Odometry, odom_callback)
        
        # 等待接收数据
        timeout = 5.0
        start_time = time.time()
        
        print("\n⏳ 等待位姿数据...")
        while not pose_data['received'] and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        sub.unregister()
        
        if pose_data['received']:
            self.odom_received = True
            return True
        else:
            print(f"\n❌ {timeout} 秒内未收到位姿数据")
            print("   请确保导航系统正常运行")
            return False
    
    def call_reloc_with_options(self):
        """提供多种重定位选项"""
        print("\n" + "="*60)
        print("📋 步骤 3: 选择重定位方式")
        print("="*60)
        
        pcd_path = '/home/unitree/tang/WK/G1Nav2D/src/fastlio2/PCD/map.pcd'
        
        print("\n🎯 可选方案:")
        print("-"*60)
        print("1️⃣  使用当前位姿作为初始猜测 (推荐)")
        if self.odom_received and self.current_pose:
            p = self.current_pose
            print(f"    将使用: x={p['x']:.2f}, y={p['y']:.2f}, yaw={p['yaw']*180/3.14159:.1f}°")
        else:
            print("    ⚠️  当前位姿不可用")
        
        print("\n2️⃣  使用自定义位姿")
        print("    你可以输入具体的 x, y, yaw 值")
        
        print("\n3️⃣  使用原始的全零位姿 (0,0,0,0,0,0)")
        print("    ⚠️  可能会因重力对齐导致失败")
        
        print("\n4️⃣  测试模式: 打印详细信息但不执行")
        print("-"*60)
        
        try:
            choice = input("\n请选择方案 (1/2/3/4): ").strip()
            
            if choice == '1':
                if not self.odom_received or not self.current_pose:
                    print("❌ 错误: 当前位姿不可用，请选择其他方案")
                    return False
                return self._do_reloc(pcd_path, self.current_pose)
            
            elif choice == '2':
                return self._get_custom_pose_and_reloc(pcd_path)
            
            elif choice == '3':
                zero_pose = {
                    'x': 0.0, 'y': 0.0, 'z': 0.0,
                    'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0
                }
                return self._do_reloc(pcd_path, zero_pose)
            
            elif choice == '4':
                self._print_debug_info(pcd_path)
                return True
            
            else:
                print("❌ 无效选择")
                return False
                
        except KeyboardInterrupt:
            print("\n\n❌ 用户取消操作")
            return False
    
    def _get_custom_pose_and_reloc(self, pcd_path):
        """获取自定义位姿并执行重定位"""
        print("\n📍 输入自定义位姿:")
        print("(直接回车使用默认值)")
        
        try:
            x = input("  x [0.0]: ").strip()
            x = float(x) if x else 0.0
            
            y = input("  y [0.0]: ").strip()
            y = float(y) if y else 0.0
            
            z = input("  z [0.0]: ").strip()
            z = float(z) if z else 0.0
            
            yaw_deg = input("  yaw (度) [0.0]: ").strip()
            yaw = float(yaw_deg) * 3.14159 / 180.0 if yaw_deg else 0.0
            
            custom_pose = {
                'x': x, 'y': y, 'z': z,
                'roll': 0.0, 'pitch': 0.0, 'yaw': yaw
            }
            
            print(f"\n✅ 自定义位姿: x={x}, y={y}, yaw={float(yaw_deg) if yaw_deg else 0.0}°")
            return self._do_reloc(pcd_path, custom_pose)
            
        except ValueError as e:
            print(f"❌ 输入格式错误: {e}")
            return False
    
    def _do_reloc(self, pcd_path, pose):
        """执行重定位服务调用"""
        print("\n" + "="*60)
        print("📋 步骤 4: 执行重定位")
        print("="*60)
        
        print(f"\n🎯 重定位参数:")
        print(f"   PCD路径: {pcd_path}")
        print(f"   位置: x={pose['x']:.3f}, y={pose['y']:.3f}, z={pose['z']:.3f}")
        print(f"   姿态: roll={pose['roll']:.3f}, pitch={pose['pitch']:.3f}, yaw={pose['yaw']:.3f}")
        
        if not self.imu_ready:
            print("\n⚠️  警告: IMU 未完全初始化!")
            print("   重定位可能失败，建议等待 IMU 初始化完成")
            
            confirm = input("\n是否继续? (y/n): ").strip().lower()
            if confirm != 'y':
                print("❌ 已取消")
                return False
        
        try:
            print("\n⏳ 调用重定位服务...")
            rospy.wait_for_service('/slam_reloc', timeout=10.0)
            reloc_proxy = rospy.ServiceProxy('/slam_reloc', SlamReLoc)
            
            result = reloc_proxy(
                pcd_path,
                pose['x'], pose['y'], pose['z'],
                pose['roll'], pose['pitch'], pose['yaw']
            )
            
            print(f"\n✅ 服务调用成功!")
            print(f"   返回状态: {result.status}")
            print(f"   返回消息: {result.message}")
            
            # 等待并检查结果
            print("\n⏳ 等待 ICP 配准完成 (5秒)...")
            time.sleep(5)
            
            # 再次检查重定位结果（如果服务可用）
            if HAS_RELOC_CHECK:
                try:
                    rospy.wait_for_service('/slam_reloc_check', timeout=5.0)
                    check_proxy = rospy.ServiceProxy('/slam_reloc_check', fastlio.srv.SlamRelocCheck)
                    check_result = check_proxy()
                    
                    if check_result.status:
                        print("\n🎉 重定位成功!")
                        print("   ✅ ICP 配准收敛")
                        print("   ✅ 位姿已更新")
                        return True
                    else:
                        print("\n❌ 重定位失败!")
                        print("   ❌ ICP 配准未成功")
                        print("\n💡 建议尝试:")
                        print("   1. 检查机器人是否在地图范围内")
                        print("   2. 尝试不同的初始位姿 (方案2)")
                        print("   3. 增大 localize.yaml 中的 xy_offset 和 thresh 参数")
                        return False
                        
                except Exception as e:
                    print(f"\n⚠️  无法验证结果: {e}")
                    print("   请在 RViz 中查看配准效果")
                    return True
            else:
                print("\n✅ 重定位服务已调用!")
                print("   ⏳ 请在 RViz 中查看配准效果")
                return True
                
        except rospy.ServiceException as e:
            print(f"\n❌ 服务调用失败: {e}")
            return False
        except Exception as e:
            print(f"\n❌ 异常: {e}")
            return False
    
    def _print_debug_info(self, pcd_path):
        """打印调试信息"""
        print("\n" + "="*60)
        print("🔍 调试信息")
        print("="*60)
        
        print(f"\n📁 PCD 文件: {pcd_path}")
        import os
        if os.path.exists(pcd_path):
            size = os.path.getsize(pcd_path) / (1024*1024)
            print(f"   ✅ 文件存在，大小: {size:.2f} MB")
        else:
            print(f"   ❌ 文件不存在!")
        
        print(f"\n📊 IMU 状态: {'✅ 已初始化' if self.imu_ready else '❌ 未初始化'}")
        print(f"📊 位姿数据: {'✅ 已获取' if self.odom_received else '❌ 未获取'}")
        
        if self.current_pose:
            p = self.current_pose
            print(f"\n📍 当前位姿:")
            print(f"   x={p['x']:.3f}, y={p['y']:.3f}, z={p['z']:.3f}")
            print(f"   roll={p['roll']:.3f}, pitch={p['pitch']:.3f}, yaw={p['yaw']:.3f}")
        
        print("\n📝 ROS 话题和服务:")
        topics = ['/livox/imu', '/livox/lidar', '/slam_odom']
        for topic in topics:
            pub_count = rospy.get_published_topics(topic)
            status = "✅" if len(pub_count) > 0 else "❌"
            print(f"   {status} {topic}: {len(pub_count)} 个发布者")
        
        services = ['/slam_reloc', '/slam_reloc_check', '/slam_hold', '/slam_start']
        for svc in services:
            try:
                rospy.wait_for_service(svc, timeout=1.0)
                print(f"   ✅ 服务: {svc}")
            except:
                print(f"   ❌ 服务: {svc} (不存在)")


def main():
    print("\n" + "🤖 "*20)
    print("🎯 G1Nav2D 重定位调试工具")
    print("   结合方案1(等待IMU初始化) + 方案3(合理初始位姿)")
    print("🤖 "*20 + "\n")
    
    # 初始化 ROS 节点
    rospy.init_node('reloc_debugger', anonymous=True)
    
    debugger = RelocDebugger()
    
    # 步骤1: 检测 IMU 状态
    if not debugger.check_imu_status():
        print("\n⚠️  IMU 未就绪，但仍可继续调试...")
    
    # 步骤2: 获取当前位姿
    debugger.get_current_pose()
    
    # 步骤3 & 4: 选择方案并执行
    success = debugger.call_reloc_with_options()
    
    print("\n" + "="*60)
    if success:
        print("✅ 调试完成")
    else:
        print("❌ 调试未成功")
    print("="*60 + "\n")


if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
    except KeyboardInterrupt:
        print("\n\n👋 用户中断")

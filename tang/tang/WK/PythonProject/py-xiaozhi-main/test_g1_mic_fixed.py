#!/usr/bin/env python3
"""
G1麦克风组播接收测试脚本 - 修复版
按照官方C++示例的方法加入组播组
"""
import socket
import struct
import time
import sys

GROUP_IP = "239.168.123.161"
PORT = 5555

def get_local_ip_for_multicast():
    """获取本地用于组播的IP地址"""
    import subprocess
    try:
        result = subprocess.run(['ip', 'addr', 'show', 'eth0'],
                              capture_output=True, text=True)
        output = result.stdout
        for line in output.split('\n'):
            if 'inet ' in line and '192.168.123.' in line:
                parts = line.strip().split()
                return parts[1].split('/')[0]
    except Exception as e:
        print(f"获取本地IP失败: {e}")
    return None

print("G1麦克风组播接收测试 (修复版)")
print("=" * 50)

# 获取本地IP
local_ip = get_local_ip_for_multicast()
if local_ip:
    print(f"本地IP: {local_ip}")
else:
    print("警告: 无法获取本地IP，使用默认eth0配置")
    local_ip = "192.168.123.164"  # fallback

print(f"组播地址: {GROUP_IP}:{PORT}")
print("请确保G1机器人处于唤醒模式")
print("=" * 50)

try:
    # 创建UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # 设置套接字选项，允许地址重用
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # 如果在Linux上，还需要SO_REUSEPORT
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except (AttributeError, OSError):
        pass

    # 绑定到端口
    local_addr = ('', PORT)
    sock.bind(local_addr)
    print(f"已绑定到端口 {PORT}")

    # 加入组播组 - 使用本地IP而不是0.0.0.0
    mreq = struct.pack('4s4s', socket.inet_aton(GROUP_IP), socket.inet_aton(local_ip))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    print(f"已加入组播组 {GROUP_IP}，接口: {local_ip}")

    # 设置超时
    sock.settimeout(5.0)

    print("\n开始接收麦克风数据...")
    print("请对G1机器人说话，观察是否有数据接收")
    print("按 Ctrl+C 退出\n")

    start_time = time.time()
    packet_count = 0
    last_packet_time = start_time

    while True:
        try:
            # 接收数据
            data, addr = sock.recvfrom(2048)

            elapsed = time.time() - start_time
            packet_count += 1
            last_packet_time = time.time()

            # 计算音频参数
            bytes_per_sample = 2  # 16bit
            sample_rate = 16000
            duration_seconds = len(data) / (bytes_per_sample * sample_rate)

            print(f"[{elapsed:.2f}s] 收到数据包: {len(data)} 字节 ({duration_seconds:.3f}秒音频), 来自={addr}")

            # 每10个数据包显示统计
            if packet_count % 10 == 0:
                print(f"累计接收 {packet_count} 个数据包")

        except socket.timeout:
            if packet_count > 0:
                elapsed_since_last = time.time() - last_packet_time
                if elapsed_since_last > 10:
                    print(f"最后数据包后已等待 {elapsed_since_last:.1f}秒...")
        except KeyboardInterrupt:
            print("\n测试结束")
            break
        except Exception as e:
            print(f"错误: {e}")
            break

    print(f"\n测试结束")
    print(f"总接收数据包数: {packet_count}")

finally:
    try:
        sock.close()
    except:
        pass
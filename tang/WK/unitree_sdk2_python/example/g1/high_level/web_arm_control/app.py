#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import math
import subprocess
import threading
import logging

# ===== 修复：禁用 apport 错误报告（它尝试 import apt 会触发段错误）=====
# systemd 环境下 Python 异常时会调用 sys.excepthook → apport → apt → SEGV
# 替换 excepthook 为简单版本，避免触发 apt
def _simple_excepthook(type, value, tb):
    import traceback
    traceback.print_exception(type, value, tb)
sys.excepthook = _simple_excepthook

from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit

sys.path.append('/home/unitree/tang/WK/unitree_sdk2_python')

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_, WirelessController_
from unitree_sdk2py.core.channel import ChannelPublisher

log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

# 屏蔽 DDS Reader 的 take sample error 日志（机器人未连接时持续刷屏到 stderr）
class _FilteredStream:
    """包装 stdout/stderr，过滤掉 DDS 刷屏日志"""
    def __init__(self, original):
        self._original = original
        self._buf = ""

    def write(self, data):
        if 'Reader' in data and ('take sample' in data or 'sample error' in data.lower()):
            return  # 静默丢弃
        self._buf += data
        self._original.write(data)

    def flush(self):
        self._original.flush()

    # 兼容属性
    @property
    def encoding(self): return getattr(self._original, 'encoding', 'utf-8')
    @property
    def errors(self): return getattr(self._original, 'errors', 'strict')
    def fileno(self): return self._original.fileno()
    def isatty(self): return self._original.isatty()
    def __getattr__(self, name): return getattr(self._original, name)

import sys
sys.stdout = _FilteredStream(sys.stdout)
sys.stderr = _FilteredStream(sys.stderr)

class PollingFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if '/api/get_velocity' in msg or '/api/status' in msg:
            return False
        if 'Reader' in msg and 'take sample error' in msg:
            return False
        return True

log.addFilter(PollingFilter())

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ===== 全局异常处理器：确保所有错误返回 JSON，而不是 HTML =====
@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': f'服务器内部错误: {str(error)}'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({'success': False, 'message': f'异常: {str(e)}'}), 500

# 初始化全局变量
arm_client = None
initialized = False
current_action = None
action_lock = threading.Lock()

# 导航相关全局变量
navigation_running = False
navigation_process = None
rviz_process = None
rviz_streaming = False
vnc_process = None

# 展览与巡逻功能模块全局变量
recorded_points = []
websockify_process = None
VNC_DISPLAY = ':2'
VNC_PORT = 5902
WEBSOCKIFY_PORT = 6080
NOVNC_PATH = '/home/unitree/tang/noVNC'

# 运动控制相关全局变量
loco_running = False
loco_process = None
loco_log_thread = None
loco_log_buffer = []  # 日志缓冲区，保存最近的日志

# 小野AI相关全局变量
xiaoye_running = False
xiaoye_process = None

# 人脸识别模块 (g1_face_greet.py 子进程)
face_greet_running = False
face_greet_process = None
face_greet_log_thread = None
face_greet_log_buffer = []
FACE_GREET_SCRIPT = '/home/unitree/tang/WK/unitree_sdk2_python/example/g1/high_level/g1_face_greet.py'

# 手势识别模块 (g1_gesture_control.py 子进程)
gesture_control_running = False
gesture_control_process = None
gesture_control_log_thread = None
gesture_control_log_buffer = []
GESTURE_CONTROL_SCRIPT = '/home/unitree/tang/WK/unitree_sdk2_python/example/g1/high_level/g1_gesture_control.py'

# 展览导航相关全局变量
exhibition_running = False
exhibition_process = None

# 展览路径编辑相关全局变量
current_editing_path = []  # 当前正在编辑的路径点列表
EXHIBITION_PATH_DIR = '/home/unitree/tang/exhibition_paths'  # 路径保存目录

# 建图功能相关全局变量
mapping_running = False
mapping_process = None

# 地图管理相关全局变量
selected_map = None  # 当前选中的导航地图（不含路径，只有文件名如 "mymap"）

# 地图原点缓存（启动时自动从yaml文件动态加载）
MAP_ORIGINS = {}
MAP_DIR = '/home/unitree/tang/map'

# PCD 点云地图目录（每个地图可以有自己的 PCD 文件）
PCD_DIR = os.path.expanduser('~/tang/WK/G1Nav2D/src/fastlio2/PCD')

def _load_map_origins_from_yaml():
    """启动时扫描地图目录，从所有.yaml文件动态加载origin"""
    global MAP_ORIGINS
    import re
    import os
    
    MAP_ORIGINS = {}
    
    if not os.path.exists(MAP_DIR):
        print(f"[MAP] ⚠️ 地图目录不存在: {MAP_DIR}")
        return
    
    try:
        for filename in os.listdir(MAP_DIR):
            if filename.endswith('.yaml'):
                map_name = filename.replace('.yaml', '')
                yaml_path = os.path.join(MAP_DIR, filename)
                
                try:
                    with open(yaml_path, 'r') as f:
                        content = f.read()
                    
                    match = re.search(r'origin:\s*\[([-\d.]+),\s*([-\d.]+)', content)
                    if match:
                        origin_x = float(match.group(1))
                        origin_y = float(match.group(2))
                        MAP_ORIGINS[map_name] = {
                            'x': origin_x,
                            'y': origin_y,
                            'desc': f'{map_name} (从{filename}读取)',
                            'source': yaml_path
                        }
                        print(f"[MAP] ✅ 加载 [{map_name}] 原点: ({origin_x:.3f}, {origin_y:.3f})")
                    else:
                        print(f"[MAP] ⚠️ 无法解析 {filename} 的origin")
                except Exception as e:
                    print(f"[MAP] ❌ 读取 {filename} 失败: {e}")
        
        print(f"[MAP] 📋 共加载 {len(MAP_ORIGINS)} 个地图原点配置")
        
    except Exception as e:
        print(f"[MAP] ❌ 扫描地图目录失败: {e}")

def get_pcd_path_for_map(map_name):
    """
    根据地图名称自动选择对应的 PCD 文件
    
    PCD 文件查找优先级：
    1. {map_name}.pcd （地图专用 PCD 文件）⭐ 最优先
    2. map.pcd （默认/通用 PCD 文件）⭐ 备选
    
    Args:
        map_name: 地图名称（如 "mymap", "zhanting3"）
    
    Returns:
        pcd_path: PCD 文件的完整路径
        source_type: "specific" | "default" | "missing"
        message: 描述信息
    """
    if not map_name:
        return None, None, "未指定地图"
    
    # 优先级 1：查找地图专用的 PCD 文件（如 mymap.pcd, zhanting3.pcd）
    specific_pcd = os.path.join(PCD_DIR, f'{map_name}.pcd')
    if os.path.exists(specific_pcd):
        file_size = os.path.getsize(specific_pcd) / (1024 * 1024)  # MB
        print(f"[PCD] ✅ 使用专用文件: {map_name}.pcd ({file_size:.2f} MB)")
        return specific_pcd, 'specific', f'使用 [{map_name}] 专用 PCD'
    
    # 优先级 2：回退到默认的 map.pcd
    default_pcd = os.path.join(PCD_DIR, 'map.pcd')
    if os.path.exists(default_pcd):
        file_size = os.path.getsize(default_pcd) / (1024 * 1024)  # MB
        print(f"[PCD] ⚠️ 回退到默认: map.pcd ({file_size:.2f} MB) - 建议为 [{map_name}] 创建专用 PCD")
        return default_pcd, 'default', f'回退到默认 map.pcd（建议创建 {map_name}.pcd）'
    
    # 优先级 3：都没有找到
    print(f"[PCD] ❌ 未找到任何 PCD 文件！目录: {PCD_DIR}")
    return default_pcd, 'missing', f'⚠️ PCD 文件不存在！请先建图保存点云'

def check_pcd_file_valid(pcd_path, map_name=None):
    """
    检查 PCD 文件是否有效
    
    Args:
        pcd_path: PCD 文件路径
        map_name: 关联的地图名称（可选）
    
    Returns:
        (is_valid, error_message)
    """
    if not pcd_path or not os.path.exists(pcd_path):
        return False, f"PCD 文件不存在: {pcd_path}"
    
    file_size = os.path.getsize(pcd_path)
    min_valid_size = 10 * 1024  # 至少 10KB 才是有效 PCD
    
    if file_size < min_valid_size:
        return False, f"PCD 文件过小 ({file_size} bytes)，可能是空文件或损坏"
    
    file_size_mb = file_size / (1024 * 1024)
    if file_size_mb < 0.5:
        print(f"[PCD] ⚠️ 文件较小 ({file_size_mb:.2f} MB)，可能不包含完整的地图数据")
        return True, None
    elif file_size_mb > 100:
        print(f"[PCD] ℹ️ 文件较大 ({file_size_mb:.1f} MB)，ICP 配准可能较慢")
    
    return True, None

def list_available_pcds():
    """列出所有可用的 PCD 文件"""
    pcd_files = {}
    if os.path.exists(PCD_DIR):
        for filename in os.listdir(PCD_DIR):
            if filename.endswith('.pcd'):
                filepath = os.path.join(PCD_DIR, filename)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                mtime = os.path.getmtime(filepath)
                import datetime
                mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                pcd_files[filename] = {
                    'path': filepath,
                    'size_mb': round(size_mb, 2),
                    'modified': mtime_str
                }
    return pcd_files

# 启动时立即加载所有地图原点
_load_map_origins_from_yaml()

# 启动时打印可用 PCD 文件信息
print("\n" + "="*60)
print("[PCD] 📋 可用的 PCD 点云地图文件:")
print("="*60)
available_pcds = list_available_pcds()
if available_pcds:
    for name, info in sorted(available_pcds.items()):
        marker = "🔹" if name != "map.pcd" else "📍"
        print(f"  {marker} {name:<20} {info['size_mb']:>6.2f} MB   修改时间: {info['modified']}")
else:
    print("  ⚠️  未找到任何 PCD 文件！")
    print(f"     请确保目录存在并已保存地图: {PCD_DIR}")
print("="*60 + "\n")

# 运动控制（摇杆/FSM）相关全局变量
loco_client = None
current_vx = 0.0
current_vy = 0.0
current_vw = 0.0
odom_lock = threading.Lock()
current_gear = 1

GEAR_SPEEDS = {
    1: {"vx": 0.3, "vy": 0.2, "wz": 0.4},
    2: {"vx": 0.6, "vy": 0.3, "wz": 0.8},
    3: {"vx": 1.0, "vy": 0.5, "wz": 1.2},
}

FSM_MODES = {
    0:   {"name": "ZeroTorque",  "desc": "零力矩",     "group": "基础"},
    1:   {"name": "Damp",        "desc": "阻尼模式",   "group": "基础"},
    3:   {"name": "Sit",         "desc": "坐下",       "group": "姿态"},
    4:   {"name": "Ready",       "desc": "预备模式",   "group": "姿态"},
    200: {"name": "Start",       "desc": "启动运动",   "group": "运动"},
    501: {"name": "Walk",        "desc": "常规走路",   "group": "运动"},
    702: {"name": "Lie2StandUp", "desc": "躺→站",     "group": "姿态"},
    706: {"name": "Squat2Stand", "desc": "蹲↔站",     "group": "姿态"},
    802: {"name": "Run",         "desc": "走跑模式",   "group": "运动"},
    503: {"name": "Dance",       "desc": "舞蹈模式",   "group": "运动"},
}

# ============ 虚拟遥控器模块全局变量 ============
class RemoteState:
    """管理虚拟遥控器的摇杆和按键状态"""
    KEY_MAP = {
        'R1': 0, 'L1': 1, 'Start': 2, 'Select': 3,
        'R2': 4, 'L2': 5, 'F1': 6, 'F3': 7,
        'A': 8, 'B': 9, 'X': 10, 'Y': 11,
        'Up': 12, 'Right': 13, 'Down': 14, 'Left': 15,
    }

    def __init__(self):
        self.lx = 0.0
        self.ly = 0.0
        self.rx = 0.0
        self.ry = 0.0
        self.keys = 0
        self.lock = threading.Lock()

    def set_joystick(self, stick, x, y):
        with self.lock:
            if stick == 'left':
                self.lx = max(-1.0, min(1.0, x))
                self.ly = max(-1.0, min(1.0, y))
            elif stick == 'right':
                self.rx = max(-1.0, min(1.0, x))
                self.ry = max(-1.0, min(1.0, y))

    def set_button(self, name, pressed):
        with self.lock:
            bit = self.KEY_MAP.get(name)
            if bit is not None:
                if pressed:
                    self.keys |= (1 << bit)
                else:
                    self.keys &= ~(1 << bit)

    def get_state(self):
        with self.lock:
            return self.lx, self.ly, self.rx, self.ry, self.keys

    def reset(self):
        with self.lock:
            self.lx = 0.0; self.ly = 0.0
            self.rx = 0.0; self.ry = 0.0
            self.keys = 0


class VirtualRemotePublisher:
    """向 rt/wirelesscontroller 发布 WirelessController_ 消息（完全独立，不依赖init_clients）"""

    def __init__(self):
        self.publisher = None
        self.initialized = False
        self.running = False
        self.publish_thread = None
        self.state = RemoteState()
        self.publish_rate = 100  # Hz

    def init_dds(self, network_interface='eth0'):
        """独立初始化DDS通道和Publisher（与参考项目一致）"""
        global _dds_channel_initialized
        try:
            if not _dds_channel_initialized:
                ChannelFactoryInitialize(0, network_interface)
                _dds_channel_initialized = True
            self.publisher = ChannelPublisher("rt/wirelesscontroller", WirelessController_)
            self.publisher.Init()
            self.initialized = True
            self.start_publishing()
            print(f"✅ 虚拟遥控器初始化成功 (接口: {network_interface})，已启动发布线程")
            return True, f"虚拟遥控器初始化成功 (接口: {network_interface})"
        except Exception as e:
            print(f"❌ 虚拟遥控器初始化失败: {e}")
            return False, str(e)

    def start_publishing(self):
        if not self.initialized:
            return False
        if self.running:
            return True
        self.running = True
        self.publish_thread = threading.Thread(target=self._publish_loop, daemon=True)
        self.publish_thread.start()
        return True

    def stop_publishing(self):
        self.running = False
        if self.publish_thread:
            self.publish_thread.join(timeout=2.0)
            self.publish_thread = None

    def _publish_loop(self):
        interval = 1.0 / self.publish_rate
        while self.running:
            try:
                lx, ly, rx, ry, keys = self.state.get_state()
                msg = WirelessController_(lx=lx, ly=ly, rx=rx, ry=ry, keys=keys)
                self.publisher.Write(msg)
            except Exception as e:
                print(f"[VirtualRemote] 发布错误: {e}")
            time.sleep(interval)

    def get_status(self):
        return {'initialized': self.initialized, 'running': self.running}


virtual_remote_publisher = VirtualRemotePublisher()
virtual_remote_connected_clients = 0


# ============ 键盘控制模块 ============

ARM_ACTIONS = [
    {"id": 0,  "key": "0", "name": "release arm",    "map": "release arm",    "need_release": False, "desc": "释放手臂"},
    {"id": 1,  "key": "1", "name": "shake hand",     "map": "shake hand",     "need_release": True,  "desc": "握手"},
    {"id": 2,  "key": "2", "name": "high five",      "map": "high five",      "need_release": True,  "desc": "举手你好"},
    {"id": 3,  "key": "3", "name": "hug",            "map": "hug",            "need_release": True,  "desc": "拥抱"},
    {"id": 4,  "key": "4", "name": "high wave",      "map": "high wave",      "need_release": False, "desc": "拜拜挥手"},
    {"id": 5,  "key": "5", "name": "clap",           "map": "clap",           "need_release": False, "desc": "鼓掌"},
    {"id": 6,  "key": "6", "name": "face wave",      "map": "face wave",      "need_release": False, "desc": "低位挥手"},
    {"id": 7,  "key": "7", "name": "left kiss",      "map": "left kiss",      "need_release": False, "desc": "左飞吻"},
    {"id": 8,  "key": "8", "name": "heart",          "map": "heart",          "need_release": True,  "desc": "比心"},
    {"id": 9,  "key": "9", "name": "right heart",    "map": "right heart",    "need_release": True,  "desc": "右比心"},
    {"id": 10, "key": "z", "name": "hands up",       "map": "hands up",       "need_release": True,  "desc": "双手举起"},
    {"id": 11, "key": "x", "name": "x-ray",          "map": "x-ray",          "need_release": True,  "desc": "迪迦光线"},
    {"id": 12, "key": "c", "name": "right hand up",  "map": "right hand up",  "need_release": True,  "desc": "右手举起"},
    {"id": 13, "key": "v", "name": "reject",         "map": "reject",         "need_release": True,  "desc": "拒绝"},
    {"id": 14, "key": "b", "name": "right kiss",     "map": "right kiss",     "need_release": False, "desc": "右飞吻"},
    {"id": 15, "key": "n", "name": "two-hand kiss",  "map": "two-hand kiss",  "need_release": False, "desc": "双手飞吻"},
]

KEY_TO_ARM_ACTION = {}
for a in ARM_ACTIONS:
    KEY_TO_ARM_ACTION[a["key"]] = a

# 键盘控制专用常量（避免与全局 FSM_MODES 冲突）
KB_FSM_MODES = {
    "0": {"id": 0,   "desc": "零力矩",   "name": "ZeroTorque"},
    "1": {"id": 1,   "desc": "阻尼模式", "name": "Damp"},
    "3": {"id": 3,   "desc": "坐下",     "name": "Sit"},
    "4": {"id": 4,   "desc": "预备模式", "name": "Ready"},
    "5": {"id": 501, "desc": "常规走路", "name": "Walk"},
    "6": {"id": 200, "desc": "启动运动", "name": "Start"},
    "7": {"id": 702, "desc": "躺→站",   "name": "Lie2StandUp"},
    "8": {"id": 706, "desc": "蹲↔站",   "name": "Squat2Stand"},
    "9": {"id": 802, "desc": "走跑模式", "name": "Run"},
}

KB_GEAR_SPEEDS = {
    1: {"vx": 0.3, "vy": 0.2, "wz": 0.4},
    2: {"vx": 0.6, "vy": 0.3, "wz": 0.8},
    3: {"vx": 1.0, "vy": 0.5, "wz": 1.2},
}


class KeyboardController:
    """键盘控制器 - 后台线程持续发送运动指令"""

    def __init__(self):
        self.enabled = False
        self.running = False
        self.control_thread = None
        self.lock = threading.Lock()
        self.consecutive_errors = 0  # 连续错误计数

        # 运动目标值
        self.target_vx = 0.0
        self.target_vy = 0.0
        self.target_wz = 0.0

        # 平滑后的发送值
        self.send_vx = 0.0
        self.send_vy = 0.0
        self.send_wz = 0.0

        # 档位和参数
        self.current_gear = 1
        self.smoothing = 0.15
        self.stop_threshold = 0.005

        # 模式切换 (arm / fsm)
        self.key_mode = "arm"

        # 机械臂状态
        self.arm_executing = False
        self.arm_lock = threading.Lock()

    def enable(self):
        """启用键盘控制"""
        if self.enabled:
            return True, "已启用"
        if not initialized or loco_client is None:
            return False, "SDK未初始化，请先初始化"
        self.enabled = True
        if not self.running:
            self._start_thread()
        print("[Keyboard] ✅ 键盘控制已启用")
        return True, "键盘控制已启用"

    def disable(self):
        """禁用键盘控制"""
        self.enabled = False
        with self.lock:
            self.target_vx = 0.0
            self.target_vy = 0.0
            self.target_wz = 0.0
        try:
            loco_client.StopMove()
        except:
            pass
        print("[Keyboard] ⏹️ 键盘控制已禁用")
        return True, "键盘控制已禁用"

    def _start_thread(self):
        if self.running:
            return
        self.running = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        print("[Keyboard] 控制线程已启动")

    def _stop_thread(self):
        self.running = False
        if self.control_thread:
            self.control_thread.join(timeout=2.0)
            self.control_thread = None

    def _control_loop(self):
        """后台循环：平滑插值 + 发送运动指令 (50Hz)"""
        while self.running:
            if not self.enabled:
                time.sleep(0.02)
                continue

            # 连续错误过多时降低频率，避免频繁崩溃
            if self.consecutive_errors > 10:
                time.sleep(0.5)
                self.consecutive_errors = 0
                continue

            try:
                global loco_client
                if loco_client is None:
                    time.sleep(0.1)
                    continue

                with self.lock:
                    tvx, tvy, twz = self.target_vx, self.target_vy, self.target_wz

                # 平滑插值
                self.send_vx = self._smooth(self.send_vx, tvx)
                self.send_vy = self._smooth(self.send_vy, tvy)
                self.send_wz = self._smooth(self.send_wz, twz)

                # 发送运动指令
                if (abs(self.send_vx) < self.stop_threshold and
                    abs(self.send_vy) < self.stop_threshold and
                    abs(self.send_wz) < self.stop_threshold):
                    loco_client.StopMove()
                else:
                    loco_client.Move(self.send_vx, self.send_vy, self.send_wz)

                self.consecutive_errors = 0  # 成功后重置错误计数

            except Exception as e:
                self.consecutive_errors += 1
                if self.consecutive_errors <= 3:  # 只打印前几次
                    print(f"[Keyboard] 控制循环异常 ({self.consecutive_errors}次): {e}")
            except SystemExit:
                raise
            except BaseException as e:
                # 捕获所有异常包括可能的底层崩溃信号
                self.consecutive_errors += 1
                print(f"[Keyboard] 底层异常 ({self.consecutive_errors}次): {type(e).__name__}")
                time.sleep(0.5)  # 等待恢复

            time.sleep(0.02)

    def _smooth(self, current, target):
        if abs(target - current) < self.stop_threshold:
            return target
        return current + (target - current) * self.smoothing

    def process_key(self, key):
        """处理按键事件"""
        if not self.enabled:
            return None, "键盘控制未启用"

        key_lower = key.lower()

        # F键：切换 Arm/FSM 模式
        if key_lower == 'f':
            if self.key_mode == "arm":
                self.key_mode = "fsm"
                mode_info = "FSM模式 (数字键切换运动状态)"
            else:
                self.key_mode = "arm"
                mode_info = "Arm模式 (数字键执行手臂动作)"
            return {'type': 'mode_change', 'mode': self.key_mode, 'info': mode_info}, f"切换到{mode_info}"

        # FSM模式下数字键 → 切换运动状态
        if self.key_mode == "fsm" and key_lower in KB_FSM_MODES:
            return self._set_fsm(key_lower)

        # Arm模式下按键 → 执行手臂动作
        if self.key_mode == "arm":
            action_info = KEY_TO_ARM_ACTION.get(key_lower)
            if action_info:
                return self._execute_arm_action(action_info)

        # 运动控制（所有模式通用）
        gear = KB_GEAR_SPEEDS[self.current_gear]
        info = None

        if key in ('w', 'W'):
            self.target_vx = gear["vx"]
            info = f"前进 ({gear['vx']}m/s)"
        elif key in ('s', 'S'):
            self.target_vx = -gear["vx"]
            info = f"后退 ({-gear['vx']}m/s)"
        elif key in ('a', 'A'):
            self.target_vy = gear["vy"]
            info = f"左移 ({gear['vy']}m/s)"
        elif key in ('d', 'D'):
            self.target_vy = -gear["vy"]
            info = f"右移 ({-gear['vy']}m/s)"
        elif key in ('q', 'Q'):
            self.target_wz = gear["wz"]
            info = f"左转 ({gear['wz']}rad/s)"
        elif key in ('e', 'E'):
            self.target_wz = -gear["wz"]
            info = f"右转 ({-gear['wz']}rad/s)"
        elif key == ' ':
            with self.lock:
                self.target_vx = 0.0
                self.target_vy = 0.0
                self.target_wz = 0.0
            try:
                loco_client.StopMove()
            except:
                pass
            info = "急停!"
        elif key == ',':
            if self.current_gear > 1:
                self.current_gear -= 1
                gear_names = {1: "低速", 2: "中速", 3: "高速"}
                info = f"档位↓ {self.current_gear}({gear_names[self.current_gear]})"
        elif key == '.':
            if self.current_gear < 3:
                self.current_gear += 1
                gear_names = {1: "低速", 2: "中速", 3: "高速"}
                info = f"档位↑ {self.current_gear}({gear_names[self.current_gear]})"
        elif key in ('r', 'R'):
            with self.lock:
                self.target_vx = 0.0
                self.target_vy = 0.0
                self.target_wz = 0.0
            info = "速度归零"
        elif key_lower == 't':
            # T键：舞蹈模式 (ID=503)
            return self._set_fsm_direct(503, "舞蹈模式")

        if info:
            return {'type': 'move', 'target': [self.target_vx, self.target_vy, self.target_wz],
                    'gear': self.current_gear}, info
        return None, None

    def release_key(self, key):
        """松开按键时衰减目标速度"""
        if not self.enabled:
            return
        key_lower = key.lower()
        gear = KB_GEAR_SPEEDS[self.current_gear]
        changed = False
        with self.lock:
            if key_lower in ('w', 's') and self.target_vx != 0:
                self.target_vx *= 0.5
                if abs(self.target_vx) < 0.05:
                    self.target_vx = 0.0
                changed = True
            elif key_lower in ('a', 'd') and self.target_vy != 0:
                self.target_vy *= 0.5
                if abs(self.target_vy) < 0.05:
                    self.target_vy = 0.0
                changed = True
            elif key_lower in ('q', 'e') and self.target_wz != 0:
                self.target_wz *= 0.5
                if abs(self.target_wz) < 0.05:
                    self.target_wz = 0.0
                changed = True
        if changed:
            socketio.emit('keyboard_status', self.get_status())

    def _execute_arm_action(self, action_info):
        """执行机械臂动作"""
        global arm_client
        if arm_client is None:
            return {'type': 'error', 'message': '机械臂未初始化'}, "机械臂未初始化"

        with self.arm_lock:
            if self.arm_executing:
                return {'type': 'busy'}, "⏳ 机械臂正在执行中..."
            self.arm_executing = True

        def _run():
            try:
                arm_client.ExecuteAction(action_map.get(action_info["map"]))
                if action_info["need_release"]:
                    time.sleep(2.0)
                    arm_client.ExecuteAction(action_map.get("release arm"))
                socketio.emit('keyboard_status', self.get_status())
            except Exception as e:
                pass
            finally:
                with self.arm_lock:
                    self.arm_executing = False

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return {'type': 'arm_action', 'action': action_info["desc"]}, f"🤖 执行: {action_info['desc']}"

    def _set_fsm(self, key):
        """设置FSM模式"""
        mode = KB_FSM_MODES[key]
        return self._set_fsm_direct(mode["id"], mode["desc"])

    def _set_fsm_direct(self, fsm_id, desc):
        """直接设置FSM ID"""
        try:
            code = loco_client.SetFsmId(fsm_id)
            if code == 0:
                return {'type': 'fsm', 'fsm_id': fsm_id, 'desc': desc}, f"🔄 FSM → {fsm_id} ({desc}) ✅"
            else:
                return {'type': 'error', 'message': f'FSM切换失败(code:{code})'}, f"❌ FSM失败({code})"
        except Exception as e:
            return {'type': 'error', 'message': str(e)}, f"❌ FSM错误: {e}"

    def get_status(self):
        """获取当前状态"""
        gear_names = {1: "低速", 2: "中速", 3: "高速"}
        return {
            'enabled': self.enabled,
            'running': self.running,
            'mode': self.key_mode,
            'gear': self.current_gear,
            'gear_name': gear_names.get(self.current_gear, "?"),
            'target': [round(self.target_vx, 3), round(self.target_vy, 3), round(self.target_wz, 3)],
            'send': [round(self.send_vx, 3), round(self.send_vy, 3), round(self.send_wz, 3)],
            'arm_executing': self.arm_executing,
        }


# 全局键盘控制器实例
keyboard_controller = KeyboardController()


# 动作列表
action_list = [
    {"id": 0, "name": "release arm", "description": "释放机械臂"},
    {"id": 1, "name": "shake hand", "description": "握手"},
    {"id": 2, "name": "high five", "description": "手举高，你好"},
    {"id": 3, "name": "hug", "description": "拥抱"},
    {"id": 4, "name": "high wave", "description": "挥手"},
    {"id": 5, "name": "clap", "description": "鼓掌"},
    {"id": 6, "name": "face wave", "description": "面部挥手"},
    {"id": 7, "name": "left kiss", "description": "左边亲吻"},
    {"id": 8, "name": "heart", "description": "比心"},
    {"id": 9, "name": "right heart", "description": "右边比心"},
    {"id": 10, "name": "hands up", "description": "双手举起"},
    {"id": 11, "name": "x-ray", "description": "X光"},
    {"id": 12, "name": "right hand up", "description": "右手举起"},
    {"id": 13, "name": "reject", "description": "拒绝"},
    {"id": 14, "name": "right kiss", "description": "右边亲吻"},
    {"id": 15, "name": "two-hand kiss", "description": "双手亲吻"},
]

def _dds_odom_callback(msg: SportModeState_):
    global current_vx, current_vy, current_vw
    with odom_lock:
        current_vx = msg.velocity[0]
        current_vy = msg.velocity[1]
        current_vw = msg.yaw_speed

# DDS通道是否已初始化（ChannelFactoryInitialize只能调用一次）
_dds_channel_initialized = False

def init_clients(network_interface):
    """初始化机械臂客户端和运动控制客户端"""
    global arm_client, loco_client, initialized, _dds_channel_initialized
    
    if initialized:
        return True
    
    try:
        if not _dds_channel_initialized:
            ChannelFactoryInitialize(0, network_interface)
            _dds_channel_initialized = True

        loco_client = LocoClient()
        loco_client.SetTimeout(10.0)
        loco_client.Init()
        print(f"✅ 运动控制客户端初始化成功")

        arm_client = G1ArmActionClient()
        arm_client.SetTimeout(10.0)
        try:
            arm_client.Init()
            print(f"✅ 机械臂客户端初始化成功")
        except Exception as e:
            print(f"⚠️  机械臂客户端初始化失败: {e}")
            arm_client = None

        # 初始化语音动作控制器
        voice_action_controller.init_audio(network_interface)
        voice_action_controller.set_arm_client(arm_client)

        odom_sub = ChannelSubscriber("rt/odommodestate", SportModeState_)
        odom_sub.Init(_dds_odom_callback)

        initialized = True
        print(f"✅ SDK客户端初始化成功 (网络接口: {network_interface})")

        return True
    except Exception as e:
        print(f"❌ SDK客户端初始化失败: {e}")
        return False

@app.route('/')
def index():
    """主页"""
    return render_template('index.html', actions=action_list)

@app.route('/api/init', methods=['POST'])
def init_api():
    """初始化API"""
    global initialized
    
    data = request.get_json() or {}
    network_interface = data.get('network_interface', 'eth0')
    
    if initialized:
        return jsonify({'success': True, 'message': '已经初始化', 'initialized': True})
    
    success = init_clients(network_interface)
    return jsonify({
        'success': success,
        'message': '初始化成功' if success else '初始化失败',
        'initialized': success
    })


# ============================================================
#  语音动作输出模块
# ============================================================
VOICE_ACTIONS = {
    0: {"name": "释放手臂", "en_name": "release arm", "desc": "放松机械臂到自然下垂位置"},
    1: {"name": "握手", "en_name": "shake hand", "desc": "伸出右手握手致意"},
    2: {"name": "击掌", "en_name": "high five", "desc": "高举右手准备击掌"},
    3: {"name": "拥抱", "en_name": "hug", "desc": "张开双臂做出拥抱姿势"},
    4: {"name": "挥手", "en_name": "high wave", "desc": "高高挥动手臂打招呼"},
    5: {"name": "鼓掌", "en_name": "clap", "desc": "双手鼓掌表示赞赏"},
    6: {"name": "面部挥手", "en_name": "face wave", "desc": "在面前挥手示意"},
    7: {"name": "左亲吻", "en_name": "left kiss", "desc": "向左侧飞吻"},
    8: {"name": "比心", "en_name": "heart", "desc": "双手比出爱心形状"},
    9: {"name": "右比心", "en_name": "right heart", "desc": "单手比出爱心形状"},
    10: {"name": "举手", "en_name": "hands up", "desc": "双手高举过头顶"},
    11: {"name": "X光", "en_name": "x-ray", "desc": "做出X射线扫描姿势"},
    12: {"name": "右手举起", "en_name": "right hand up", "desc": "右臂向上伸展"},
    13: {"name": "拒绝", "en_name": "reject", "desc": "做出拒绝/否定的手势"},
    14: {"name": "右亲吻", "en_name": "right kiss", "desc": "向右侧飞吻"},
    15: {"name": "双手吻", "en_name": "two-hand kiss", "desc": "双手同时飞吻"}
}

PRESET_VOICES = {
    "greeting": {
        "label": "问候语",
        "voices": [
            "您好，我是G1机器人！",
            "欢迎来到朝野科技！",
            "很高兴见到您！",
            "大家好，我是您的智能助手。",
            "Hello! Nice to meet you!"
        ]
    },
    "introduction": {
        "label": "讲解介绍",
        "voices": [
            "让我为您介绍一下这里...",
            "这是我们的产品展示区。",
            "请跟随我参观。",
            "这里是公司的核心区域。",
            "接下来我将为您详细讲解。"
        ]
    },
    "interaction": {
        "label": "互动交流",
        "voices": [
            "请问有什么可以帮助您的？",
            "请让一让我通过，谢谢！",
            "请注意安全。",
            "您想了解更多信息吗？",
            "好的，我明白了。"
        ]
    },
    "farewell": {
        "label": "告别道别",
        "voices": [
            "再见，期待下次见面！",
            "感谢您的参观！",
            "有需要随时找我！",
            "祝您生活愉快！",
            "Bye bye! See you next time!"
        ]
    },
    "entertainment": {
        "label": "娱乐表演",
        "voices": [
            "看我给大家表演个节目！",
            "准备好了吗？我要开始啦！",
            "是不是很厉害？",
            "哈哈，好玩吧！",
            "再来一次好不好？"
        ]
    }
}


class VoiceActionController:
    """语音动作控制器 - 输入文本+选择动作，让机器人执行动作并播放语音"""

    def __init__(self):
        self.audio_client = None
        self.arm_client = None
        self._ready = False
        self._executing = False

    def init_audio(self, network_interface):
        """初始化音频和机械臂客户端"""
        try:
            from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
            self.audio_client = AudioClient()
            self.audio_client.Init()
            self.audio_client.SetTimeout(10.0)
            # 唤醒音频硬件
            for i in range(5):
                try:
                    self.audio_client.GetVolume()
                    break
                except Exception:
                    time.sleep(1)
            self.audio_client.SetVolume(100)
            print("[VoiceAction] 音频系统初始化完成")
        except Exception as e:
            print(f"[VoiceAction] 音频系统初始化失败: {e}")

    def set_arm_client(self, client):
        """设置机械臂客户端（复用已有的）"""
        self.arm_client = client
        if client is not None and self.audio_client is not None:
            self._ready = True

    @property
    def ready(self):
        return self._ready and not self._executing

    def speak(self, text):
        """播放语音"""
        if not text or not text.strip():
            return False, "语音内容为空"
        if self.audio_client is None:
            return False, "音频系统未初始化"
        try:
            self.audio_client.TtsMaker(text.strip(), 0)
            estimated_duration = len(text) * 0.195
            time.sleep(max(estimated_duration, 1.0))
            return True, f"语音播放完成 ({estimated_duration:.1f}s)"
        except Exception as e:
            return False, f"语音播放失败: {e}"

    def execute_action(self, action_id):
        """执行单个动作"""
        if action_id not in VOICE_ACTIONS:
            return False, f"无效的动作ID: {action_id}"
        if self.arm_client is None:
            return False, "机械臂未初始化"

        action_info = VOICE_ACTIONS[action_id]
        try:
            self.arm_client.ExecuteAction(action_map.get(action_info["en_name"]))
            time.sleep(2.0)
            return True, f"动作 '{action_info['name']}' 执行完成"
        except Exception as e:
            return False, f"动作执行失败: {e}"

    def perform_interaction(self, text, action_id, auto_reset=True):
        """组合执行：先动作后语音，最后复位"""
        if self._executing:
            return False, "正在执行中，请稍候"
        if not self._ready:
            return False, "系统未就绪"

        self._executing = True
        results = []

        # Step 1: 执行动作
        if action_id is not None and action_id != -1:
            ok, msg = self.execute_action(action_id)
            results.append({"step": "action", "success": ok, "message": msg})
        else:
            results.append({"step": "action", "success": True, "message": "跳过动作"})

        # Step 2: 播放语音
        if text and text.strip():
            ok, msg = self.speak(text)
            results.append({"step": "voice", "success": ok, "message": msg})
        else:
            results.append({"step": "voice", "success": True, "message": "跳过语音"})

        # Step 3: 复位手臂
        if auto_reset and self.arm_client is not None:
            try:
                self.arm_client.ExecuteAction(99)
                time.sleep(3.0)
                results.append({"step": "reset", "success": True, "message": "手臂复位完成"})
            except Exception as e:
                results.append({"step": "reset", "success": False, "message": f"复位失败: {e}"})

        self._executing = False
        return True, results

    def reset_arm(self):
        """复位手臂"""
        if self.arm_client is None:
            return False, "机械臂未初始化"
        try:
            self.arm_client.ExecuteAction(99)
            time.sleep(3.0)
            return True, "手臂已复位"
        except Exception as e:
            return False, f"复位失败: {e}"


# 全局实例
voice_action_controller = VoiceActionController()


@app.route('/api/voice_actions')
def get_voice_actions():
    """获取语音动作模块的动作列表"""
    return jsonify({
        'actions': VOICE_ACTIONS,
        'preset_voices': PRESET_VOICES,
        'ready': voice_action_controller.ready,
        'executing': voice_action_controller._executing
    })



@app.route('/api/status')
def get_status():
    """获取状态"""
    with odom_lock:
        vx, vy, vw = current_vx, current_vy, current_vw
    return jsonify({
        'initialized': initialized,
        'current_action': current_action,
        'navigation_running': navigation_running,
        'rviz_streaming': rviz_streaming,
        'loco_running': loco_running,
        'xiaoye_running': xiaoye_running,
        'exhibition_running': exhibition_running,
        'mapping_running': mapping_running,
        'selected_map': selected_map,
        'current_gear': current_gear,
        'current_velocity': {'vx': round(vx, 3), 'vy': round(vy, 3), 'wz': round(vw, 3)},
        'fsm_modes': {str(k): v for k, v in FSM_MODES.items()},
        'gear_speeds': {str(k): v for k, v in GEAR_SPEEDS.items()},
    })

@app.route('/api/network_interfaces')
def get_network_interfaces():
    """获取系统可用的网络接口列表"""
    interfaces = []
    try:
        with open('/proc/net/dev', 'r') as f:
            for line in f:
                if ':' in line:
                    iface = line.split(':')[0].strip()
                    if iface != 'lo':
                        interfaces.append(iface)
    except:
        pass
    return jsonify({'interfaces': interfaces})

@app.route('/api/actions')
def get_actions():
    """获取动作列表"""
    return jsonify(action_list)

@app.route('/api/set_velocity', methods=['POST'])
def set_velocity():
    """设置速度（摇杆/键盘控制）"""
    if not initialized or loco_client is None:
        return jsonify({'success': False, 'message': '运动控制未初始化'}), 400
    data = request.get_json() or {}
    vx = float(data.get('vx', 0.0))
    vy = float(data.get('vy', 0.0))
    wz = float(data.get('wz', 0.0))
    try:
        if abs(vx) < 0.005 and abs(vy) < 0.005 and abs(wz) < 0.005:
            loco_client.StopMove()
        else:
            loco_client.Move(vx, vy, wz)
        return jsonify({'success': True, 'message': f'速度: vx={vx:.2f}, vy={vy:.2f}, wz={wz:.2f}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'速度设置失败: {str(e)}'}), 500

@app.route('/api/emergency_stop', methods=['POST'])
def emergency_stop():
    """急停"""
    if not initialized or loco_client is None:
        return jsonify({'success': False, 'message': '运动控制未初始化'}), 400
    try:
        loco_client.StopMove()
        return jsonify({'success': True, 'message': '急停成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'急停失败: {str(e)}'}), 500

@app.route('/api/set_gear', methods=['POST'])
def set_gear():
    """设置档位"""
    global current_gear
    data = request.get_json() or {}
    gear = int(data.get('gear', 1))
    if gear not in GEAR_SPEEDS:
        return jsonify({'success': False, 'message': f'无效档位: {gear}'}), 400
    current_gear = gear
    gear_names = {1: "低速", 2: "中速", 3: "高速"}
    return jsonify({
        'success': True,
        'message': f'档位: {gear} ({gear_names[gear]})',
        'gear': gear,
        'speeds': GEAR_SPEEDS[gear]
    })

@app.route('/api/set_fsm', methods=['POST'])
def set_fsm():
    """切换FSM模式"""
    if not initialized or loco_client is None:
        return jsonify({'success': False, 'message': '运动控制未初始化'}), 400
    data = request.get_json() or {}
    fsm_id = int(data.get('fsm_id', -1))
    if fsm_id not in FSM_MODES:
        return jsonify({'success': False, 'message': f'未知FSM ID: {fsm_id}'}), 400
    info = FSM_MODES[fsm_id]
    try:
        code = loco_client.SetFsmId(fsm_id)
        if code == 0:
            return jsonify({
                'success': True,
                'message': f'切换成功: {info["desc"]} ({info["name"]})',
                'fsm_id': fsm_id,
                'fsm_info': info
            })
        else:
            return jsonify({
                'success': False,
                'message': f'切换失败 (code: {code})',
                'fsm_id': fsm_id
            }), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'FSM切换失败: {str(e)}'}), 500

@app.route('/api/get_velocity', methods=['GET'])
def get_velocity():
    """获取当前速度"""
    with odom_lock:
        vx, vy, vw = current_vx, current_vy, current_vw
    return jsonify({
        'vx': round(vx, 3),
        'vy': round(vy, 3),
        'wz': round(vw, 3),
        'gear': current_gear
    })

@app.route('/api/start_navigation', methods=['POST'])
def start_navigation():
    """启动导航功能（包含RViz画面 - VNC交互式）"""
    global navigation_running, navigation_process, rviz_streaming, vnc_process, websockify_process
    
    if navigation_running:
        return jsonify({'success': False, 'message': '导航已经在运行中'}), 400

    if mapping_running:
        return jsonify({'success': False, 'message': '请先停止建图功能再启动导航'}), 400

    if not selected_map:
        return jsonify({
            'success': False,
            'message': '请先在建图模块选择一个地图，然后再启动导航'
        }), 400

    try:
        print("=== 开始清理残留进程 ===")
        
        subprocess.run(['pkill', '-9', '-f', 'navigation.launch'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'move_base'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rviz'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'roslaunch'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rosmaster'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'roscore'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rosout'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'tf2_ros.*buffer_server'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'robot_state_publisher'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'websockify'], capture_output=True)
        
        time.sleep(2)
        
        g1nav_dir = os.path.expanduser('~/tang/WK/G1Nav2D')
        env = os.environ.copy()
        env['ROS_PACKAGE_PATH'] = f"{g1nav_dir}/devel:{env.get('ROS_PACKAGE_PATH', '')}"
        
        kill_vnc = subprocess.run(
            ['vncserver', '-kill', VNC_DISPLAY],
            capture_output=True, text=True, timeout=5
        )
        print(f"VNC kill输出: {kill_vnc.stdout} {kill_vnc.stderr}")
        
        time.sleep(1)
        
        rosparam_del = subprocess.run(
            ['bash', '-c', f'source {g1nav_dir}/devel/setup.bash && rosparam delete / 2>/dev/null; true'],
            env=env, capture_output=True, timeout=5
        )
        time.sleep(2)
        
        for port in [11311, 6080]:
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                result = s.connect_ex(('localhost', port))
                if result == 0:
                    print(f"端口 {port} 仍被占用")
                else:
                    print(f"端口 {port} 已释放")
                s.close()
            except:
                pass
        
        navigation_process = None
        vnc_process = None
        websockify_process = None
        
        print("=== 启动新的VNC服务器 ===")
        vnc_result = subprocess.run(
            ['vncserver', VNC_DISPLAY, '-geometry', '1920x1080', '-depth', '24',
             '-xstartup', '/usr/bin/xterm', '-localhost', 'no'],
            capture_output=True, text=True, timeout=15
        )
        if vnc_result.returncode != 0:
            error_msg = f'VNC启动失败: {vnc_result.stderr}'
            print(error_msg)
            return jsonify({'success': False, 'message': error_msg}), 500
        
        print(f"VNC服务器已启动: {VNC_DISPLAY} (端口 {VNC_PORT})")
        time.sleep(2)
        
        websockify_process = subprocess.Popen(
            ['websockify', '--web', NOVNC_PATH, str(WEBSOCKIFY_PORT), f'localhost:{VNC_PORT}'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        time.sleep(1.5)
        
        if websockify_process.poll() is not None:
            _, ws_err = websockify_process.communicate()
            error_msg = f'websockify启动失败: {ws_err.decode()}'
            print(error_msg)
            return jsonify({'success': False, 'message': error_msg}), 500
        
        print(f"websockify已启动: 端口 {WEBSOCKIFY_PORT}")
        
        env = os.environ.copy()
        env['DISPLAY'] = VNC_DISPLAY
        g1nav_dir = os.path.expanduser('~/tang/WK/G1Nav2D')
        gridmap_launch_file = f"{g1nav_dir}/src/fastlio2/launch/gridmap_load.launch"
        env['ROS_PACKAGE_PATH'] = f"{g1nav_dir}/devel:{env.get('ROS_PACKAGE_PATH', '')}"

        print("=== 启动导航 roslaunch ===")
        map_yaml_path = f"/home/unitree/tang/map/{selected_map}.yaml"
        print(f"使用地图: {map_yaml_path}")

        try:
            with open(gridmap_launch_file, 'r') as f:
                launch_content = f.read()

            import re
            new_launch_content = re.sub(
                r'(<arg name="2dmap_file" default=")[^"]*(" />)',
                rf'\g<1>{map_yaml_path}\g<2>',
                launch_content
            )

            if new_launch_content != launch_content:
                with open(gridmap_launch_file, 'w') as f:
                    f.write(new_launch_content)
                print(f"✅ 已更新 gridmap_load.launch 中的地图路径为: {map_yaml_path}")
            else:
                print(f"⚠️  地图路径已经是: {map_yaml_path}")
        except Exception as e:
            print(f"⚠️  修改 launch 文件失败: {e}")
            return jsonify({'success': False, 'message': f'修改地图配置失败：{str(e)}'}), 500

        # 🎯 根据 selected_map 更新 navigation.launch 中的 PCD 路径
        try:
            nav_launch_file = f"{g1nav_dir}/src/fastlio2/launch/navigation.launch"
            with open(nav_launch_file, 'r') as f:
                nav_content = f.read()

            orig_content = nav_content

            # 1. slam_reloc 的 pcd_path：{map}.pcd → 回退 map.pcd
            specific_pcd = os.path.join(PCD_DIR, f'{selected_map}.pcd')
            reloc_pcd = specific_pcd if os.path.exists(specific_pcd) else os.path.join(PCD_DIR, 'map.pcd')
            nav_content = re.sub(
                r'(<param name="pcd_path" value=")[^"]*(" />)',
                rf'\g<1>{reloc_pcd}\g<2>',
                nav_content
            )
            print(f"📦 重定位 PCD: {os.path.basename(reloc_pcd)}")

            # 2. downsample_pointcloud 的 pcd_file：{map}_ground.pcd → 回退 ground_map.pcd
            specific_ground = os.path.join(PCD_DIR, f'{selected_map}_ground.pcd')
            ground_pcd = specific_ground if os.path.exists(specific_ground) else os.path.join(PCD_DIR, 'ground_map.pcd')
            nav_content = re.sub(
                r'(<arg name="pcd_file" value=")[^"]*("/>)',
                rf'\g<1>{ground_pcd}\g<2>',
                nav_content
            )
            print(f"📦 地面滤波 PCD (/filtered_cloud): {os.path.basename(ground_pcd)}")

            if nav_content != orig_content:
                with open(nav_launch_file, 'w') as f:
                    f.write(nav_content)
                print(f"✅ 已更新 navigation.launch 中的 PCD 路径")
        except Exception as e:
            print(f"⚠️  修改 navigation.launch 失败（使用默认路径）: {e}")

        navigation_process = subprocess.Popen(
            ['bash', '-c', f'source {g1nav_dir}/devel/setup.bash && roslaunch fastlio navigation.launch'],
            cwd=g1nav_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print("正在启动导航（包含RViz），等待12秒...")
        time.sleep(12)
        
        result = navigation_process.poll()
        if result is not None:
            stdout, stderr = navigation_process.communicate()
            error_msg = f"导航启动失败，返回码: {result}\nSTDERR: {stderr.decode()}"
            print(error_msg)
            _stop_vnc()
            return jsonify({'success': False, 'message': error_msg}), 500
        
        navigation_running = True
        rviz_streaming = True
        
        socketio.emit('navigation_status', {
            'status': 'started',
            'message': '导航功能已启动'
        })
        socketio.emit('rviz_status', {
            'status': 'started',
            'message': 'RViz画面已启动（可交互）'
        })
        
        return jsonify({'success': True, 'message': '导航功能启动成功，RViz画面已就绪（可交互）'})
        
    except Exception as e:
        _stop_vnc()
        return jsonify({'success': False, 'message': f'启动导航失败：{str(e)}'}), 500

def _stop_vnc():
    """停止VNC和websockify"""
    global vnc_process, websockify_process
    try:
        subprocess.run(['vncserver', '-kill', VNC_DISPLAY], capture_output=True, timeout=5)
    except:
        pass
    subprocess.run(['pkill', '-9', '-f', 'websockify'], capture_output=True)
    if websockify_process:
        try:
            websockify_process.kill()
            websockify_process.wait(timeout=3)
        except:
            pass
        websockify_process = None
    vnc_process = None
    time.sleep(1)

@app.route('/api/stop_navigation', methods=['POST'])
def stop_navigation():
    """停止导航功能"""
    global navigation_running, navigation_process, rviz_streaming
    
    if not navigation_running:
        return jsonify({'success': False, 'message': '导航未运行'}), 400
    
    try:
        subprocess.run(['pkill', '-9', '-f', 'navigation.launch'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'move_base'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rviz'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'roslaunch'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'roscore'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rosout'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rosmaster'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'tf2_ros.*buffer_server'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'robot_state_publisher'], capture_output=True)
        
        if navigation_process:
            try:
                navigation_process.kill()
                navigation_process.wait(timeout=5)
            except:
                pass
            navigation_process = None
        
        _stop_vnc()
        
        time.sleep(2)
        
        navigation_running = False
        rviz_streaming = False
        
        socketio.emit('navigation_status', {
            'status': 'stopped',
            'message': '导航功能已停止'
        })
        socketio.emit('rviz_status', {
            'status': 'stopped',
            'message': 'RViz画面已停止'
        })
        
        return jsonify({'success': True, 'message': '导航功能已停止'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止导航失败：{str(e)}'}), 500

@app.route('/api/start_mapping', methods=['POST'])
def start_mapping():
    """启动建图功能（包含RViz画面 - VNC交互式）"""
    global mapping_running, mapping_process, rviz_streaming, vnc_process, websockify_process

    if mapping_running:
        return jsonify({'success': False, 'message': '建图已经在运行中'}), 400

    if navigation_running:
        return jsonify({'success': False, 'message': '请先停止导航功能再启动建图'}), 400

    try:
        print("=== 开始清理残留进程 ===")

        subprocess.run(['pkill', '-9', '-f', 'mapping.launch'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'navigation.launch'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'move_base'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rviz'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'roslaunch'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rosmaster'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'roscore'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rosout'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'tf2_ros.*buffer_server'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'robot_state_publisher'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'websockify'], capture_output=True)

        time.sleep(2)

        g1nav_dir = os.path.expanduser('~/tang/WK/G1Nav2D')
        env = os.environ.copy()
        env['ROS_PACKAGE_PATH'] = f"{g1nav_dir}/devel:{env.get('ROS_PACKAGE_PATH', '')}"

        kill_vnc = subprocess.run(
            ['vncserver', '-kill', VNC_DISPLAY],
            capture_output=True, text=True, timeout=5
        )
        print(f"VNC kill输出: {kill_vnc.stdout} {kill_vnc.stderr}")

        time.sleep(1)

        rosparam_del = subprocess.run(
            ['bash', '-c', f'source {g1nav_dir}/devel/setup.bash && rosparam delete / 2>/dev/null; true'],
            env=env, capture_output=True, timeout=5
        )
        time.sleep(2)

        for port in [11311, 6080]:
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                result = s.connect_ex(('localhost', port))
                if result == 0:
                    print(f"端口 {port} 仍被占用")
                else:
                    print(f"端口 {port} 已释放")
                s.close()
            except:
                pass

        mapping_process = None
        vnc_process = None
        websockify_process = None

        print("=== 启动新的VNC服务器 ===")
        vnc_result = subprocess.run(
            ['vncserver', VNC_DISPLAY, '-geometry', '1920x1080', '-depth', '24',
             '-xstartup', '/usr/bin/xterm', '-localhost', 'no'],
            capture_output=True, text=True, timeout=15
        )
        if vnc_result.returncode != 0:
            error_msg = f'VNC启动失败: {vnc_result.stderr}'
            print(error_msg)
            return jsonify({'success': False, 'message': error_msg}), 500

        print(f"VNC服务器已启动: {VNC_DISPLAY} (端口 {VNC_PORT})")
        time.sleep(2)

        websockify_process = subprocess.Popen(
            ['websockify', '--web', NOVNC_PATH, str(WEBSOCKIFY_PORT), f'localhost:{VNC_PORT}'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        time.sleep(1.5)

        if websockify_process.poll() is not None:
            _, ws_err = websockify_process.communicate()
            error_msg = f'websockify启动失败: {ws_err.decode()}'
            print(error_msg)
            return jsonify({'success': False, 'message': error_msg}), 500

        print(f"websockify已启动: 端口 {WEBSOCKIFY_PORT}")

        env = os.environ.copy()
        env['DISPLAY'] = VNC_DISPLAY
        g1nav_dir = os.path.expanduser('~/tang/WK/G1Nav2D')
        env['ROS_PACKAGE_PATH'] = f"{g1nav_dir}/devel:{env.get('ROS_PACKAGE_PATH', '')}"

        print("=== 启动建图 roslaunch ===")
        mapping_process = subprocess.Popen(
            ['bash', '-c', f'source {g1nav_dir}/devel/setup.bash && roslaunch fastlio mapping.launch'],
            cwd=g1nav_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        print("正在启动建图（包含RViz），等待12秒...")
        time.sleep(12)

        result = mapping_process.poll()
        if result is not None:
            stdout, stderr = mapping_process.communicate()
            error_msg = f"建图启动失败，返回码: {result}\nSTDERR: {stderr.decode()}"
            print(error_msg)
            _stop_vnc()
            return jsonify({'success': False, 'message': error_msg}), 500

        mapping_running = True
        rviz_streaming = True

        socketio.emit('mapping_status', {
            'status': 'started',
            'message': '建图功能已启动'
        })
        socketio.emit('rviz_status', {
            'status': 'started',
            'message': 'RViz画面已启动（可交互）'
        })

        return jsonify({'success': True, 'message': '建图功能启动成功，RViz画面已就绪（可交互）'})

    except Exception as e:
        _stop_vnc()
        return jsonify({'success': False, 'message': f'启动建图失败：{str(e)}'}), 500

@app.route('/api/stop_mapping', methods=['POST'])
def stop_mapping():
    """停止建图功能"""
    global mapping_running, mapping_process, rviz_streaming

    if not mapping_running:
        return jsonify({'success': False, 'message': '建图未运行'}), 400

    try:
        subprocess.run(['pkill', '-9', '-f', 'mapping.launch'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'navigation.launch'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'move_base'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rviz'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'roslaunch'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'roscore'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rosout'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'rosmaster'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'tf2_ros.*buffer_server'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'robot_state_publisher'], capture_output=True)

        if mapping_process:
            try:
                mapping_process.kill()
                mapping_process.wait(timeout=5)
            except:
                pass
            mapping_process = None

        _stop_vnc()

        time.sleep(2)

        mapping_running = False
        rviz_streaming = False

        socketio.emit('mapping_status', {
            'status': 'stopped',
            'message': '建图功能已停止'
        })
        socketio.emit('rviz_status', {
            'status': 'stopped',
            'message': 'RViz画面已停止'
        })

        return jsonify({'success': True, 'message': '建图功能已停止'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'停止建图失败：{str(e)}'}), 500

@app.route('/api/save_map', methods=['POST'])
def save_map():
    """保存地图（支持自定义名称，自动修正 yaml 中的 nan 为 0，同时保存 3D PCD 点云地图）"""
    if not mapping_running:
        return jsonify({'success': False, 'message': '建图未运行，无法保存地图'}), 400

    try:
        data = request.get_json() or {}
        map_name = data.get('map_name', 'mymap').strip()

        if not map_name:
            return jsonify({'success': False, 'message': '地图名称不能为空'}), 400

        if not map_name.replace('_', '').replace('-', '').isalnum():
            return jsonify({'success': False, 'message': '地图名称只能包含字母、数字、下划线和连字符'}), 400

        g1nav_dir = os.path.expanduser('~/tang/WK/G1Nav2D')
        map_dir = '/home/unitree/tang/map'
        map_path = f"{map_dir}/{map_name}"
        pcd_dir = PCD_DIR
        pcd_path = f"{pcd_dir}/{map_name}.pcd"
        pcd_ground_path = f"{pcd_dir}/{map_name}_ground.pcd"
        pcd_default_path = f"{pcd_dir}/map.pcd"
        pcd_ground_default_path = f"{pcd_dir}/ground_map.pcd"

        env = os.environ.copy()
        env['ROS_PACKAGE_PATH'] = f"{g1nav_dir}/devel:{env.get('ROS_PACKAGE_PATH', '')}"

        print(f"=== 保存地图: {map_path} ===")

        # 步骤 1: 保存 2D 栅格地图（pgm + yaml）
        save_2d_process = subprocess.Popen(
            ['bash', '-c', f'source {g1nav_dir}/devel/setup.bash && rosrun map_server map_saver map:=/projected_map -f {map_path}'],
            cwd=g1nav_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = save_2d_process.communicate(timeout=30)

        pcd_save_success = False
        pcd_ground_save_success = False
        pcd_save_message = ""

        if save_2d_process.returncode == 0:
            yaml_file = f"{map_path}.yaml"

            if os.path.exists(yaml_file):
                try:
                    with open(yaml_file, 'r') as f:
                        content = f.read()

                    import re
                    content_modified = re.sub(r'\bnan\b', '0.000000', content)

                    if content_modified != content:
                        with open(yaml_file, 'w') as f:
                            f.write(content_modified)
                        print(f"✅ 已修正 {yaml_file} 中的 nan 为 0")
                except Exception as e:
                    print(f"⚠️  修正 yaml 文件失败: {e}")

            # 步骤 2: 保存 3D PCD 点云地图（用于重定位）
            # 注意：使用 resolution=1.0 作为标志位，通知 C++ 同时保存 ground_map
            # 必须用 YAML flow mapping 语法 {key: val, key: val}，否则 rosservice 解析为单 arg 时会 YAML 报错
            print(f"=== 保存 PCD 点云地图: {pcd_path} ===")
            try:
                pcd_save_process = subprocess.Popen(
                    ['bash', '-c', f'source {g1nav_dir}/devel/setup.bash && rosservice call /save_map "{{save_path: \'{pcd_path}\', resolution: 1.0}}"'],
                    cwd=g1nav_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                pcd_stdout, pcd_stderr = pcd_save_process.communicate(timeout=30)

                if pcd_save_process.returncode == 0:
                    if os.path.exists(pcd_path) and os.path.getsize(pcd_path) > 10240:
                        file_size_mb = os.path.getsize(pcd_path) / (1024 * 1024)
                        print(f"✅ PCD 地图已保存: {pcd_path} ({file_size_mb:.2f} MB)")
                        pcd_save_success = True
                    else:
                        pcd_save_message = "PCD 文件未生成或过小"
                        print(f"⚠️ {pcd_save_message}")
                else:
                    err_text = pcd_stderr.decode(errors='replace')
                    out_text = pcd_stdout.decode(errors='replace')
                    print(f"❌ PCD 保存 returncode={pcd_save_process.returncode}")
                    print(f"   STDOUT: {out_text[:500]}")
                    print(f"   STDERR: {err_text[:1500]}")
                    pcd_save_message = f"PCD 保存失败 (rc={pcd_save_process.returncode}): {err_text[:200]}"
                    print(f"⚠️ {pcd_save_message}")

                # 检查 ground_map 是否也已保存
                if os.path.exists(pcd_ground_path) and os.path.getsize(pcd_ground_path) > 1024:
                    ground_size_mb = os.path.getsize(pcd_ground_path) / (1024 * 1024)
                    print(f"✅ Ground PCD 已保存: {pcd_ground_path} ({ground_size_mb:.2f} MB)")
                    pcd_ground_save_success = True
                else:
                    print(f"ℹ️ Ground PCD 未生成（可能没有地面点云数据）")
            except subprocess.TimeoutExpired:
                pcd_save_message = "PCD 保存超时"
                print(f"⚠️ {pcd_save_message}")
            except Exception as e:
                pcd_save_message = f"PCD 保存异常: {str(e)}"
                print(f"⚠️ {pcd_save_message}")

            # 步骤 3: 同时更新默认 map.pcd / ground_map.pcd（保持向后兼容）
            try:
                if os.path.exists(pcd_path) and pcd_path != pcd_default_path:
                    import shutil
                    shutil.copy2(pcd_path, pcd_default_path)
                    print(f"✅ 已同步更新默认 PCD: {pcd_default_path}")
            except Exception as e:
                print(f"⚠️ 同步默认 PCD 失败: {e}")

            try:
                if os.path.exists(pcd_ground_path) and pcd_ground_path != pcd_ground_default_path:
                    import shutil
                    shutil.copy2(pcd_ground_path, pcd_ground_default_path)
                    print(f"✅ 已同步更新默认 Ground PCD: {pcd_ground_default_path}")
            except Exception as e:
                print(f"⚠️ 同步默认 Ground PCD 失败: {e}")

            # 组合返回消息
            pcd_save_message = ""
            if pcd_save_success:
                pcd_save_message = f"PCD 已保存 ({os.path.getsize(pcd_path) / (1024 * 1024):.2f} MB)"
                if pcd_ground_save_success:
                    pcd_save_message += f" | Ground PCD 已保存 ({os.path.getsize(pcd_ground_path) / (1024 * 1024):.2f} MB)"

            socketio.emit('map_saved', {
                'status': 'success',
                'message': f'地图保存成功：{map_path}',
                'map_name': map_name,
                'pcd_saved': pcd_save_success,
                'pcd_ground_saved': pcd_ground_save_success,
                'pcd_message': pcd_save_message
            })
            return jsonify({
                'success': True,
                'message': f'地图保存成功：{map_path}' + (f' | {pcd_save_message}' if pcd_save_message else ''),
                'map_name': map_name,
                'pcd_saved': pcd_save_success,
                'pcd_ground_saved': pcd_ground_save_success,
                'pcd_path': pcd_path,
                'pcd_ground_path': pcd_ground_path
            })
        else:
            error_msg = f"地图保存失败: {stderr.decode()}"
            print(error_msg)
            return jsonify({'success': False, 'message': error_msg}), 500

    except Exception as e:
        return jsonify({'success': False, 'message': f'保存地图失败：{str(e)}'}), 500

@app.route('/api/get_maps', methods=['GET'])
def get_maps():
    """获取可用地图列表"""
    try:
        map_dir = '/home/unitree/tang/map'

        if not os.path.exists(map_dir):
            return jsonify({
                'success': True,
                'maps': [],
                'message': '地图目录不存在'
            })

        maps = []
        for file in os.listdir(map_dir):
            if file.endswith('.yaml') and not file.endswith('.yaml.old'):
                map_name = file[:-5]
                pgm_file = f"{map_name}.pgm"
                if os.path.exists(os.path.join(map_dir, pgm_file)):
                    file_stat = os.stat(os.path.join(map_dir, file))
                    maps.append({
                        'name': map_name,
                        'path': f"{map_dir}/{map_name}",
                        'modified_time': file_stat.st_mtime
                    })

        maps.sort(key=lambda x: x['modified_time'], reverse=True)

        return jsonify({
            'success': True,
            'maps': maps,
            'selected_map': selected_map
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取地图列表失败：{str(e)}'}), 500

@app.route('/api/select_map', methods=['POST'])
def select_map():
    """选择用于导航的地图"""
    global selected_map

    try:
        data = request.get_json() or {}
        map_name = data.get('map_name', '').strip()

        if not map_name:
            return jsonify({'success': False, 'message': '请选择一个地图'}), 400

        map_dir = '/home/unitree/tang/map'
        yaml_file = f"{map_dir}/{map_name}.yaml"
        pgm_file = f"{map_dir}/{map_name}.pgm"

        if not os.path.exists(yaml_file) or not os.path.exists(pgm_file):
            return jsonify({'success': False, 'message': f'地图文件不存在: {map_name}'}), 400

        selected_map = map_name

        socketio.emit('map_selected', {
            'status': 'success',
            'message': f'已选择地图: {map_name}',
            'map_name': map_name
        })

        return jsonify({
            'success': True,
            'message': f'已选择地图: {map_name}',
            'map_name': map_name
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'选择地图失败：{str(e)}'}), 500

@app.route('/api/toggle_loco', methods=['POST'])
def toggle_loco():
    """切换运动控制状态"""
    global loco_running, loco_process
    
    if loco_running:
        # 停止运动控制
        try:
            # 先使用pkill强制杀死所有相关进程
            subprocess.run(['pkill', '-9', '-f', 'g1_control_mpc'], capture_output=True)
            subprocess.run(['pkill', '-9', '-f', 'python3.9.*g1_control'], capture_output=True)
            
            # 清理进程对象（不等待，因为进程已经被杀死）
            if loco_process:
                try:
                    loco_process.kill()
                except:
                    pass
                loco_process = None
            
            # 等待一下确保进程完全终止
            time.sleep(1)
            
            loco_running = False
            socketio.emit('loco_status', {
                'status': 'stopped',
                'message': '运动控制已停止'
            })
            return jsonify({'success': True, 'message': '运动控制已停止'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'停止运动控制失败：{str(e)}'}), 500
    else:
        # 启动运动控制
        try:
            # 启动前先清理残留进程
            subprocess.run(['pkill', '-9', '-f', 'g1_control_mpc'], capture_output=True)
            subprocess.run(['pkill', '-9', '-f', 'python3.9.*g1_control'], capture_output=True)
            time.sleep(0.5)
            
            # 设置环境变量
            env = os.environ.copy()
            env['PYTHONPATH'] = f"{os.path.expanduser('~/tang/WK/unitree_sdk2_python')}:{env.get('PYTHONPATH', '')}"
            env['PYTHONUNBUFFERED'] = '1'  # 关键：禁止Python缓冲stdout，防止管道满导致进程阻塞
            
            # 获取网络接口（从请求参数或默认值）
            # 处理空body或非JSON请求
            try:
                data = request.get_json() or {}
            except:
                data = {}
            network_interface = data.get('network_interface', 'eth0')
            
            # 启动运动控制节点（使用 -u 参数强制无缓冲输出）
            loco_process = subprocess.Popen(
                ['python3.9', '-u', '/home/unitree/tang/WK/unitree_sdk2_python/example/g1/high_level/g1_control_mpc_stable_fast.py', network_interface],
                cwd=os.path.expanduser('~/tang/WK/unitree_sdk2_python/example/g1/high_level'),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # 清空日志缓冲区
            global loco_log_buffer
            loco_log_buffer = []
            
            # 关键：必须先设置 loco_running = True，再启动日志读取线程
            # 否则线程的 while loco_running 条件为 False，线程会立即退出
            # 导致无人读取管道，缓冲区满后进程阻塞，运动控制失效
            loco_running = True
            
            # 创建日志读取线程
            def read_loco_logs():
                global loco_log_buffer, loco_running
                try:
                    while loco_running and loco_process.poll() is None:
                        line = loco_process.stdout.readline()
                        if line:
                            loco_log_buffer.append(line.strip())
                            if len(loco_log_buffer) > 100:
                                loco_log_buffer.pop(0)
                            
                            socketio.emit('loco_log', {
                                'line': line.strip(),
                                'full_log': loco_log_buffer.copy()
                            })
                        else:
                            time.sleep(0.01)
                except Exception as e:
                    print(f"日志读取线程异常: {e}")
            
            loco_log_thread = threading.Thread(target=read_loco_logs, daemon=True)
            loco_log_thread.start()
            
            print("正在启动运动控制...")
            time.sleep(3)
            
            # 检查是否正常启动
            result = loco_process.poll()
            if result is not None:
                loco_running = False
                log_content = "\n".join(loco_log_buffer) if loco_log_buffer else "无日志"
                error_msg = f"运动控制启动失败，返回码: {result}\n日志: {log_content}"
                print(error_msg)
                return jsonify({'success': False, 'message': error_msg}), 500
            
            socketio.emit('loco_status', {
                'status': 'started',
                'message': '运动控制已启动'
            })
            return jsonify({'success': True, 'message': '运动控制启动成功', 'logs': loco_log_buffer.copy()})
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'启动运动控制失败：{str(e)}'}), 500

def check_and_kill_xiaoye_processes():
    """检查并杀死所有相关进程"""
    global xiaoye_process
    
    # 先杀死可能存在的相关进程
    subprocess.run(['pkill', '-f', 'main.py.*xiaozhi'], capture_output=True)
    subprocess.run(['pkill', '-f', 'py-xiaozhi'], capture_output=True)
    subprocess.run(['pkill', '-f', 'python3.9.*main.py'], capture_output=True)
    
    # 清理进程对象
    if xiaoye_process:
        try:
            xiaoye_process.kill()
        except:
            pass
        xiaoye_process = None


@app.route('/api/start_xiaoye', methods=['POST'])
def start_xiaoye():
    """启动小野AI"""
    global xiaoye_running, xiaoye_process
    
    if xiaoye_running:
        return jsonify({'success': False, 'message': '小野AI已经在运行中'}), 400
    
    try:
        # 启动前先清理可能存在的残留进程
        check_and_kill_xiaoye_processes()
        
        project_dir = '/home/unitree/tang/WK/PythonProject/py-xiaozhi-main'
        log_dir = os.path.join(project_dir, 'logs')
        log_file = os.path.join(log_dir, 'startup.log')
        
        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置环境变量（参考start_g1.sh）
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{project_dir}:{env.get('PYTHONPATH', '')}"
        env['DISPLAY'] = ':0'
        env['XDG_RUNTIME_DIR'] = '/run/user/1000'
        
        # 记录启动日志
        with open(log_file, 'a') as f:
            f.write("========================================\n")
            f.write(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"工作目录: {project_dir}\n")
            f.write(f"Python路径: /usr/bin/python3.9\n")
            f.write("========================================\n")
        
        # 使用绝对路径启动（参考start_g1.sh），输出重定向到日志文件
        log_fd = open(log_file, 'a')
        xiaoye_process = subprocess.Popen(
            ['/usr/bin/python3.9', '/home/unitree/tang/WK/PythonProject/py-xiaozhi-main/main.py', '--mode', 'cli', '--protocol', 'websocket'],
            cwd=project_dir,
            env=env,
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid  # 创建新进程组，便于后续杀死
        )
        
        print("正在启动小野AI...")
        time.sleep(5)  # 等待启动
        
        # 检查是否正常启动
        result = xiaoye_process.poll()
        if result is not None:
            # 读取日志文件获取详细错误信息
            error_msg = f"小野AI启动失败，返回码: {result}\n"
            try:
                with open(log_file, 'r') as f:
                    log_content = f.read()
                    # 获取最后10行日志
                    lines = log_content.split('\n')[-10:]
                    error_msg += "最近日志:\n" + '\n'.join(lines)
            except:
                error_msg += "无法读取日志文件"
            
            print(error_msg)
            # 重置状态
            xiaoye_process = None
            return jsonify({'success': False, 'message': error_msg}), 500
        
        xiaoye_running = True
        socketio.emit('xiaoye_status', {
            'status': 'started',
            'message': '小野AI已启动，可使用唤醒词唤醒'
        })
        return jsonify({'success': True, 'message': '小野AI启动成功，可使用唤醒词唤醒'})
        
    except Exception as e:
        # 发生异常时确保状态正确
        xiaoye_running = False
        xiaoye_process = None
        return jsonify({'success': False, 'message': f'启动小野AI失败：{str(e)}'}), 500


@app.route('/api/stop_xiaoye', methods=['POST'])
def stop_xiaoye():
    """停止小野AI"""
    global xiaoye_running, xiaoye_process
    
    if not xiaoye_running:
        return jsonify({'success': False, 'message': '小野AI未运行'}), 400
    
    try:
        # 强力杀死所有相关进程
        # 使用 -9 参数强制杀死（SIGKILL）
        subprocess.run(['pkill', '-9', '-f', 'main.py'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'py-xiaozhi'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'python3.9.*main'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'python3.*xiaozhi'], capture_output=True)
        
        # 尝试杀死进程组（因为启动时使用了preexec_fn=os.setsid）
        if xiaoye_process:
            try:
                os.killpg(os.getpgid(xiaoye_process.pid), subprocess.signal.SIGKILL)
            except:
                try:
                    os.kill(xiaoye_process.pid, subprocess.signal.SIGKILL)
                except:
                    pass
            xiaoye_process = None
        
        # 等待一下确保进程完全终止
        time.sleep(1)
        
        xiaoye_running = False
        socketio.emit('xiaoye_status', {
            'status': 'stopped',
            'message': '小野AI已停止'
        })
        return jsonify({'success': True, 'message': '小野AI已停止'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止小野AI失败：{str(e)}'}), 500


# ============================================================
#  人脸识别模块 (g1_face_greet.py 子进程)
# ============================================================

def _check_and_kill_face_greet_processes():
    """清理可能残留的人脸识别进程"""
    global face_greet_process
    subprocess.run(['pkill', '-9', '-f', 'g1_face_greet.py'], capture_output=True)
    if face_greet_process:
        try:
            os.killpg(os.getpgid(face_greet_process.pid), subprocess.signal.SIGKILL)
        except Exception:
            try:
                os.kill(face_greet_process.pid, subprocess.signal.SIGKILL)
            except Exception:
                pass
        face_greet_process = None


@app.route('/api/start_face_greet', methods=['POST'])
def start_face_greet():
    """启动人脸识别模块 (拍照→百度识别→挥手+语音)"""
    global face_greet_running, face_greet_process, face_greet_log_thread, face_greet_log_buffer

    if face_greet_running:
        return jsonify({'success': False, 'message': '人脸识别模块已在运行中'}), 400

    # 手势识别与人脸识别共用 RealSense 相机, 不可同时运行
    if gesture_control_running:
        return jsonify({'success': False, 'message': '手势识别正在运行, 请先停止 (相机占用冲突)'}), 400

    try:
        _check_and_kill_face_greet_processes()
        time.sleep(0.3)

        try:
            data = request.get_json() or {}
        except Exception:
            data = {}
        network_interface = data.get('network_interface', 'eth0')

        env = os.environ.copy()
        env['PYTHONPATH'] = f"{os.path.expanduser('~/tang/WK/unitree_sdk2_python')}:{env.get('PYTHONPATH', '')}"
        env['PYTHONUNBUFFERED'] = '1'

        face_greet_process = subprocess.Popen(
            ['python3.8', '-u', FACE_GREET_SCRIPT, network_interface],
            cwd=os.path.dirname(FACE_GREET_SCRIPT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,
        )

        face_greet_log_buffer = []
        face_greet_running = True

        def read_face_greet_logs():
            global face_greet_log_buffer, face_greet_running
            try:
                while face_greet_running and face_greet_process is not None and face_greet_process.poll() is None:
                    line = face_greet_process.stdout.readline()
                    if line:
                        line = line.rstrip('\n')
                        face_greet_log_buffer.append(line)
                        if len(face_greet_log_buffer) > 200:
                            face_greet_log_buffer.pop(0)
                        socketio.emit('face_greet_log', {
                            'line': line,
                            'full_log': face_greet_log_buffer.copy()
                        })
                    else:
                        time.sleep(0.02)
            except Exception as e:
                print(f"[FaceGreet] 日志线程异常: {e}")
            finally:
                # 进程意外退出时同步状态
                if face_greet_running:
                    socketio.emit('face_greet_status', {
                        'status': 'stopped',
                        'message': '人脸识别进程已退出'
                    })

        face_greet_log_thread = threading.Thread(target=read_face_greet_logs, daemon=True)
        face_greet_log_thread.start()

        time.sleep(3)

        result = face_greet_process.poll()
        if result is not None:
            face_greet_running = False
            log_content = "\n".join(face_greet_log_buffer) if face_greet_log_buffer else "无日志"
            return jsonify({
                'success': False,
                'message': f'人脸识别启动失败 (返回码 {result})\n日志:\n{log_content}'
            }), 500

        socketio.emit('face_greet_status', {
            'status': 'started',
            'message': '人脸识别模块已启动'
        })
        return jsonify({
            'success': True,
            'message': '人脸识别模块已启动',
            'logs': face_greet_log_buffer.copy()
        })
    except Exception as e:
        face_greet_running = False
        face_greet_process = None
        return jsonify({'success': False, 'message': f'启动人脸识别失败：{str(e)}'}), 500


@app.route('/api/stop_face_greet', methods=['POST'])
def stop_face_greet():
    """停止人脸识别模块（等待相机资源释放）"""
    global face_greet_running, face_greet_process

    if not face_greet_running:
        return jsonify({'success': False, 'message': '人脸识别模块未运行'}), 400

    try:
        # ===== 等待进程退出（最多3秒） =====
        if face_greet_process is not None and face_greet_process.poll() is None:
            for _ in range(30):
                if face_greet_process.poll() is not None:
                    break
                time.sleep(0.1)

        # ===== 超时后强制杀死 =====
        if face_greet_process is not None and face_greet_process.poll() is None:
            _check_and_kill_face_greet_processes()

        # ===== 等待相机资源释放（关键！） =====
        time.sleep(2)

        face_greet_running = False
        face_greet_process = None

        socketio.emit('face_greet_status', {
            'status': 'stopped',
            'message': '人脸识别模块已停止，相机资源已释放'
        })
        return jsonify({
            'success': True,
            'message': '人脸识别已停止，相机资源已释放（可启动手势识别）'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止人脸识别失败：{str(e)}'}), 500


@app.route('/api/face_greet_status', methods=['GET'])
def face_greet_status():
    """查询人脸识别模块状态"""
    running = face_greet_running and face_greet_process is not None and face_greet_process.poll() is None
    return jsonify({
        'running': running,
        'logs': face_greet_log_buffer.copy() if face_greet_log_buffer else []
    })


# ============================================================
#  手势识别模块 (g1_gesture_control.py 子进程)
# ============================================================

def _check_and_kill_gesture_control_processes():
    """清理可能残留的手势识别进程"""
    global gesture_control_process
    subprocess.run(['pkill', '-9', '-f', 'g1_gesture_control.py'], capture_output=True)
    if gesture_control_process:
        try:
            os.killpg(os.getpgid(gesture_control_process.pid), subprocess.signal.SIGKILL)
        except Exception:
            try:
                os.kill(gesture_control_process.pid, subprocess.signal.SIGKILL)
            except Exception:
                pass
        gesture_control_process = None


@app.route('/api/start_gesture_control', methods=['POST'])
def start_gesture_control():
    """启动手势识别模块 (五模式: 控制跟随走近导航问候)"""
    global gesture_control_running, gesture_control_process
    global gesture_control_log_thread, gesture_control_log_buffer

    if gesture_control_running:
        return jsonify({'success': False, 'message': '手势识别模块已在运行中'}), 400

    # 与人脸识别共用 RealSense, 不可同时运行
    if face_greet_running:
        return jsonify({'success': False, 'message': '人脸识别正在运行, 请先停止 (相机占用冲突)'}), 400

    try:
        _check_and_kill_gesture_control_processes()
        time.sleep(0.3)

        try:
            data = request.get_json() or {}
        except Exception:
            data = {}
        network_interface = data.get('network_interface', 'eth0')

        env = os.environ.copy()
        env['PYTHONPATH'] = f"{os.path.expanduser('~/tang/WK/unitree_sdk2_python')}:{env.get('PYTHONPATH', '')}"
        env['PYTHONUNBUFFERED'] = '1'

        gesture_control_process = subprocess.Popen(
            ['python3.8', '-u', GESTURE_CONTROL_SCRIPT, network_interface],
            cwd=os.path.dirname(GESTURE_CONTROL_SCRIPT),
            env=env,
            stdin=subprocess.PIPE,   # 用于向子进程发送按键
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,
        )

        gesture_control_log_buffer = []
        gesture_control_running = True

        def read_gesture_control_logs():
            global gesture_control_log_buffer, gesture_control_running
            try:
                while (gesture_control_running and gesture_control_process is not None
                       and gesture_control_process.poll() is None):
                    line = gesture_control_process.stdout.readline()
                    if line:
                        line = line.rstrip('\n')
                        gesture_control_log_buffer.append(line)
                        if len(gesture_control_log_buffer) > 200:
                            gesture_control_log_buffer.pop(0)
                        socketio.emit('gesture_control_log', {
                            'line': line,
                            'full_log': gesture_control_log_buffer.copy()
                        })
                    else:
                        time.sleep(0.02)
            except Exception as e:
                print(f"[GestureControl] 日志线程异常: {e}")
            finally:
                if gesture_control_running:
                    # 子进程已退出（崩溃或被杀），复位运行标志，
                    # 否则 start_gesture_control 会一直误判"已在运行中"而无法重启。
                    gesture_control_running = False
                    socketio.emit('gesture_control_status', {
                        'status': 'stopped',
                        'message': '手势识别进程已退出'
                    })

        gesture_control_log_thread = threading.Thread(target=read_gesture_control_logs, daemon=True)
        gesture_control_log_thread.start()

        time.sleep(3)

        result = gesture_control_process.poll()
        if result is not None:
            gesture_control_running = False
            log_content = "\n".join(gesture_control_log_buffer) if gesture_control_log_buffer else "无日志"
            return jsonify({
                'success': False,
                'message': f'手势识别启动失败 (返回码 {result})\n日志:\n{log_content}'
            }), 500

        socketio.emit('gesture_control_status', {
            'status': 'started',
            'message': '手势识别模块已启动'
        })
        return jsonify({
            'success': True,
            'message': '手势识别模块已启动',
            'logs': gesture_control_log_buffer.copy()
        })
    except Exception as e:
        gesture_control_running = False
        gesture_control_process = None
        return jsonify({'success': False, 'message': f'启动手势识别失败：{str(e)}'}), 500


@app.route('/api/stop_gesture_control', methods=['POST'])
def stop_gesture_control():
    """停止手势识别模块（等待相机资源释放）"""
    global gesture_control_running, gesture_control_process

    if not gesture_control_running:
        return jsonify({'success': False, 'message': '手势识别模块未运行'}), 400

    try:
        # ===== 先尝试优雅退出：发送 Q 按键 =====
        if gesture_control_process is not None and gesture_control_process.poll() is None:
            try:
                gesture_control_process.stdin.write('Q')
                gesture_control_process.stdin.flush()
                # 等待子进程自然退出（最多5秒，相机资源释放需要时间）
                for _ in range(50):
                    if gesture_control_process.poll() is not None:
                        break
                    time.sleep(0.1)
            except Exception:
                pass  # stdin 可能已关闭

        # ===== 超时后强制杀死 =====
        if gesture_control_process is not None and gesture_control_process.poll() is None:
            _check_and_kill_gesture_control_processes()
            time.sleep(1)  # 强杀后等待1秒确保相机释放

        gesture_control_running = False
        gesture_control_process = None

        socketio.emit('gesture_control_status', {
            'status': 'stopped',
            'message': '手势识别模块已停止，相机资源已释放'
        })
        return jsonify({
            'success': True,
            'message': '手势识别已停止，相机资源已释放（可启动人脸识别）'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止手势识别失败：{str(e)}'}), 500


@app.route('/api/gesture_control_status', methods=['GET'])
def gesture_control_status():
    """查询手势识别模块状态"""
    running = (gesture_control_running and gesture_control_process is not None
               and gesture_control_process.poll() is None)
    return jsonify({
        'running': running,
        'logs': gesture_control_log_buffer.copy() if gesture_control_log_buffer else []
    })


@app.route('/api/gesture_send_key', methods=['POST'])
def gesture_send_key():
    """向前台运行的手势识别子进程 stdin 发送一个按键 (R/1/2/3/4/5/Q)"""
    # 必须声明 global：下方 Q 分支会 gesture_control_running = False 赋值，
    # 若不声明，Python 会把该变量在本函数内当作 local，导致开头那行
    # `if not gesture_control_running` 在赋值前读取，抛 UnboundLocalError
    # （表现为 /api/gesture_send_key 不论发什么 key 都 500）。
    global gesture_control_running
    data = request.get_json() or {}
    key = (data.get('key') or '').strip()
    if not key:
        return jsonify({'success': False, 'message': '缺少 key 参数'}), 400

    # 白名单: 仅允许这些按键, 防止注入异常控制字符
    allowed = {'r', 'R', '1', '2', '3', '4', '5', 'q', 'Q'}
    if key not in allowed:
        return jsonify({'success': False, 'message': f'不支持的按键: {key}'}), 400

    if not gesture_control_running or gesture_control_process is None:
        return jsonify({'success': False, 'message': '手势识别未运行'}), 400
    if gesture_control_process.poll() is not None:
        return jsonify({'success': False, 'message': '手势识别进程已退出'}), 400

    # ===== 检查 stdin 是否可用 =====
    if gesture_control_process.stdin is None:
        return jsonify({'success': False, 'message': '进程 stdin 管道未打开'}), 400

    try:
        gesture_control_process.stdin.write(key)
        gesture_control_process.stdin.flush()

        # ===== Q 退出按键特殊处理：等待进程退出并清理相机资源 =====
        if key.upper() == 'Q':
            # 等待子进程自然退出（最多5秒）
            for _ in range(50):
                if gesture_control_process.poll() is not None:
                    break
                time.sleep(0.1)

            # 超时后强制杀死
            if gesture_control_process.poll() is None:
                _check_and_kill_gesture_control_processes()

            # 清理状态
            gesture_control_running = False
            socketio.emit('gesture_control_status', {
                'status': 'stopped',
                'message': '手势识别已退出，相机资源已释放'
            })
            return jsonify({
                'success': True,
                'message': '手势识别已退出，相机资源已释放（可启动人脸识别）',
                'key': key
            })

        return jsonify({'success': True, 'message': f'已发送按键: {key}', 'key': key})
    except BrokenPipeError:
        return jsonify({'success': False, 'message': '进程 stdin 已关闭（进程已退出）'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'发送按键失败: {str(e)}'}), 500


@app.route('/api/start_exhibition', methods=['POST'])
def start_exhibition():
    """启动一键展览（多站点导航）"""
    global exhibition_running, exhibition_process
    
    if exhibition_running:
        return jsonify({'success': False, 'message': '展览导航已经在运行中'}), 400
    
    try:
        # 启动前先清理残留进程
        subprocess.run(['pkill', '-9', '-f', 'multi_nav_hys'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'multi_waypoint_nav'], capture_output=True)
        time.sleep(0.5)
        
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{os.path.expanduser('~/tang/WK/unitree_sdk2_python')}:{env.get('PYTHONPATH', '')}"
        
        # 获取网络接口（从请求参数或默认值）
        try:
            data = request.get_json() or {}
        except:
            data = {}
        network_interface = data.get('network_interface', 'eth0')
        
        # 启动展览导航脚本
        exhibition_process = subprocess.Popen(
            ['python3.9', '/home/unitree/tang/WK/unitree_sdk2_python/example/g1/high_level/multi_nav_hys.py', network_interface],
            cwd=os.path.expanduser('~/tang/WK/unitree_sdk2_python/example/g1/high_level'),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print("正在启动一键展览...")
        time.sleep(3)  # 等待启动
        
        # 检查是否正常启动
        result = exhibition_process.poll()
        if result is not None:
            stdout, stderr = exhibition_process.communicate()
            error_msg = f"一键展览启动失败，返回码: {result}\nSTDERR: {stderr.decode()}"
            print(error_msg)
            exhibition_process = None
            return jsonify({'success': False, 'message': error_msg}), 500
        
        exhibition_running = True
        socketio.emit('exhibition_status', {
            'status': 'started',
            'message': '一键展览已启动，机器人正在前往第一个站点'
        })
        return jsonify({'success': True, 'message': '一键展览启动成功'})
        
    except Exception as e:
        exhibition_running = False
        exhibition_process = None
        return jsonify({'success': False, 'message': f'启动一键展览失败：{str(e)}'}), 500


@app.route('/api/stop_exhibition', methods=['POST'])
def stop_exhibition():
    """停止一键展览"""
    global exhibition_running, exhibition_process
    
    if not exhibition_running:
        return jsonify({'success': False, 'message': '展览导航未运行'}), 400
    
    try:
        # 强力杀死所有相关进程
        subprocess.run(['pkill', '-9', '-f', 'multi_nav_hys'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'multi_waypoint_nav'], capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'python3.9.*multi_nav'], capture_output=True)
        
        # 清理进程对象
        if exhibition_process:
            try:
                exhibition_process.kill()
            except:
                pass
            exhibition_process = None
        
        # 等待一下确保进程完全终止
        time.sleep(1)
        
        exhibition_running = False
        socketio.emit('exhibition_status', {
            'status': 'stopped',
            'message': '一键展览已停止'
        })
        return jsonify({'success': True, 'message': '一键展览已停止'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止一键展览失败：{str(e)}'}), 500


# ==================== 展览与巡逻路径管理 API ====================

@app.route('/api/exhibition/get_current_position', methods=['GET'])
def get_current_position():
    """获取机器人当前位置（通过ROS TF）"""
    try:
        if not navigation_running:
            return jsonify({'success': False, 'message': '请先启动导航功能'}), 400
        
        import re
        
        g1nav_dir = os.path.expanduser('~/tang/WK/G1Nav2D')
        env = os.environ.copy()
        env['ROS_MASTER_URI'] = 'http://localhost:11311'
        
        try:
            print("[EXHIBITION] 尝试从 TF 获取 map->base_link 变换...")
            
            tf_result = subprocess.run(
                ['bash', '-c',
                 f"source {g1nav_dir}/devel/setup.bash && "
                 "timeout 2 rosrun tf tf_echo map base_link 2>&1"],
                cwd=g1nav_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=4
            )
            
            if tf_result.stdout and 'Translation' in tf_result.stdout:
                tf_match = re.search(
                    r'Translation:\s*\[([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\]',
                    tf_result.stdout
                )
                rot_match = re.search(
                    r'Rotation.*?Quaternion\s*\[([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\]',
                    tf_result.stdout,
                    re.DOTALL
                )
                
                if tf_match:
                    x = float(tf_match.group(1))
                    y = float(tf_match.group(2))
                    
                    yaw = 0.0
                    if rot_match:
                        qx = float(rot_match.group(1))
                        qy = float(rot_match.group(2))
                        qz = float(rot_match.group(3))
                        qw = float(rot_match.group(4))
                        siny_cosp = 2 * (qw * qz + qx * qy)
                        cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
                        yaw = math.atan2(siny_cosp, cosy_cosp)
                    
                    print(f"[EXHIBITION] ✅ TF 成功: X={x:.3f}, Y={y:.3f}, Yaw={yaw:.4f}")
                    
                    return jsonify({
                        'success': True,
                        'position': {
                            'x': x,
                            'y': y,
                            'yaw': yaw
                        },
                        'message': f'当前位置: ({x}, {y}, 航向: {math.degrees(yaw):.1f}°)'
                    })
            
            return jsonify({'success': False, 'message': '无法从TF获取位置，请确保导航已启动且RViz可显示机器人'}), 500
            
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'message': '获取位置超时'}), 500
        except Exception as e:
            print(f"[EXHIBITION] 获取位置异常: {str(e)}")
            return jsonify({'success': False, 'message': f'获取位置异常: {str(e)}'}), 500
    except Exception as e:
        print(f"[EXHIBITION] 获取位置异常(外层): {str(e)}")
        return jsonify({'success': False, 'message': f'获取位置异常: {str(e)}'}), 500


@app.route('/api/exhibition/add_waypoint', methods=['POST'])
def add_waypoint():
    """添加一个路径点到当前编辑的路径（使用当前位置或手动输入）"""
    global current_editing_path
    
    try:
        data = request.get_json() or {}
        
        if data.get('use_current_position', False):
            if not navigation_running:
                return jsonify({'success': False, 'message': '请先启动导航功能以获取当前位置'}), 400
            
            import re as _re2
            g1nav_dir = os.path.expanduser('~/tang/WK/G1Nav2D')
            env = os.environ.copy()
            env['ROS_MASTER_URI'] = 'http://localhost:11311'
            
            tf_result = subprocess.run(
                ['bash', '-c',
                 f"source {g1nav_dir}/devel/setup.bash && "
                 "timeout 2 rosrun tf tf_echo map base_link 2>&1"],
                cwd=g1nav_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=4
            )
            
            if tf_result.stdout and 'Translation' in tf_result.stdout:
                tf_match = _re2.search(
                    r'Translation:\s*\[([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\]',
                    tf_result.stdout
                )
                rot_match = _re2.search(
                    r'Rotation.*?Quaternion\s*\[([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\]',
                    tf_result.stdout,
                    _re2.DOTALL
                )
                
                if tf_match:
                    x = float(tf_match.group(1))
                    y = float(tf_match.group(2))
                    
                    yaw = 0.0
                    if rot_match:
                        qx = float(rot_match.group(1))
                        qy = float(rot_match.group(2))
                        qz = float(rot_match.group(3))
                        qw = float(rot_match.group(4))
                        siny_cosp = 2 * (qw * qz + qx * qy)
                        cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
                        yaw = math.atan2(siny_cosp, cosy_cosp)
                else:
                    return jsonify({'success': False, 'message': '无法从TF解析位置数据'}), 500
            else:
                return jsonify({'success': False, 'message': '无法获取位置，请确保导航已启动且RViz可显示机器人'}), 500
        else:
            x = float(data.get('x', 0.0))
            y = float(data.get('y', 0.0))
            yaw = float(data.get('yaw', 0.0))
        
        action_id = int(data.get('action_id', 25))
        say_texts = data.get('say_texts', ['你好'])
        
        if not isinstance(say_texts, list):
            say_texts = [say_texts]
        
        waypoint = {
            'id': len(current_editing_path) + 1,
            'x': x,
            'y': y,
            'yaw': yaw,
            'action_id': action_id,
            'say_texts': say_texts
        }
        
        current_editing_path.append(waypoint)
        
        socketio.emit('waypoint_added', {
            'waypoint': waypoint,
            'total': len(current_editing_path),
            'message': f'已添加第 {len(current_editing_path)} 个路径点'
        })
        
        return jsonify({
            'success': True,
            'message': f'已添加第 {len(current_editing_path)} 个路径点: ({x}, {y})',
            'waypoint': waypoint,
            'total_waypoints': len(current_editing_path)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加路径点失败: {str(e)}'}), 500


@app.route('/api/exhibition/update_waypoint', methods=['POST'])
def update_waypoint():
    """更新指定路径点的信息"""
    global current_editing_path
    
    try:
        data = request.get_json() or {}
        waypoint_id = int(data.get('id', -1))
        
        if waypoint_id < 1 or waypoint_id > len(current_editing_path):
            return jsonify({'success': False, 'message': f'无效的路径点ID: {waypoint_id}'}), 400
        
        idx = waypoint_id - 1
        
        if 'x' in data:
            current_editing_path[idx]['x'] = float(data['x'])
        if 'y' in data:
            current_editing_path[idx]['y'] = float(data['y'])
        if 'yaw' in data:
            current_editing_path[idx]['yaw'] = float(data['yaw'])
        if 'action_id' in data:
            current_editing_path[idx]['action_id'] = int(data['action_id'])
        if 'say_texts' in data:
            say_texts = data['say_texts']
            if not isinstance(say_texts, list):
                say_texts = [say_texts]
            current_editing_path[idx]['say_texts'] = say_texts
        
        socketio.emit('waypoint_updated', {
            'waypoint': current_editing_path[idx],
            'message': f'已更新第 {waypoint_id} 个路径点'
        })
        
        return jsonify({
            'success': True,
            'message': f'已更新第 {waypoint_id} 个路径点',
            'waypoint': current_editing_path[idx]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新路径点失败: {str(e)}'}), 500


@app.route('/api/exhibition/delete_waypoint', methods=['POST'])
def delete_waypoint():
    """删除指定的路径点"""
    global current_editing_path
    
    try:
        data = request.get_json() or {}
        waypoint_id = int(data.get('id', -1))
        
        if waypoint_id < 1 or waypoint_id > len(current_editing_path):
            return jsonify({'success': False, 'message': f'无效的路径点ID: {waypoint_id}'}), 400
        
        idx = waypoint_id - 1
        removed = current_editing_path.pop(idx)
        
        for i, wp in enumerate(current_editing_path):
            wp['id'] = i + 1
        
        socketio.emit('waypoint_deleted', {
            'deleted_id': waypoint_id,
            'total': len(current_editing_path),
            'message': f'已删除第 {waypoint_id} 个路径点'
        })
        
        return jsonify({
            'success': True,
            'message': f'已删除第 {waypoint_id} 个路径点',
            'total_waypoints': len(current_editing_path)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除路径点失败: {str(e)}'}), 500


@app.route('/api/exhibition/get_current_path', methods=['GET'])
def get_current_path():
    """获取当前正在编辑的路径"""
    return jsonify({
        'success': True,
        'path': current_editing_path,
        'total': len(current_editing_path)
    })


@app.route('/api/exhibition/clear_current_path', methods=['POST'])
def clear_current_path():
    """清空当前编辑的路径"""
    global current_editing_path
    
    current_editing_path = []
    
    socketio.emit('path_cleared', {
        'message': '已清空当前编辑的路径'
    })
    
    return jsonify({
        'success': True,
        'message': '已清空当前编辑的路径'
    })


@app.route('/api/exhibition/save_path', methods=['POST'])
def save_exhibition_path():
    """保存当前编辑的路径到文件"""
    import re
    try:
        data = request.get_json() or {}
        path_name = data.get('name', '').strip()
        
        if not path_name:
            return jsonify({'success': False, 'message': '请输入路径名称'}), 400
        
        if not current_editing_path:
            return jsonify({'success': False, 'message': '当前路径为空，请先添加路径点'}), 400
        
        os.makedirs(EXHIBITION_PATH_DIR, exist_ok=True)
        
        safe_name = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', path_name)
        file_path = os.path.join(EXHIBITION_PATH_DIR, f'{safe_name}.json')
        
        path_data = {
            'name': path_name,
            'created_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'waypoints': current_editing_path,
            'total_waypoints': len(current_editing_path)
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(path_data, f, ensure_ascii=False, indent=2)
        
        socketio.emit('path_saved', {
            'name': path_name,
            'file': file_path,
            'total_waypoints': len(current_editing_path),
            'message': f'路径 "{path_name}" 已保存，共 {len(current_editing_path)} 个站点'
        })
        
        return jsonify({
            'success': True,
            'message': f'路径 "{path_name}" 已保存成功',
            'file_path': file_path,
            'total_waypoints': len(current_editing_path)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'保存路径失败: {str(e)}'}), 500


@app.route('/api/exhibition/list_paths', methods=['GET'])
def list_exhibition_paths():
    """列出所有已保存的展览路径"""
    try:
        paths = []
        
        if os.path.exists(EXHIBITION_PATH_DIR):
            for file in sorted(os.listdir(EXHIBITION_PATH_DIR)):
                if file.endswith('.json'):
                    file_path = os.path.join(EXHIBITION_PATH_DIR, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            file_stat = os.stat(file_path)
                            paths.append({
                                'name': data.get('name', file[:-5]),
                                'filename': file,
                                'file_path': file_path,
                                'total_waypoints': len(data.get('waypoints', [])),
                                'created_time': data.get('created_time', ''),
                                'updated_time': data.get('updated_time', ''),
                                'modified_time': file_stat.st_mtime
                            })
                    except Exception as e:
                        print(f"读取路径文件失败 {file}: {e}")
        
        paths.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return jsonify({
            'success': True,
            'paths': paths,
            'total': len(paths)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取路径列表失败: {str(e)}'}), 500


@app.route('/api/exhibition/load_path', methods=['POST'])
def load_exhibition_path():
    """加载已保存的路径到编辑器"""
    global current_editing_path
    
    try:
        data = request.get_json() or {}
        filename = data.get('filename', '')
        
        if not filename:
            return jsonify({'success': False, 'message': '请选择要加载的路径'}), 400
        
        file_path = os.path.join(EXHIBITION_PATH_DIR, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': f'路径文件不存在: {filename}'}), 400
        
        with open(file_path, 'r', encoding='utf-8') as f:
            path_data = json.load(f)
        
        current_editing_path = path_data.get('waypoints', [])
        
        for i, wp in enumerate(current_editing_path):
            wp['id'] = i + 1
        
        socketio.emit('path_loaded', {
            'name': path_data.get('name', filename),
            'waypoints': current_editing_path,
            'total': len(current_editing_path),
            'message': f'已加载路径 "{path_data.get("name", filename)}"，共 {len(current_editing_path)} 个站点'
        })
        
        return jsonify({
            'success': True,
            'message': f'已加载路径，共 {len(current_editing_path)} 个站点',
            'path_name': path_data.get('name', filename),
            'waypoints': current_editing_path,
            'total': len(current_editing_path)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'加载路径失败: {str(e)}'}), 500


@app.route('/api/exhibition/delete_path', methods=['POST'])
def delete_exhibition_path():
    """删除已保存的路径文件"""
    try:
        data = request.get_json() or {}
        filename = data.get('filename', '')
        
        if not filename:
            return jsonify({'success': False, 'message': '请选择要删除的路径'}), 400
        
        file_path = os.path.join(EXHIBITION_PATH_DIR, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': f'路径文件不存在: {filename}'}), 400
        
        os.remove(file_path)
        
        socketio.emit('path_deleted', {
            'filename': filename,
            'message': f'已删除路径: {filename}'
        })
        
        return jsonify({
            'success': True,
            'message': f'已删除路径: {filename}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除路径失败: {str(e)}'}), 500


@app.route('/api/exhibition/run_saved_path', methods=['POST'])
def run_saved_path():
    """执行已保存的展览路径（生成临时脚本并运行）"""
    global exhibition_running, exhibition_process
    
    if exhibition_running:
        return jsonify({'success': False, 'message': '展览导航已经在运行中'}), 400
    
    try:
        data = request.get_json() or {}
        filename = data.get('filename', '')
        network_interface = data.get('network_interface', 'eth0')
        
        if not filename:
            return jsonify({'success': False, 'message': '请选择要执行的路径'}), 400
        
        file_path = os.path.join(EXHIBITION_PATH_DIR, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': f'路径文件不存在: {filename}'}), 400
        
        with open(file_path, 'r', encoding='utf-8') as f:
            path_data = json.load(f)
        
        waypoints = path_data.get('waypoints', [])
        
        if not waypoints:
            return jsonify({'success': False, 'message': '路径中没有站点'}), 400
        
        temp_script_path = os.path.join(EXHIBITION_PATH_DIR, '_temp_run_script.py')
        
        script_content = generate_navigation_script(waypoints, network_interface)
        
        with open(temp_script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        subprocess.run(['pkill', '-9', '-f', '_temp_run_script'], capture_output=True)
        time.sleep(0.5)
        
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{os.path.expanduser('~/tang/WK/unitree_sdk2_python')}:{env.get('PYTHONPATH', '')}"
        
        exhibition_process = subprocess.Popen(
            ['python3.9', temp_script_path],
            cwd=os.path.expanduser('~/tang/WK/unitree_sdk2_python/example/g1/high_level'),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print(f"正在执行展览路径: {filename} ({len(waypoints)} 个站点)...")
        time.sleep(3)
        
        result = exhibition_process.poll()
        if result is not None:
            stdout, stderr = exhibition_process.communicate()
            error_msg = f"展览路径执行失败，返回码: {result}\nSTDERR: {stderr.decode()}"
            print(error_msg)
            exhibition_process = None
            return jsonify({'success': False, 'message': error_msg}), 500
        
        exhibition_running = True
        socketio.emit('exhibition_status', {
            'status': 'started',
            'message': f'正在执行展览路径 "{path_data.get("name", filename)}"，共 {len(waypoints)} 个站点'
        })
        return jsonify({
            'success': True,
            'message': f'展览路径执行中，共 {len(waypoints)} 个站点',
            'path_name': path_data.get('name', filename)
        })
        
    except Exception as e:
        exhibition_running = False
        exhibition_process = None
        return jsonify({'success': False, 'message': f'执行展览路径失败: {str(e)}'}), 500


@app.route('/api/exhibition/stop_running_path', methods=['POST'])
def stop_running_path():
    """中断/停止正在执行的展览路径"""
    global exhibition_running, exhibition_process
    
    if not exhibition_running:
        return jsonify({'success': False, 'message': '当前没有正在执行的展览路径'}), 400
    
    try:
        print("[EXHIBITION] 正在中断展览路径执行...")
        
        if exhibition_process and exhibition_process.poll() is None:
            print(f"[EXHIBITION] 终止进程 PID: {exhibition_process.pid}")
            
            try:
                exhibition_process.terminate()
                time.sleep(0.5)
                
                if exhibition_process.poll() is None:
                    print("[EXHIBITION] terminate未生效，使用kill")
                    exhibition_process.kill()
                    time.sleep(0.5)
                    
                    if exhibition_process.poll() is None:
                        print("[EXHIBITION] kill未生效，使用pkill强制终止")
                        subprocess.run(['pkill', '-9', '-f', '_temp_run_script'], capture_output=True)
                        time.sleep(0.3)
            except Exception as term_err:
                print(f"[EXHIBITION] 终止进程异常: {term_err}")
                subprocess.run(['pkill', '-9', '-f', '_temp_run_script'], capture_output=True)
        
        stdout, stderr = exhibition_process.communicate(timeout=2) if exhibition_process else (b'', b'')
        
        exhibition_running = False
        old_process = exhibition_process
        exhibition_process = None
        
        socketio.emit('exhibition_status', {
            'status': 'stopped',
            'message': '✅ 展览路径已成功中断/停止',
            'user_initiated': True
        })
        
        print("[EXHIBITION] ✅ 展览路径已成功中断/停止")
        
        return jsonify({
            'success': True,
            'message': '✅ 展览路径已成功中断/停止',
            'stopped_by_user': True
        })
        
    except subprocess.TimeoutExpired:
        exhibition_running = False
        exhibition_process = None
        subprocess.run(['pkill', '-9', '-f', '_temp_run_script'], capture_output=True)
        
        socketio.emit('exhibition_status', {
            'status': 'stopped',
            'message': '⚠️ 展览路径已强制停止（进程无响应）',
            'user_initiated': True
        })
        
        return jsonify({
            'success': True,
            'message': '⚠️ 展览路径已强制停止'
        })
        
    except Exception as e:
        exhibition_running = False
        exhibition_process = None
        
        print(f"[EXHIBITION] 中断路径失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'中断路径失败: {str(e)}'
        }), 500


def generate_navigation_script(waypoints, network_interface):
    """生成导航脚本的Python代码"""
    
    waypoints_str = '[\n'
    for wp in waypoints:
        say_text = json.dumps(wp['say_texts'][0] if wp['say_texts'] else '你好', ensure_ascii=False)
        waypoints_str += f'''   {{"x": {wp["x"]}, "y": {wp["y"]}, "yaw": {wp["yaw"]}, "action_id": {wp["action_id"]}, "say_text": {say_text}}},\n'''
    waypoints_str += ']'
    
    script = f'''#!/usr/bin/env python3
import rospy
import actionlib
import threading
import time
import math
import tf
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from nav_msgs.msg import Path
from geometry_msgs.msg import Twist
from std_srvs.srv import Empty
from tf.transformations import quaternion_from_euler, euler_from_quaternion
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient

current_global_pose = {{"x": 0.0, "y": 0.0, "yaw": 0.0}}
pose_lock = threading.Lock()

class RobotController:
    def __init__(self, network_interface):
        rospy.loginfo("正在初始化语音和动作系统...")
        ChannelFactoryInitialize(0, network_interface)
        self.audio_client = AudioClient()
        self.audio_client.Init()
        self.audio_client.SetTimeout(10.0)
        self.arm_client = G1ArmActionClient()
        self.arm_client.Init()
        self._wakeup_audio()
        self.global_plan_length = 0
        self.loco_client = LocoClient()
        self.loco_client.SetTimeout(10.0)
        self.loco_client.Init()
        rospy.Subscriber("/move_base/GlobalPlanner/plan", Path, self._path_callback)
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        rospy.loginfo("✅ 语音和动作系统初始化完成")

    def _path_callback(self, msg: Path):
        self.global_plan_length = len(msg.poses)

    def _wakeup_audio(self):
        rospy.loginfo("🔊 正在唤醒音频硬件...")
        for i in range(10):
            try:
                self.audio_client.GetVolume()
                rospy.loginfo("✅ 音频服务已连接")
                break
            except:
                rospy.logwarn(f"⏳ 等待音频服务... ({{i+1}}/10)")
                time.sleep(1)
        self.audio_client.SetVolume(100)
        time.sleep(0.5)
        rospy.loginfo("✅ 音频硬件唤醒完成")

    def speak(self, text):
        try:
            rospy.loginfo(f"🔊 说: {{text}}")
            self.audio_client.TtsMaker(text, 0)
        except Exception as e:
            rospy.logerr(f"语音播放失败: {{e}}")

    def perform_interaction(self, text, action_id):
        rospy.loginfo(f"🤖 执行动作 ID: {{action_id}}")
        action_name_map = {{
            0: "release arm", 1: "shake hand", 2: "high five", 3: "hug",
            4: "high wave", 5: "clap", 6: "face wave", 7: "left kiss",
            8: "heart", 9: "right heart", 10: "hands up", 11: "x-ray",
            12: "right hand up", 13: "reject", 14: "right kiss",
            15: "two-hand kiss"
        }}
        action_name = action_name_map.get(action_id)
        if not action_name:
            rospy.logerr(f"无效的动作 ID: {{action_id}}")
            return
        try:
            self.arm_client.ExecuteAction(action_map.get(action_name))
            time.sleep(2.0)
        except Exception as e:
            rospy.logerr(f"动作执行失败: {{e}}")

        rospy.loginfo(f"🎤 播放: {{text}}")
        self.speak(text)
        
        estimated_speech_time = len(text) * 0.195
        rospy.loginfo(f"⏳ 预计讲解时长: {{estimated_speech_time:.1f}} 秒，正在等待讲解结束...")
        time.sleep(estimated_speech_time)

        rospy.loginfo("🔄 讲解结束，正在复位手臂...")
        try:
            self.arm_client.ExecuteAction(99)
            time.sleep(3.0)
        except Exception as e:
            rospy.logerr(f"复位失败: {{e}}")

    def rotate_to_yaw(self, target_yaw, listener):
        rospy.loginfo(f"🔄 开始原地旋转修正航向至: {{math.degrees(target_yaw):.1f}}°")
        rate = rospy.Rate(20)
        
        while not rospy.is_shutdown():
            try:
                (trans, rot) = listener.lookupTransform("/map", "/base_link", rospy.Time(0))
                current_yaw = euler_from_quaternion(rot)[2]
                
                yaw_diff = math.atan2(math.sin(target_yaw - current_yaw), math.cos(target_yaw - current_yaw))
                
                if abs(yaw_diff) < 0.1:
                    rospy.loginfo("✅ 航向对齐完成")
                    break
                
                cmd_wz = max(-0.6, min(0.6, yaw_diff * 1.5))
                
                twist_msg = Twist()
                twist_msg.angular.z = cmd_wz
                self.cmd_vel_pub.publish(twist_msg)
                
            except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
                pass
            
            rate.sleep()
        
        self.cmd_vel_pub.publish(Twist())
        time.sleep(0.1)


def set_fast_params():
    rospy.set_param('/move_base/TebLocalPlannerROS/max_vel_x', 0.8)
    rospy.set_param('/move_base/TebLocalPlannerROS/max_vel_theta', 0.8)
    rospy.set_param('/move_base/TebLocalPlannerROS/acc_lim_x', 0.8)
    rospy.set_param('/move_base/TebLocalPlannerROS/acc_lim_theta', 0.7)
    rospy.set_param('/move_base/TebLocalPlannerROS/path_distance_bias', 60.0)
    rospy.set_param('/move_base/TebLocalPlannerROS/goal_distance_bias', 20.0)
    rospy.set_param('/move_base/TebLocalPlannerROS/xy_goal_tolerance', 0.05)
    rospy.set_param('/move_base/TebLocalPlannerROS/yaw_goal_tolerance', 0.05)
    rospy.set_param('/move_base/TebLocalPlannerROS/min_turning_radius', 0.0)
    rospy.set_param('/move_base/TebLocalPlannerROS/weight_optimaltime', 1.0)

def set_slow_params():
    rospy.set_param('/move_base/TebLocalPlannerROS/max_vel_x', 0.6)
    rospy.set_param('/move_base/TebLocalPlannerROS/max_vel_theta', 1.0)
    rospy.set_param('/move_base/TebLocalPlannerROS/acc_lim_x', 0.5)
    rospy.set_param('/move_base/TebLocalPlannerROS/acc_lim_theta', 0.8)
    rospy.set_param('/move_base/TebLocalPlannerROS/min_turning_radius', 0.0)
    rospy.set_param('/move_base/TebLocalPlannerROS/max_vel_x_backwards', 0.0)
    rospy.set_param('/move_base/TebLocalPlannerROS/xy_goal_tolerance', 0.2)
    rospy.set_param('/move_base/TebLocalPlannerROS/yaw_goal_tolerance', 0.2)


def force_robot_stop(robot_controller_instance):
    rospy.logwarn("🛑 强制接管控制...")
    try:
        robot_controller_instance.loco_client.StopMove()
        stop_msg = Twist()
        for _ in range(10):
            robot_controller_instance.cmd_vel_pub.publish(stop_msg)
            time.sleep(0.02)
        rospy.loginfo("🛑 SDK StopMove 指令已发送")
    except Exception as e:
        rospy.logerr(f"SDK 停止指令发送失败: {{e}}")
    time.sleep(0.1)


def navigate_to_waypoints(waypoints, robot_controller):
    client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    rospy.loginfo("等待move_base服务器启动...")
    client.wait_for_server()

    clear_costmaps_service = rospy.ServiceProxy('/move_base/clear_costmaps', Empty)
    
    rospy.set_param('/move_base/DWAPlannerROS/yaw_goal_tolerance', 0.4)
    rospy.set_param('/move_base/DWAPlannerROS/max_rot_vel', 0.6)
    rospy.set_param('/move_base/DWAPlannerROS/min_rot_vel', 0.2)
    rospy.set_param('/move_base/DWAPlannerROS/acc_lim_theta', 0.2)
    rospy.set_param('/move_base/DWAPlannerROS/path_distance_bias', 40.0)
    rospy.set_param('/move_base/DWAPlannerROS/goal_distance_bias', 15.0)
    rospy.set_param('/move_base/planner_patience', 30.0)
    rospy.set_param('/move_base/planner_frequency', 2.0)

    listener = tf.TransformListener()
    base_frame = "/base_link" 
    map_frame = "/map"
    
    STOP_YAW_TOLERANCE = 3.14

    for idx, waypoint in enumerate(waypoints):
        rospy.loginfo("⏳ 获取机器人在地图中的真实初始位置...")
        try:
            listener.waitForTransform(map_frame, base_frame, rospy.Time(), rospy.Duration(4.0))
            (trans, rot) = listener.lookupTransform(map_frame, base_frame, rospy.Time(0))
            with pose_lock:
                current_global_pose["x"] = trans[0]
                current_global_pose["y"] = trans[1]
            rospy.loginfo(f"📍 初始全局位置: ({{current_global_pose['x']:.2f}}, {{current_global_pose['y']:.2f}})")
        except Exception as e:
            rospy.logerr(f"❌ 无法获取 TF 变换: {{e}}")
            continue

        start_dist = math.sqrt(
            (waypoint["x"] - current_global_pose["x"]) ** 2 + 
            (waypoint["y"] - current_global_pose["y"]) ** 2
        )
        
        if start_dist < 1.0:
            STOP_DISTANCE = 0.1
        else:
            STOP_DISTANCE = 0.2
            
        SLOWDOWN_DISTANCE = 1.5

        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = waypoint["x"]
        goal.target_pose.pose.position.y = waypoint["y"]
        goal.target_pose.pose.position.z = 0.0

        q = quaternion_from_euler(0, 0, waypoint["yaw"])
        goal.target_pose.pose.orientation.x = q[0]
        goal.target_pose.pose.orientation.y = q[1]
        goal.target_pose.pose.orientation.z = q[2]
        goal.target_pose.pose.orientation.w = q[3]

        rospy.loginfo(f"发送第{{idx+1}}个目标: ({{waypoint['x']}}, {{waypoint['y']}}, yaw: {{waypoint['yaw']:.2f}})")
        
        set_fast_params()
        client.send_goal(goal)

        start_time = time.time()
        last_spoke_time = 0.0
        speak_interval = 10.0
        obstacle_start_time = 0.0 
        map_cleared = False
        is_fast_mode = True
        slowdown_switched = False
        
        while not rospy.is_shutdown():
            state = client.get_state()
            elapsed = time.time() - start_time
            now = time.time()

            def handle_arrival(reason):
                rospy.loginfo(f"✅ {{reason}}：触发第{{idx+1}}个点停止流程")
                client.cancel_goal()
                force_robot_stop(robot_controller)
                
                try:
                    (trans, rot) = listener.lookupTransform(map_frame, base_frame, rospy.Time(0))
                    current_yaw = euler_from_quaternion(rot)[2]
                    yaw_diff = math.atan2(math.sin(waypoint["yaw"] - current_yaw), math.cos(waypoint["yaw"] - current_yaw))
                    
                    if abs(yaw_diff) > 0.15:
                        robot_controller.rotate_to_yaw(waypoint["yaw"], listener)
                except:
                    pass
                
                say_text = waypoint.get("say_text", "你好")
                action_id = waypoint.get("action_id", 25)
                robot_controller.perform_interaction(say_text, action_id)
                
                rospy.loginfo("🎯 讲解与动作执行完毕，准备前往下一站")
                return True

            if state == actionlib.GoalStatus.ACTIVE:
                try:
                    (trans, rot) = listener.lookupTransform(map_frame, base_frame, rospy.Time(0))
                    cur_x = trans[0]
                    cur_y = trans[1]
                    current_yaw = euler_from_quaternion(rot)[2]
                    
                    with pose_lock:
                        current_global_pose["x"] = cur_x
                        current_global_pose["y"] = cur_y
                        current_global_pose["yaw"] = current_yaw

                    distance_to_goal = math.sqrt(
                        (waypoint["x"] - cur_x) ** 2 + 
                        (waypoint["y"] - cur_y) ** 2
                    )
                    
                    yaw_diff = math.atan2(
                        math.sin(waypoint["yaw"] - current_yaw), 
                        math.cos(waypoint["yaw"] - current_yaw)
                    )

                    if is_fast_mode and distance_to_goal < SLOWDOWN_DISTANCE and not slowdown_switched:
                        rospy.loginfo(f"📏 距离目标 {{distance_to_goal:.2f}}m，切换到慢速模式")
                        set_slow_params()
                        is_fast_mode = False
                        slowdown_switched = True
                    
                    if elapsed > 0.8 and distance_to_goal < STOP_DISTANCE:
                        if handle_arrival(f"物理距离达标 (Dist: {{distance_to_goal:.2f}}m)"):
                            break

                except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
                    pass

                if elapsed > 0.8: 
                    if robot_controller.global_plan_length == 0:
                        if obstacle_start_time == 0.0:
                            obstacle_start_time = now
                        
                        if now - obstacle_start_time > 1.5: 
                            if now - last_spoke_time > speak_interval:
                                robot_controller.speak("请让一让我")
                                last_spoke_time = now
                            
                            if (not map_cleared):
                                rospy.loginfo("🧹 尝试清除代价地图...")
                                try:
                                    clear_costmaps_service()
                                    map_cleared = True
                                except Exception as e:
                                    rospy.logerr(f"清除代价地图失败: {{e}}")
                    else:
                        if obstacle_start_time != 0.0:
                            rospy.loginfo("✅ 路径已恢复")
                            obstacle_start_time = 0.0
                            map_cleared = False

            if state == actionlib.GoalStatus.SUCCEEDED:
                if handle_arrival("Move_base 判定到达"):
                    break

            if state == actionlib.GoalStatus.ABORTED:
                rospy.logwarn(f"⚠️ 第{{idx+1}}个目标导航失败，跳过")
                robot_controller.speak("无法到达该目标位置，即将前往下一位置")
                time.sleep(3.0)
                break

            rospy.sleep(0.01) 

if __name__ == '__main__':
    try:
        rospy.init_node('multi_waypoint_nav')

        network_interface = '{network_interface}'
        robot_controller = RobotController(network_interface)

        rospy.sleep(1.0)
        robot_controller.speak("启动成功")

        waypoints = {waypoints_str}

        navigate_to_waypoints(waypoints, robot_controller)
        
        robot_controller.speak("展览巡逻完成")

    except rospy.ROSInterruptException:
        rospy.loginfo("导航脚本被中断")
'''
    
    return script


@app.route('/api/map_origin', methods=['GET'])
def get_current_map_origin():
    """获取当前选择地图的原点信息"""
    global selected_map

    if selected_map and selected_map in MAP_ORIGINS:
        origin_info = MAP_ORIGINS[selected_map]
        return jsonify({
            'success': True,
            'map_name': selected_map,
            'origin': {
                'x': origin_info['x'],
                'y': origin_info['y']
            },
            'description': origin_info.get('desc', ''),
            'message': f'📍 当前地图 [{selected_map}] 原点: ({origin_info["x"]}, {origin_info["y"]})'
        })
    elif selected_map:
        try:
            yaml_path = f'/home/unitree/tang/map/{selected_map}.yaml'
            with open(yaml_path, 'r') as f:
                content = f.read()
            import re
            match = re.search(r'origin:\s*\[([-\d.]+),\s*([-\d.]+)', content)
            if match:
                return jsonify({
                    'success': True,
                    'map_name': selected_map,
                    'origin': {
                        'x': float(match.group(1)),
                        'y': float(match.group(2))
                    },
                    'description': f'{selected_map} (从yaml动态读取)',
                    'message': f'📍 地图 [{selected_map}] 原点: ({float(match.group(1))}, {float(match.group(2))})'
                })
        except Exception as e:
            pass
        return jsonify({
            'success': False,
            'map_name': selected_map,
            'origin': None,
            'message': f'⚠️ 无法读取地图 [{selected_map}] 的原点信息'
        }), 404
    else:
        return jsonify({
            'success': False,
            'map_name': None,
            'origin': None,
            'message': '⚠️ 未选择任何地图，请先在"保存地图"模块选择导航地图'
        }), 400


@app.route('/api/pcd_files', methods=['GET'])
def list_pcd_files():
    """获取所有可用的 PCD 文件列表"""
    try:
        pcds = list_available_pcds()
        
        # 获取当前地图对应的 PCD 信息
        current_pcd_path, current_source_type, current_message = get_pcd_path_for_map(selected_map)
        current_pcd_info = {
            'path': current_pcd_path,
            'filename': os.path.basename(current_pcd_path) if current_pcd_path else None,
            'source_type': current_source_type,
            'message': current_message
        }
        if current_pcd_path and os.path.exists(current_pcd_path):
            current_pcd_info['size_mb'] = round(os.path.getsize(current_pcd_path) / (1024 * 1024), 2)
            import datetime
            current_pcd_info['modified'] = datetime.datetime.fromtimestamp(
                os.path.getmtime(current_pcd_path)
            ).strftime('%Y-%m-%d %H:%M')
        
        return jsonify({
            'success': True,
            'current_map': selected_map,
            'current_pcd': current_pcd_info,
            'available_pcds': pcds,
            'pcd_dir': PCD_DIR,
            'total_count': len(pcds),
            'message': f'📦 共找到 {len(pcds)} 个 PCD 文件'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'❌ 获取 PCD 列表失败: {str(e)}'
        }), 500


@app.route('/api/pcd_check', methods=['POST'])
def check_pcd_for_map():
    """检查指定地图的 PCD 文件状态"""
    try:
        data = request.get_json() or {}
        map_name = data.get('map_name', selected_map)
        
        if not map_name:
            return jsonify({
                'success': False,
                'message': '❌ 未指定地图名称'
            }), 400
        
        # 获取 PCD 路径和来源信息
        pcd_path, source_type, message = get_pcd_path_for_map(map_name)
        
        # 检查文件有效性
        is_valid, error_msg = check_pcd_file_valid(pcd_path, map_name) if pcd_path else (False, "文件不存在")
        
        result = {
            'success': True,
            'map_name': map_name,
            'pcd_path': pcd_path,
            'pcd_filename': os.path.basename(pcd_path) if pcd_path else None,
            'source_type': source_type,
            'source_message': message,
            'is_valid': is_valid,
            'recommendation': ''
        }
        
        if pcd_path and os.path.exists(pcd_path):
            result['size_mb'] = round(os.path.getsize(pcd_path) / (1024 * 1024), 2)
            import datetime
            result['modified'] = datetime.datetime.fromtimestamp(
                os.path.getmtime(pcd_path)
            ).strftime('%Y-%m-%d %H:%M')
            
            # 生成建议
            if source_type == 'default':
                result['recommendation'] = (
                    f'⚠️ 当前使用默认 map.pcd，建议为 [{map_name}] 创建专用 PCD 文件\n'
                    f'   可通过建图时保存点云自动生成 {map_name}.pcd'
                )
            elif source_type == 'specific':
                result['recommendation'] = f'✅ [{map_name}] 有专用的 PCD 文件，配置正确'
            
            if is_valid:
                result['status'] = '✅ PCD 文件有效'
            else:
                result['status'] = f'❌ PCD 文件无效: {error_msg}'
                result['recommendation'] += f'\n   错误: {error_msg}'
        else:
            result['status'] = '❌ PCD 文件不存在'
            result['recommendation'] = (
                f'❌ 未找到 [{map_name}] 的 PCD 文件！\n'
                f'   请执行以下操作之一：\n'
                f'   1. 使用该地图重新建图并保存点云\n'
                f'   2. 手动复制其他 PCD 文件为 {map_name}.pcd'
            )
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'❌ 检查 PCD 失败: {str(e)}'
        }), 500


@app.route('/api/relocate', methods=['POST'])
def relocate():
    """FastLIO 智能重定位机器人位置（针对 FastLIO SLAM 优化）"""
    try:
        data = request.get_json() or {}
        x = float(data.get('x', 0.0))
        y = float(data.get('y', 0.0))
        z = float(data.get('z', 0.0))
        roll = float(data.get('roll', 0.0))
        pitch = float(data.get('pitch', 0.0))
        yaw = float(data.get('yaw', 0.0))

        if not navigation_running:
            return jsonify({'success': False, 'message': '请先启动导航'}), 400

        g1nav_dir = os.path.expanduser('~/tang/WK/G1Nav2D')
        
        # 🎯 动态选择 PCD 文件（根据当前选择的地图）
        pcd_path, pcd_source_type, pcd_message = get_pcd_path_for_map(selected_map)

        print(f"\n[RELOCATE] 🗺️  当前地图: {selected_map or '未选择'}")
        print(f"[RELOCATE] 📦 PCD 文件: {os.path.basename(pcd_path) if pcd_path else '无'}")
        print(f"[RELOCATE] 💡 PCD 来源: {pcd_message}")
        
        # 检查 PCD 文件有效性
        if pcd_path:
            is_valid, error_msg = check_pcd_file_valid(pcd_path, selected_map)
            if not is_valid:
                fail_msg = (
                    f'❌ PCD 文件无效\n'
                    f'━━━━━━━━━━━━━━━━━━━━━━━\n'
                    f'📄 文件: {os.path.basename(pcd_path)}\n'
                    f'❌ 错误: {error_msg}\n'
                    f'━━━━━━━━━━━━━━━━━━━━━━━\n'
                    f'💡 解决方案:\n'
                    f'1. 重新建图并保存点云地图\n'
                    f'2. 或复制正确的 PCD 文件到:\n'
                    f'   {PCD_DIR}/{selected_map or "map"}.pcd'
                )
                print(f"[RELOCATE] {fail_msg}")
                socketio.emit('relocate_status', {
                    'status': 'failed',
                    'message': fail_msg
                })
                return jsonify({'success': False, 'message': fail_msg}), 500
        else:
            fail_msg = (
                f'❌ 未找到 PCD 点云文件\n'
                f'━━━━━━━━━━━━━━━━━━━━━━━\n'
                f'💡 请先执行建图操作保存 PCD 地图！'
            )
            print(f"[RELOCATE] {fail_msg}")
            socketio.emit('relocate_status', {
                'status': 'failed',
                'message': fail_msg
            })
            return jsonify({'success': False, 'message': fail_msg}), 500

        env = os.environ.copy()
        env['DISPLAY'] = VNC_DISPLAY
        env['ROS_MASTER_URI'] = 'http://localhost:11311'

        import re

        print("\n" + "="*60)
        print("[RELOCATE] 🚀 FastLIO 重定位开始")
        print("="*60)
        socketio.emit('relocate_status', {'status': 'progress', 'message': '🔍 正在检查 FastLIO 服务...'})

        def check_fastlio_service():
            """检查 FastLIO /slam_reloc 服务是否可用"""
            try:
                result = subprocess.run(
                    ['bash', '-c',
                     f"source {g1nav_dir}/devel/setup.bash && "
                     "timeout 3 rosservice list | grep -E 'slam_reloc|fastlio'"],
                    cwd=g1nav_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout:
                    print(f"[RELOCATE] ✅ 找到服务: {result.stdout.strip()}")
                    return True
                else:
                    print(f"[RELOCATE] ⚠️ 未找到 slam_reloc 服务")
                    return False
            except Exception as e:
                print(f"[RELOCATE] ❌ 检查服务异常: {e}")
                return False

        def check_network_quality():
            """简单网络质量检查"""
            try:
                ping_result = subprocess.run(
                    ['ping', '-c', '1', '-W', '2', 'localhost'],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if ping_result.returncode == 0:
                    print("[RELOCATE] ✅ 网络连接正常")
                    return True
                else:
                    print("[RELOCATE] ⚠️ 网络可能不稳定")
                    return False
            except:
                return True

        def get_map_origin():
            """根据当前选择的地图获取原点（始终从文件读取最新值，避免缓存过期）"""
            global selected_map, MAP_ORIGINS

            if selected_map:
                try:
                    yaml_path = f'/home/unitree/tang/map/{selected_map}.yaml'
                    with open(yaml_path, 'r') as f:
                        content = f.read()
                    match = re.search(r'origin:\s*\[([-\d.]+),\s*([-\d.]+)', content)
                    if match:
                        origin_x = float(match.group(1))
                        origin_y = float(match.group(2))

                        MAP_ORIGINS[selected_map] = {
                            'x': origin_x,
                            'y': origin_y,
                            'desc': f'{selected_map} (实时读取)',
                            'source': yaml_path
                        }

                        print(f"[RELOCATE] 📍 地图 [{selected_map}] 原点（实时读取）: ({origin_x:.3f}, {origin_y:.3f})")
                        return origin_x, origin_y
                    else:
                        print(f"[RELOCATE] ⚠️ 无法从 {yaml_path} 解析原点")
                        return None, None
                except Exception as e:
                    print(f"[RELOCATE] ⚠️ 读取 {selected_map}.yaml 失败: {e}")
                    if selected_map in MAP_ORIGINS:
                        print(f"[RELOCATE] ⚠️ 回退到缓存值: {MAP_ORIGINS[selected_map]}")
                        return MAP_ORIGINS[selected_map]['x'], MAP_ORIGINS[selected_map]['y']
                    return None, None
            else:
                print("[RELOCATE] ⚠️ 未选择任何地图，尝试读取默认 mymap.yaml")
                try:
                    with open('/home/unitree/tang/map/mymap.yaml', 'r') as f:
                        content = f.read()
                    match = re.search(r'origin:\s*\[([-\d.]+),\s*([-\d.]+)', content)
                    if match:
                        origin_x = float(match.group(1))
                        origin_y = float(match.group(2))
                        print(f"[RELOCATE] 📍 默认地图原点: ({origin_x:.3f}, {origin_y:.3f})")
                        return origin_x, origin_y
                    return None, None
                except Exception as e:
                    print(f"[RELOCATE] ⚠️ 读取默认地图原点失败: {e}")
                    return None, None

        def execute_fastlio_relocate(init_x, init_y, init_z, init_roll, init_pitch, init_yaw):
            """
            执行 FastLIO 重定位命令
            严格照搬 README.md#L274-279 中 VNC 验证成功的命令：
              rosservice call /slam_reloc "{pcd_path: '.../map.pcd', x: 0.0, y: 0.0, ...}"
            关键：不加 timeout，让 ICP 配准完整跑完（与 VNC 一致）
            返回: (成功与否, 标准输出, 标准错误)
            """
            # 完全照搬 VNC 命令：只 source + rosservice call（无 timeout）
            cmd = (
                f"source {g1nav_dir}/devel/setup.bash && "
                f"rosservice call /slam_reloc "
                f'"{{pcd_path: \'{pcd_path}\', '
                f'x: {init_x}, y: {init_y}, z: {init_z}, '
                f'roll: {init_roll}, pitch: {init_pitch}, yaw: {init_yaw}}}"'
            )

            try:
                result = subprocess.run(
                    ['bash', '-c', cmd],
                    cwd=g1nav_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=120  # 给 ICP 配准足够时间（不限制 rosservice 本身）
                )

                stdout = (result.stdout or '').strip()
                stderr = (result.stderr or '').strip()

                is_success = result.returncode == 0 and 'RELOCALIZE CALLED' in stdout

                return is_success, stdout, stderr

            except subprocess.TimeoutExpired:
                print("[RELOCATE] ⏰ 命令执行超时（120秒）- ICP 配准未在限定时间内完成")
                return False, '', 'Timeout'
            except Exception as e:
                print(f"[RELOCATE] ❌ 执行异常: {e}")
                return False, '', str(e)

        def verify_position_updated():
            """
            验证重定位是否真正生效
            简化逻辑：轮询 ICP 状态直到成功或超时
            """
            try:
                # 轮询等待 ICP 完成（最多 90 秒）
                for i in range(18):  # 18 * 5s = 90s
                    time.sleep(5)
                    check_cmd = (
                        f"source {g1nav_dir}/devel/setup.bash && "
                        "timeout 3 rosservice call /slam_reloc_check '{}' 2>&1"
                    )
                    check_result = subprocess.run(
                        ['bash', '-c', check_cmd],
                        cwd=g1nav_dir, env=env,
                        capture_output=True, text=True, timeout=5
                    )
                    if check_result.stdout and 'status: 1' in check_result.stdout:
                        print(f"[RELOCATE] ✅ ICP 配准成功（第 {i+1} 次查询，{5*(i+1)}s）")
                        # 获取 TF 位置
                        tf_cmd = (
                            f"source {g1nav_dir}/devel/setup.bash && "
                            "timeout 3 rosrun tf tf_echo map base_link 2>&1"
                        )
                        tf_result = subprocess.run(
                            ['bash', '-c', tf_cmd],
                            cwd=g1nav_dir, env=env,
                            capture_output=True, text=True, timeout=5
                        )
                        if tf_result.stdout and 'Translation' in tf_result.stdout:
                            m = re.search(
                                r'Translation:\s*\[([-\d.]+),\s*([-\d.]+),',
                                tf_result.stdout
                            )
                            if m:
                                return True, (float(m.group(1)), float(m.group(2)))
                        return True, (0, 0)

                print(f"[RELOCATE] ❌ ICP 配准超时或失败")
                return False, (0, 0)
            except Exception as e:
                print(f"[RELOCATE] 验证异常: {e}")
                return False, (0, 0)

        if not check_fastlio_service():
            msg = ('❌ FastLIO 服务不可用\n'
                   '可能原因：\n'
                   '1. 导航未完全启动\n'
                   '2. FastLIO 节点崩溃\n'
                   '3. ROS Master 连接问题')
            print(f"[RELOCATE] {msg}")
            socketio.emit('relocate_status', {'status': 'failed', 'message': msg})
            return jsonify({'success': False, 'message': msg}), 500

        # 🎯 严格按 README.md#L274-279 执行：map.pcd + (0, 0, 0, 0, 0, 0)
        # 点击即发送命令（不轮询、不等待、不验证）
        # ICP 会在 localizer_node 主循环里异步跑完，RViz 自动更新
        print(f"\n[RELOCATE] 🚀 发送重定位命令（VNC 验证命令）")
        socketio.emit('relocate_status', {'status': 'progress', 'message': '🚀 发送重定位命令...'})

        cmd_ok, out, err = execute_fastlio_relocate(0, 0, 0, 0, 0, 0)

        print(f"[RELOCATE] 命令执行: {'✅ 成功' if cmd_ok else '❌ 失败'}")
        if out:
            print(f"[RELOCATE] 输出: {out[:120]}")
        if err:
            print(f"[RELOCATE] 错误: {err[:120]}")

        if cmd_ok:
            msg = (
                f'✅ 重定位命令已发送！\n'
                f'━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
                f'📦 点云地图: {os.path.basename(pcd_path) if pcd_path else "未知"}\n'
                f'🎯 初始位姿: (0, 0, 0, 0, 0, 0)\n'
                f'⏳ ICP 配准在后台异步进行中\n'
                f'🖥️  请在 noVNC 的 RViz 中查看定位结果\n'
                f'━━━━━━━━━━━━━━━━━━━━━━━━━━'
            )
            print(f"[RELOCATE] {msg}")
            socketio.emit('relocate_status', {'status': 'success', 'message': msg})
            return jsonify({
                'success': True,
                'message': msg,
                'position': {'x': 0, 'y': 0},
                'strategy': 'VNC 命令直接发送'
            })
        else:
            fail_msg = f'❌ 命令执行失败: {err or "未知错误"}'
            print(f"[RELOCATE] {fail_msg}")
            socketio.emit('relocate_status', {'status': 'failed', 'message': fail_msg})
            return jsonify({'success': False, 'message': fail_msg}), 500

    except subprocess.TimeoutExpired:
        timeout_msg = '⏰ 操作超时（网络延迟过高）'
        print(f"[RELOCATE] {timeout_msg}")
        socketio.emit('relocate_status', {'status': 'failed', 'message': timeout_msg})
        return jsonify({'success': False, 'message': timeout_msg}), 500

    except Exception as e:
        err_msg = f'💥 重定位异常: {str(e)}'
        print(f"[RELOCATE] {err_msg}")
        import traceback
        traceback.print_exc()
        socketio.emit('relocate_status', {'status': 'failed', 'message': err_msg})
        return jsonify({'success': False, 'message': err_msg}), 500

def _rviz_capture_loop():
    pass

@app.route('/rviz_stream')
def rviz_stream():
    return Response(status=404)

@app.route('/rviz_snapshot')
def rviz_snapshot():
    return Response(status=404)

@app.route('/api/toggle_rviz', methods=['POST'])
def toggle_rviz():
    """切换RViz显示状态 - 使用VNC+noVNC方案"""
    global rviz_streaming, rviz_process, vnc_process, websockify_process
    
    if rviz_streaming:
        subprocess.run(['pkill', '-f', 'rviz'], capture_output=True)
        subprocess.run(['pkill', '-f', 'roslaunch'], capture_output=True)
        subprocess.run(['pkill', '-f', 'roscore'], capture_output=True)
        subprocess.run(['pkill', '-f', 'rosout'], capture_output=True)
        _stop_vnc()
        rviz_process = None
        rviz_streaming = False
        socketio.emit('rviz_status', {
            'status': 'stopped',
            'message': 'RViz已停止'
        })
        return jsonify({'success': True, 'message': 'RViz已停止'})
    else:
        try:
            vnc_result = subprocess.run(
                ['vncserver', VNC_DISPLAY, '-geometry', '1920x1080', '-depth', '24',
                 '-xstartup', '/usr/bin/xterm', '-localhost', 'no'],
                capture_output=True, text=True, timeout=10
            )
            if vnc_result.returncode != 0:
                if f"already running" not in vnc_result.stderr and f"already running" not in vnc_result.stdout:
                    return jsonify({'success': False, 'message': f'VNC启动失败: {vnc_result.stderr}'}), 500
            time.sleep(2)
            
            websockify_process = subprocess.Popen(
                ['websockify', '--web', NOVNC_PATH, str(WEBSOCKIFY_PORT), f'localhost:{VNC_PORT}'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            time.sleep(1)
            
            if websockify_process.poll() is not None:
                _, ws_err = websockify_process.communicate()
                return jsonify({'success': False, 'message': f'websockify启动失败: {ws_err.decode()}'}), 500
            
            env = os.environ.copy()
            env['DISPLAY'] = VNC_DISPLAY
            g1nav_dir = os.path.expanduser('~/tang/WK/G1Nav2D')
            env['ROS_PACKAGE_PATH'] = f"{g1nav_dir}/devel:{env.get('ROS_PACKAGE_PATH', '')}"
            
            rviz_process = subprocess.Popen(
                ['bash', '-c', f'source {g1nav_dir}/devel/setup.bash && roslaunch fastlio navigation.launch'],
                cwd=g1nav_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print("正在启动导航（包含RViz）...")
            time.sleep(10)
            
            result = rviz_process.poll()
            if result is not None:
                stdout, stderr = rviz_process.communicate()
                error_msg = f"导航启动失败，返回码: {result}\nSTDERR: {stderr.decode()}"
                print(error_msg)
                _stop_vnc()
                return jsonify({'success': False, 'message': error_msg}), 500
            
            rviz_streaming = True
            socketio.emit('rviz_status', {
                'status': 'started',
                'message': 'RViz已启动（可交互）'
            })
            return jsonify({'success': True, 'message': 'RViz已启动（可交互）'})
            
        except Exception as e:
            error_msg = f'启动RViz失败：{str(e)}'
            print(error_msg)
            _stop_vnc()
            return jsonify({'success': False, 'message': error_msg}), 500


@app.route('/api/execute', methods=['POST'])
def execute_action_api():
    """执行动作API"""
    global current_action
    
    if not initialized:
        return jsonify({'success': False, 'message': 'SDK未初始化'}), 400
    
    data = request.get_json() or {}
    action_id = data.get('action_id')
    
    if action_id is None:
        return jsonify({'success': False, 'message': '缺少action_id参数'}), 400
    
    # 查找动作
    action = None
    for a in action_list:
        if a['id'] == action_id:
            action = a
            break
    
    if not action:
        return jsonify({'success': False, 'message': f'未知的动作ID: {action_id}'}), 400
    
    with action_lock:
        if current_action is not None:
            return jsonify({'success': False, 'message': '有动作正在执行中'}), 400
        
        current_action = action_id
    
    try:
        # 执行动作
        success = execute_action(action_id)
        
        with action_lock:
            current_action = None
        
        if success:
            socketio.emit('action_complete', {
                'action_id': action_id,
                'action_name': action['name'],
                'success': True
            })
            return jsonify({
                'success': True,
                'message': f'动作 "{action["name"]}" 执行成功',
                'action_id': action_id,
                'action_name': action['name']
            })
        else:
            return jsonify({
                'success': False,
                'message': f'动作 "{action["name"]}" 执行失败',
                'action_id': action_id
            }), 500
            
    except Exception as e:
        with action_lock:
            current_action = None
        return jsonify({'success': False, 'message': f'执行动作失败: {str(e)}'}), 500

# 动作名称到ID的映射
action_name_map = {
    0: "release arm",
    1: "shake hand",
    2: "high five",
    3: "hug",
    4: "high wave",
    5: "clap",
    6: "face wave",
    7: "left kiss",
    8: "heart",
    9: "right heart",
    10: "hands up",
    11: "x-ray",
    12: "right hand up",
    13: "reject",
    14: "right kiss",
    15: "two-hand kiss"
}

def execute_action(action_id):
    """执行具体的机械臂动作"""
    global arm_client
    
    try:
        action_name = action_name_map.get(action_id)
        if not action_name:
            print(f"未知的动作ID: {action_id}")
            return False
        
        # 使用action_map获取动作值并执行
        action_value = action_map.get(action_name)
        if action_value is not None:
            arm_client.ExecuteAction(action_value)
            time.sleep(2.0)
            return True
        else:
            print(f"动作 {action_name} 未在action_map中找到")
            return False
    except Exception as e:
        print(f"动作执行失败: {e}")
        return False

@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    global virtual_remote_connected_clients
    virtual_remote_connected_clients += 1
    print(f'客户端已连接 (虚拟遥控器连接数: {virtual_remote_connected_clients})')
    emit('connected', {'message': '连接成功'})
    # 同步虚拟遥控器状态
    emit('virtual_remote_status', virtual_remote_publisher.get_status())

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开"""
    global virtual_remote_connected_clients
    virtual_remote_connected_clients = max(0, virtual_remote_connected_clients - 1)
    print(f'客户端已断开 (虚拟遥控器连接数: {virtual_remote_connected_clients})')
    if virtual_remote_connected_clients == 0:
        virtual_remote_publisher.state.reset()
        print("[VirtualRemote] 无客户端连接，已重置遥控器状态")

@socketio.on('execute_action')
def handle_execute_action(data):
    """处理WebSocket动作执行请求"""
    global current_action
    
    if not initialized:
        emit('action_status', {
            'action_id': data.get('action_id'),
            'status': 'error',
            'message': 'SDK未初始化'
        })
        return
    
    action_id = data.get('action_id')
    if action_id is None:
        emit('action_status', {
            'action_id': action_id,
            'status': 'error',
            'message': '缺少action_id参数'
        })
        return
    
    # 查找动作
    action = None
    for a in action_list:
        if a['id'] == action_id:
            action = a
            break
    
    if not action:
        emit('action_status', {
            'action_id': action_id,
            'status': 'error',
            'message': f'未知的动作ID: {action_id}'
        })
        return
    
    with action_lock:
        if current_action is not None:
            emit('action_status', {
                'action_id': action_id,
                'status': 'error',
                'message': '有动作正在执行中'
            })
            return
        
        current_action = action_id
    
    try:
        # 发送执行中状态
        emit('action_status', {
            'action_id': action_id,
            'action_name': action['name'],
            'status': 'executing',
            'message': f'正在执行动作: {action["name"]}'
        })
        
        # 执行动作
        success = execute_action(action_id)
        
        with action_lock:
            current_action = None
        
        if success:
            emit('action_status', {
                'action_id': action_id,
                'action_name': action['name'],
                'status': 'completed',
                'message': f'动作 "{action["name"]}" 执行成功'
            })
        else:
            emit('action_status', {
                'action_id': action_id,
                'action_name': action['name'],
                'status': 'error',
                'message': f'动作 "{action["name"]}" 执行失败'
            })
            
    except Exception as e:
        with action_lock:
            current_action = None
        emit('action_status', {
            'action_id': action_id,
            'action_name': action.get('name', '未知'),
            'status': 'error',
            'message': f'执行动作失败: {str(e)}'
        })


# ============ 虚拟遥控器 WebSocket 事件 ============
@socketio.on('virtual_remote_init')
def on_virtual_remote_init(data):
    """初始化虚拟遥控器（独立于init_clients，默认eth0）"""
    print(f"[VirtualRemote] 收到 virtual_remote_init 请求, data={data}, 已初始化={virtual_remote_publisher.initialized}")
    if not virtual_remote_publisher.initialized:
        iface = 'eth0'
        if data and isinstance(data, dict):
            iface = data.get('interface', 'eth0')
        success, message = virtual_remote_publisher.init_dds(iface)
        print(f"[VirtualRemote] init_dds 结果: success={success}, message={message}, running={virtual_remote_publisher.running}")
        emit('virtual_remote_init_result', {
            'success': success,
            'message': message,
            'running': virtual_remote_publisher.running
        })
    else:
        print(f"[VirtualRemote] 已初始化，返回就绪状态, running={virtual_remote_publisher.running}")
        emit('virtual_remote_init_result', {
            'success': True,
            'message': '虚拟遥控器已就绪',
            'running': virtual_remote_publisher.running
        })

@socketio.on('virtual_remote_joystick')
def on_virtual_remote_joystick(data):
    """接收摇杆数据"""
    stick = data.get('stick')
    x = float(data.get('x', 0))
    y = float(data.get('y', 0))
    virtual_remote_publisher.state.set_joystick(stick, x, y)

@socketio.on('virtual_remote_button_down')
def on_virtual_remote_button_down(data):
    name = data.get('name')
    print(f"[VirtualRemote] 按键按下: {name}")
    virtual_remote_publisher.state.set_button(name, True)

@socketio.on('virtual_remote_button_up')
def on_virtual_remote_button_up(data):
    name = data.get('name')
    print(f"[VirtualRemote] 按键释放: {name}")
    virtual_remote_publisher.state.set_button(name, False)

@socketio.on('virtual_remote_emergency_stop')
def on_virtual_remote_emergency_stop():
    print("[VirtualRemote] 紧急停止!")
    virtual_remote_publisher.state.reset()
    emit('virtual_remote_emergency_ack', {'stopped': True}, broadcast=True)

@socketio.on('virtual_remote_reset')
def on_virtual_remote_reset():
    virtual_remote_publisher.state.reset()
    emit('virtual_remote_status', virtual_remote_publisher.get_status())


# ============ 键盘控制 WebSocket 事件 ============

@socketio.on('keyboard_enable')
def on_keyboard_enable():
    """启用键盘控制"""
    success, message = keyboard_controller.enable()
    emit('keyboard_result', {'success': success, 'message': message})
    if success:
        emit('keyboard_status', keyboard_controller.get_status())

@socketio.on('keyboard_disable')
def on_keyboard_disable():
    """禁用键盘控制"""
    success, message = keyboard_controller.disable()
    emit('keyboard_result', {'success': success, 'message': message})
    emit('keyboard_status', keyboard_controller.get_status())

@socketio.on('keydown')
def on_keydown(data):
    """按键按下"""
    key = data.get('key', '')
    result, message = keyboard_controller.process_key(key)
    emit('keydown_result', {'key': key, 'result': result, 'message': message})
    if result:
        emit('keyboard_status', keyboard_controller.get_status())

@socketio.on('keyup')
def on_keyup(data):
    """按键松开"""
    key = data.get('key', '')
    keyboard_controller.release_key(key)

@socketio.on('keyboard_get_status')
def on_keyboard_get_status():
    """获取键盘控制状态"""
    emit('keyboard_status', keyboard_controller.get_status())


# ============ 语音动作 WebSocket 事件 ============
@socketio.on('voice_action_execute')
def on_voice_action_execute(data):
    """执行语音+动作组合"""
    text = data.get('text', '').strip()
    action_id = data.get('action_id')
    auto_reset = data.get('auto_reset', True)

    emit('voice_action_status', {'status': 'executing', 'message': '正在执行...'})

    # 在后台线程中执行（避免阻塞WebSocket）
    def do_execute():
        try:
            success, result = voice_action_controller.perform_interaction(text, action_id, auto_reset)
            if success:
                emit('voice_action_status', {
                    'status': 'completed',
                    'results': result,
                    'message': '组合执行完成'
                })
            else:
                emit('voice_action_status', {
                    'status': 'error',
                    'message': str(result)
                })
        except Exception as e:
            emit('voice_action_status', {
                'status': 'error',
                'message': f'执行异常: {e}'
            })

    threading.Thread(target=do_execute, daemon=True).start()


@socketio.on('voice_speak_only')
def on_voice_speak_only(data):
    """仅播放语音"""
    text = data.get('text', '').strip()
    if not text:
        emit('voice_action_status', {'status': 'error', 'message': '语音内容为空'})
        return

    def do_speak():
        try:
            success, msg = voice_action_controller.speak(text)
            emit('voice_action_status', {
                'status': 'completed' if success else 'error',
                'step': 'voice',
                'message': msg
            })
        except Exception as e:
            emit('voice_action_status', {'status': 'error', 'message': f'异常: {e}'})

    threading.Thread(target=do_speak, daemon=True).start()


@socketio.on('voice_action_only')
def on_voice_action_only(data):
    """仅执行动作"""
    action_id = data.get('action_id')
    if action_id is None or action_id == -1:
        emit('voice_action_status', {'status': 'error', 'message': '请选择动作'})
        return

    def do_action():
        try:
            success, msg = voice_action_controller.execute_action(action_id)
            emit('voice_action_status', {
                'status': 'completed' if success else 'error',
                'step': 'action',
                'message': msg
            })
        except Exception as e:
            emit('voice_action_status', {'status': 'error', 'message': f'异常: {e}'})

    threading.Thread(target=do_action, daemon=True).start()


@socketio.on('voice_reset_arm')
def on_voice_reset_arm():
    """复位手臂"""
    def do_reset():
        try:
            success, msg = voice_action_controller.reset_arm()
            emit('voice_action_status', {
                'status': 'completed' if success else 'error',
                'step': 'reset',
                'message': msg
            })
        except Exception as e:
            emit('voice_action_status', {'status': 'error', 'message': f'异常: {e}'})

    threading.Thread(target=do_reset, daemon=True).start()

if __name__ == '__main__':
    import sys
    
    network_interface = 'eth0'
    if len(sys.argv) > 1:
        network_interface = sys.argv[1]
    
    print(f"🚀 启动Web控制服务器...")
    print(f"📡 网络接口: {network_interface}")
    print(f"🌐 访问地址: http://0.0.0.0:5000")
    
    # 虚拟遥控器独立初始化（不依赖init_clients，确保始终可用）
    virtual_remote_publisher.init_dds(network_interface)
    
    # 初始化SDK客户端
    init_clients(network_interface)
    
    # 启动Flask服务器
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)

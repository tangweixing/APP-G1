# Unitree G1 导航与语音助手项目 (WK)

本项目是在宇树 G1 人形机器人平台上，实现 **3D激光SLAM建图、自主导航、语音交互与运动控制** 的集成解决方案。

项目核心功能：
- 基于 FAST-LIO2 的3D激光里程计与建图
- 离线点云地图定位与重定位
- 2D栅格地图导航（支持 TEB 局部规划器）
- 自主导航、动态路径规划（支持 TEB 局部规划器）
- 集成语音助手，支持语音指令控制机器人运动
- 内置动作接口，可调用宇树内置动作、自己训练的舞蹈和动作
- 内置多个运动控制算法（含 MPC、自适应MPC、PID、开环 控制）

---

## 目录

- [项目结构](#项目结构)
WK/
├── G1Nav2D/ # ROS 导航核心工作空间
│ ├── src/
│ │ ├── fastlio2/ # FAST-LIO2 SLAM 核心包
│ │ ├── livox_ros_driver2/ # Livox 激光雷达驱动
│ │ ├── movebase/ # 导航栈配置（TEB规划器等）
│ │ ├── pointcloud_to_laserscan/ # 点云转激光扫描
│ │ ├── ros_map_edit/ # RViz 地图编辑插件
│ │ ├── tool/ # 点云处理、路径记录等工具
│ │ └── velocity_smoother_ema/ # 速度平滑器
│ └── …
├── PythonProject/ # 上层应用：语音助手与导航脚本
│ ├── py-xiaozhi-main/ # 语音助手（小智）集成
│ ├── daohang/ # 特定场景导航脚本（电梯、卫生间）
│ └── point_nav/ # 点对点导航示例
└── unitree_sdk2_python/ # 宇树机器人 Python SDK 
└── example/g1/high_level/ # G1 高级控制示例（MPC等 还有自定义导航点发布和导航讲解

- [环境依赖](#环境依赖)

---

## 环境依赖

### 硬件环境
- 宇树 G1 人形机器人
- Livox MID360 激光雷达
- 计算平台（机器人自带 ARM 板或外部 PC）

### 软件环境
- Ubuntu 20.04
- ROS Noetic
- Python 3.8+
- 依赖库：Eigen3, PCL, Open3D, Livox-SDK2 等

---

## 快速开始

### 1. 克隆仓库
```bash

git clone https://github.com/Dailywatero/WK.git

cd WK
```

### 2. 安装 Livox SDK2
```bash
cd 

sudo apt install cmake

git clone https://github.com/Livox-SDK/Livox-SDK2.git

cd Livox-SDK2

mkdir build && cd build

cmake … && make -j

sudo make install
```

### 3. 修改雷达 IP 及地图路径

1. 修改本机与雷达 IP：
```bash
cd WK/G1Nav2D/src/livox_ros_driver2/config

gedit MID360_config.json
```
根据你的网络环境修改 “lidar_configs” 里的雷达 IP 和 “host_net_info” 里的本机 IP
雷达ip一般不用修改：192.168.123.120；

```bash
#修改下面的四个ip为你自己的
"host_net_info" : {
      "cmd_data_ip" : "192.168.123.164",
      "cmd_data_port": 56101,
      "push_msg_ip": "192.168.123.164",
      "push_msg_port": 56201,
      "point_data_ip": "192.168.123.164",
      "point_data_port": 56301,
      "imu_data_ip" : "192.168.123.164",
      "imu_data_port": 56401,
      "log_data_ip" : "",
      "log_data_port": 56501
```

用ifconfig查自己的ip，要在同一网段下


2. 修改地图保存路径：
```bash
cd WK/G1Nav2D/src/fastlio2/src

gedit map_builder_node.cpp
```
将文件中地图保存路径（如 /home/water/map/）改为你自己的路径

### 4. 安装相关依赖
tf2_sensor_msgs
```bash
sudo apt-get update

sudo apt-get install ros-noetic-tf2-sensor-msgs
```

更新环境
```bash
source /opt/ros/noetic/setup.bash
```
如果遇到安装中源的问题换个源就可以解决


### 5. 编译 ROS 工作空间
```bash
cd WK/G1Nav2D
```
1.最开始建议清除所有的build中间文件
2.先单独编译 livox_ros_driver2 和 fastlio，避免消息头文件找不到
```bash
catkin_make -DROS_EDITION=ROS1 --pkg livox_ros_driver2

#这一步可能会有很多头文件或者依赖缺失的问题，如缺少GTSAM，根据终端报错去安装对应的文件即可

#编译ok后用下面这个命令看是否有CustomMsg.h头文件，有就ok
ls devel/include/livox_ros_driver2

#随时可以用下面命令刷新环境，或者写到.bashrc里面，双ROS2环境记得切换或注释
source /opt/ros/noetic/setup.bash


catkin_make -DROS_EDITION=ROS1 --pkg fastlio -j4

#整体编译

catkin_make

#如果不行，用这个命令
catkin_make -DROS_EDITION=ROS1

source devel/setup.bash
```

### 5. 安装导航相关依赖
```bash
sudo apt install ros-noetic-teb-local-planner
ros-noetic-global-planner
ros-noetic-costmap-server
```

### 6. 安装宇树运动接口功能包
unitree_sdk2_python

先安装cyclonedds 
```bash
git clone https://github.com/eclipse-cyclonedds/cyclonedds -b releases/0.10.x 
cd cyclonedds && mkdir build install && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=../install
cmake --build . --target install
```

设置 `CYCLONEDDS_HOME` 为刚刚编译好的 cyclonedds 所在路径，再安装 unitree_sdk2_python
```bash
export CYCLONEDDS_HOME="/home/water/WK/unitree_sdk2_python/cyclonedds/install"
pip3 install -e .

```
```bash
echo $CYCLONEDDS_HOME
echo $LD_LIBRARY_PATH
```
添加 cyclonedds 到 ~/.bashrc，然后 source ~/.bashrc

---

## 使用说明

### 1. 建图与保存地图

**建图：**
```bash
cd ~/tang/WK/G1Nav2D

source devel/setup.bash

roslaunch fastlio mapping.launch
```

**保存地图：**

新开终端：
```bash
cd ~/tang/WK/G1Nav2D

source devel/setup.bash

rosrun map_server map_saver map:=/projected_map -f /home/unitree/tang/map/mymap
```

> ⚠️ **重要**：上面的 `map_server map_saver` 命令**只保存 2D 栅格地图**（pgm + yaml），**不会保存 FAST-LIO 的 3D 点云地图**！
> 
> 重定位（`/slam_reloc`）**必须使用 3D 点云地图**（.pcd），需要**额外**执行以下命令保存 PCD：

```bash
cd ~/tang/WK/G1Nav2D

source devel/setup.bash
# 方式 1：调用 /save_map 服务（推荐，需要 mapping.launch 在运行）
# 注意：resolution=1.0 是标志位，会同时保存主地图和地面点云地图
# 主地图保存为 map.pcd，地面地图自动保存为 map_ground.pcd
# 必须用 YAML flow mapping 语法 {key: val, key: val}（整个用 { } 包裹）
rosservice call /save_map "{save_path: '/home/unitree/tang/WK/G1Nav2D/src/fastlio2/PCD/map.pcd', resolution: 1.0}"
# 等价于上面一条命令，会同时生成：
#   - /home/unitree/tang/WK/G1Nav2D/src/fastlio2/PCD/map.pcd
#   - /home/unitree/tang/WK/G1Nav2D/src/fastlio2/PCD/map_ground.pcd

# 方式 2：直接 Ctrl+C 关闭 mapping.launch，会自动保存到 /tmp/
# 然后手动复制：
cp /tmp/map.pcd /home/unitree/tang/WK/G1Nav2D/src/fastlio2/PCD/map.pcd
cp /tmp/ground_map.pcd /home/unitree/tang/WK/G1Nav2D/src/fastlio2/PCD/ground_map.pcd

```

### 2. 编辑地图
```bash
source devel/setup.bash

roslaunch ros_map_edit map_edit.launch
```

下载photogimp.desktop
在里面编辑pgm地图文件

### 3. 启动导航

1. 修改地图加载路径：
```bash
cd /home/unitree/tang/WK/G1Nav2D/src/fastlio2/launch

gedit gridmap_load.launch
```
修改 2dmap_file 参数为你保存的地图路径，例如：
<arg name="2dmap_file" default="/home/你的用户名/map/mymap.yaml" />

2. 启动导航：
```bash
cd ~/tang/WK/G1Nav2D

source devel/setup.bash 

roslaunch fastlio navigation.launch
```
3. 初始重定位（如有需要）：
cd /home/unitree/tang/WK/G1Nav2D/
catkin_make -DCATKIN_WHITELIST_PACKAGES="fastlio2"
source devel/setup.bash
```bash
rosservice call /slam_reloc "{pcd_path: '/home/unitree/tang/WK/G1Nav2D/src/fastlio2/PCD/map.pcd', x: 0.0, y: 0.0, z: 0.0, roll: 0.0, pitch: 0.0, yaw: 0.0}"

```

在 RViz 中确认点云与地图是否配准良好。
### 4. 运动控制（G1）

参考宇树官方文档安装 `unitree_sdk2_python`：
```bash
cd ~/tang/WK/unitree_sdk2_python/example/g1/high_level
#提供了多种可选择的运控

#基础的MPC控制
g1_control_mpc.py

#速度较快的mpc
g1_control_mpc_fast.py

#行走稳定的mpc
g1_control_mpc_stable.py

#自适应mpc
g1_control_mpc_stable_fast.py

#纯开环
g1_control_openloop.py

#闭环PID
g1_control_pid.py

#使用下方代码替换文件名和网口名即可
python3.9 g1_control_mpc_stable_fast.py eth0 # 或其他 g1_control_*.py

```

### 5. 自主导航（带动态避障）
```bash
cd ~/tang/WK/unitree_sdk2_python/example/g1/high_level
#基础导航讲解程序，替换文字和坐标位置即可实现讲解
multi_nav.py

#提供讲解暂停和暂停时实现动作：如跳舞，挥手以及自定义内置动作，预留接口
#也可以选择讲解替换成人工讲解，利用键盘交互
multi_onefloor_nav_addkey_action.py

#使用下方代码替换文件名和网口名即可
python3.9 multi_nav_hys.py eth0
```

### 可选1. 动作执行
1.g1_action.py系列文件为动作文件，可以让机器人按着预设动作运动
2.可内置到导航程序中，修改对应的程序名，已预留接口

### 可选2. 语音交互导航（基于 py-xiaozhi）

详细配置请参考 `PythonProject/py-xiaozhi-main/README.md`，这里给出关键步骤。

**安装依赖：**
```bash
cd WK/PythonProject/py-xiaozhi-main

pip install -r requirements.txt
```

**语音导航到目标点（简易版）：**

1. 在 `PythonProject/point_nav/point2.py` 中修改目标点坐标（文件最底部）。
2. 全局搜索“电梯”，根据需要替换为“卧室”、“卫生间”等关键词，并修改对应坐标。

**语音导航到目标点（MCP 版）：**

1. 在 `PythonProject/py-xiaozhi-main/src/application.py` 中添加/修改关键词与对应的 MCP 服务。
2. 在 `PythonProject/py-xiaozhi-main/src/mcp/mcp_server.py` 中注册 MCP 服务。
3. 在 `PythonProject/py-xiaozhi-main/src/mcp/tools/daohang_dianti/tools.py` 中配置拉起的 Python 程序及解释器路径。
4. 在 `PythonProject/daohang/daohang-dianti.py` 中修改目标点坐标。

**启动语音程序：**
```bash
cd ~/tang/WK/PythonProject/py-xiaozhi-main
python3.9 main.py
```

> 实现语音交互导航需要同时启动：语音程序、运控程序、导航程序。

---


VNC连接显示rviz
vncserver -kill :2 
vncserver :2 -geometry 1920x1080 -depth 24 -xstartup /usr/bin/xterm -localhost no
vncviewer 192.168.2.248:5902 -FullScreen

网页控制（前端显示rviz通过noVNC显示）
cd /home/unitree/tang/WK/unitree_sdk2_python/example/g1/high_level/web_arm_control
source /opt/ros/noetic/setup.bash
source ~/tang/WK/G1Nav2D/devel/setup.bash
python3.8 app.py eth0
## 核心模块说明

### 1. G1Nav2D (导航核心)
- `fastlio2/`: 实现 3D SLAM 与定位。
- `movebase/`: 集成 ROS navigation stack，使用 TEB 局部规划器进行避障与路径规划。
- `ros_map_edit/`: 提供 RViz 插件，方便编辑和修正 2D 栅格地图。

### 2. PythonProject (上层应用)
- `py-xiaozhi-main/`: 一个功能完整的语音助手项目，集成了大语言模型、物联网控制等功能，通过语音指令控制机器人。
- `point_nav/`, `daohang/`: 封装好的导航任务脚本，实现“去电梯口”、“去卫生间”等特定场景的自主导航。

### 3. unitree_sdk2_python (运动控制)
提供对宇树 G1 机器人的底层和高级控制接口，本项目重点使用了其中的 MPC 控制示例来实现平稳的运动控制。

---

## 常见问题

**Q: 编译时出现 `CustomMsg.h` 或 `SlamReLoc.h` 找不到？**  
A: 需要先单独编译消息生成包，参考“快速开始”中的编译顺序。

**Q: 如何修改地图路径？**  
A: 在 `G1Nav2D/src/fastlio2/launch/gridmap_load.launch` 中修改 `2dmap_file` 参数。
---

## 致谢

- [FAST_LIO](https://github.com/hku-mars/FAST_LIO)
- [Livox-SDK2](https://github.com/Livox-SDK/Livox-SDK2) 及 `livox_ros_driver2`
- [ros_map_edit](https://github.com/你的参考链接)
- [py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi)
- 宇树科技 Unitree
- 以及所有开源项目贡献者。

---

## License

本项目仅供学习交流，请遵守相关开源协议。

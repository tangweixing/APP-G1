#!/bin/bash
# Unitree G1 Web Arm Control 服务启动脚本
# 解决 systemd 环境下 conda 环境缺失问题

# 切换工作目录
cd /home/unitree/tang/WK/unitree_sdk2_python/example/g1/high_level/web_arm_control

# ===== 设置 SDK 环境变量（关键！systemd 不读 .bashrc）=====
export PYTHONPATH="/home/unitree/tang/WK/unitree_sdk2_python:${PYTHONPATH:-}"
export LD_LIBRARY_PATH="/home/unitree/tang/cyclonedds/install/lib:${LD_LIBRARY_PATH:-}"
export PYTHONUNBUFFERED=1

# Source ROS 环境（导航子进程需要）
source /opt/ros/noetic/setup.bash
source ~/tang/WK/G1Nav2D/devel/setup.bash

# 启动 Flask 服务（使用 exec 让 systemd 正确追踪进程）
exec python3.8 app.py eth0
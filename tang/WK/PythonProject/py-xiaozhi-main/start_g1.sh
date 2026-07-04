#!/bin/bash
# G1小智助手启动脚本
# 用于开机自启动

# 设置工作目录
cd /home/unitree/tang/WK/PythonProject/py-xiaozhi-main

# 设置Python路径（使用Python 3.9）
PYTHON=/usr/bin/python3.9

# 设置环境变量
export DISPLAY=:0  # 如果需要GUI显示
export XDG_RUNTIME_DIR=/run/user/1000

# 日志文件
LOG_FILE=/home/unitree/tang/WK/PythonProject/py-xiaozhi-main/logs/startup.log

# 创建日志目录
mkdir -p /home/unitree/tang/WK/PythonProject/py-xiaozhi-main/logs

# 记录启动时间
echo "========================================" >> $LOG_FILE
echo "启动时间: $(date)" >> $LOG_FILE
echo "工作目录: $(pwd)" >> $LOG_FILE
echo "Python路径: $PYTHON" >> $LOG_FILE
echo "========================================" >> $LOG_FILE

# 启动应用（无GUI模式，使用唤醒词）
$PYTHON main.py --mode cli --protocol websocket >> $LOG_FILE 2>&1

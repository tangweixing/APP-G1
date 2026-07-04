#!/bin/bash

# 设置ROS环境
source /opt/ros/noetic/setup.bash

# 设置工作空间
cd /home/ln/ros_ws/cursor_ws
export ROS_PACKAGE_PATH=$ROS_PACKAGE_PATH:/home/ln/ros_ws/cursor_ws/src

# 启动roscore如果没有运行
if ! pgrep -x "roscore" > /dev/null; then
    echo "Starting roscore..."
    roscore &
    sleep 3
fi

# 启动map_server
echo "Starting map server..."
rosrun map_server map_server /home/ln/ros_ws/cursor_ws/src/ros_map_edit/maps/sample_map.yaml &
sleep 2

# 启动RViz
echo "Starting RViz..."
rviz -d /home/ln/ros_ws/cursor_ws/src/ros_map_edit/config/map_edit.rviz

echo "Done" 
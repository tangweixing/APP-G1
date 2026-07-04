#!/bin/bash

echo "开始测试橡皮擦功能..."

# 设置ROS环境
source /opt/ros/noetic/setup.bash
source devel/setup.bash

echo "1. 启动roscore..."
roscore &
ROSCORE_PID=$!
sleep 3

echo "2. 启动地图服务器..."
rosrun map_server map_server src/ros_map_edit/maps/sample_map.yaml &
MAP_SERVER_PID=$!
sleep 2

echo "3. 检查地图话题..."
echo "原始地图话题信息:"
rostopic info /map

echo "4. 监控编辑后的地图话题..."
echo "启动地图话题监控 (在后台运行)..."
rostopic echo /map_edited -n 1 &
MONITOR_PID=$!

echo "5. 启动RViz..."
echo "请在RViz中:"
echo "- 选择MapEraserTool工具"
echo "- 左键画黑色，右键画白色"
echo "- 观察编辑后的地图是否实时更新"
echo ""
echo "启动RViz..."
rviz -d src/ros_map_edit/config/map_edit.rviz

echo "清理进程..."
kill $ROSCORE_PID $MAP_SERVER_PID $MONITOR_PID 2>/dev/null
echo "测试完成!" 
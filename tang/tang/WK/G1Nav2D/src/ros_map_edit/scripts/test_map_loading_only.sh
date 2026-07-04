#!/bin/bash

# 简单的地图加载测试脚本
echo "=== 测试地图加载功能 ==="

# 设置ROS环境
source devel/setup.bash

# 启动roscore
echo "1. 启动 roscore..."
roscore &
ROSCORE_PID=$!
sleep 3

echo "2. 启动 RViz（最小化界面）..."
# 启动RViz但不显示，只为了测试插件加载
timeout 10 rviz -d src/ros_map_edit/config/map_edit.rviz &
RVIZ_PID=$!

echo "3. 等待RViz启动..."
sleep 8

echo "4. 检查ROS话题列表..."
rostopic list | grep -E "(map|virtual|region)"

echo ""
echo "5. 手动测试地图发布..."
echo "发布测试地图到/map话题..."

# 使用map_server发布测试地图进行对比
echo "使用map_server发布测试地图："
timeout 5 rosrun map_server map_server src/ros_map_edit/maps/test.yaml &
MAP_SERVER_PID=$!

sleep 3

echo ""
echo "6. 检查地图话题内容..."
echo "Map话题信息："
timeout 3 rostopic echo /map/info || echo "无地图信息"

echo ""
echo "7. 检查地图数据..."
echo "Map话题数据（前100字节）："
timeout 2 rostopic echo /map/data | head -20 || echo "无地图数据"

echo ""
echo "=== 测试完成 ==="
echo "如果看到地图信息和数据，说明地图加载正常"
echo "如果没有看到，请检查："
echo "1. YAML文件格式是否正确"
echo "2. PGM文件是否存在"
echo "3. 文件路径是否正确"

# 清理
sleep 2
echo "清理进程..."
kill $MAP_SERVER_PID 2>/dev/null
kill $RVIZ_PID 2>/dev/null  
kill $ROSCORE_PID 2>/dev/null

echo "测试结束" 
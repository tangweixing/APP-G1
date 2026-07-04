#!/bin/bash

# 调试地图加载和虚拟墙发布的脚本
echo "=== ROS Map Edit 调试启动脚本 ==="

# 启动 roscore
echo "1. 启动 roscore..."
roscore &
ROSCORE_PID=$!
sleep 3

echo "2. 启动 RViz..."
rviz -d ../config/map_edit.rviz &
RVIZ_PID=$!
sleep 5

echo "3. 等待RViz完全启动..."
sleep 3

echo "4. 检查ROS话题..."
echo "当前可用的话题："
rostopic list | grep -E "(map|virtual|region|marker)"

echo ""
echo "5. 监控地图话题..."
echo "尝试获取地图话题信息："
timeout 2 rostopic echo /map -n 1 || echo "地图话题暂无数据"

echo ""
echo "6. 监控虚拟墙话题..."
echo "尝试获取虚拟墙话题信息："
timeout 2 rostopic echo /virtual_walls_markers -n 1 || echo "虚拟墙话题暂无数据"

echo ""
echo "7. 监控区域话题..."
echo "尝试获取区域话题信息："
timeout 2 rostopic echo /region_markers -n 1 || echo "区域话题暂无数据"

echo ""
echo "=== 调试环境已启动 ==="
echo "使用说明："
echo "1. 在MapEditPanel中点击'打开地图'按钮选择地图文件"
echo "2. 观察终端输出的调试信息"
echo "3. 检查RViz中的Map显示层"
echo "4. 检查虚拟墙和区域是否显示"
echo ""
echo "实时监控命令："
echo "  rostopic hz /map                    # 检查地图发布频率"
echo "  rostopic hz /virtual_walls_markers  # 检查虚拟墙发布频率" 
echo "  rostopic hz /region_markers         # 检查区域发布频率"
echo "  rosnode info /rviz                  # 检查RViz节点信息"
echo ""
echo "按 Ctrl+C 停止监控..."

# 持续监控话题
while true; do
    echo "=== $(date) ==="
    echo "Map话题状态:"
    rostopic hz /map --window=5 | head -1 || echo "  无数据"
    
    echo "VirtualWalls话题状态:"
    rostopic hz /virtual_walls_markers --window=5 | head -1 || echo "  无数据"
    
    echo "Regions话题状态:"
    rostopic hz /region_markers --window=5 | head -1 || echo "  无数据"
    
    echo "--------------------"
    sleep 10
done 
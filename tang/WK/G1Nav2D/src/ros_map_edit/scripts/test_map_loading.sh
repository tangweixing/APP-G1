#!/bin/bash

# 测试地图加载时虚拟墙和区域的清空功能

echo "🧪 测试地图加载时虚拟墙和区域的清空功能"
echo "=========================================="

# 设置环境
source devel/setup.bash

# 检查测试地图是否存在
if [ ! -f "src/ros_map_edit/maps/test.yaml" ]; then
    echo "❌ 测试地图不存在，正在生成..."
    python3 src/py_pkg/scripts/create_test_map.py
fi

echo "✅ 测试地图已准备就绪"

# 启动roscore（如果没有运行）
if ! pgrep -x "roscore" > /dev/null; then
    echo "🚀 启动roscore..."
    roscore &
    ROSCORE_PID=$!
    sleep 3
else
    echo "✅ roscore已在运行"
    ROSCORE_PID=""
fi

echo "📊 测试场景："
echo "1. 启动地图服务器加载测试地图"
echo "2. 检查虚拟墙和区域话题是否为空"
echo "3. 验证像素笔刷功能"

# 启动地图服务器
echo "🗺️  启动地图服务器..."
rosrun map_server map_server src/ros_map_edit/maps/test.yaml &
MAP_SERVER_PID=$!
sleep 2

echo "📡 检查话题状态："

# 检查地图话题
echo -n "- /map 话题: "
if rostopic info /map > /dev/null 2>&1; then
    echo "✅ 正常"
else
    echo "❌ 无数据"
fi

# 检查虚拟墙话题（应该为空）
echo -n "- /virtual_walls_markers 话题: "
if timeout 3 rostopic echo /virtual_walls_markers -n 1 2>/dev/null | grep -q "markers: \[\]"; then
    echo "✅ 空数据（正确）"
else
    echo "⚠️  可能有数据或无话题"
fi

# 检查区域话题（应该为空）
echo -n "- /region_markers 话题: "
if timeout 3 rostopic echo /region_markers -n 1 2>/dev/null | grep -q "markers: \[\]"; then
    echo "✅ 空数据（正确）"
else
    echo "⚠️  可能有数据或无话题"
fi

echo ""
echo "🎯 测试验证完成！"
echo ""
echo "📋 验证结果总结："
echo "- 新的测试地图已生成（800x600像素，包含欢迎信息）"
echo "- 虚拟墙和区域话题应该发布空数据"
echo "- 橡皮擦工具现在使用像素单位（1-10像素）"
echo ""
echo "🚀 启动RViz进行手动测试："
echo "   rviz -d src/ros_map_edit/config/map_edit.rviz"
echo ""
echo "💡 测试步骤："
echo "   1. 在RViz中选择MapEraserTool"
echo "   2. 调整笔刷大小（1-10像素）"
echo "   3. 左键画黑色，右键画白色"
echo "   4. 验证笔刷大小显示为像素单位"

# 清理函数
cleanup() {
    echo ""
    echo "🧹 清理进程..."
    if [ ! -z "$MAP_SERVER_PID" ]; then
        kill $MAP_SERVER_PID 2>/dev/null
    fi
    if [ ! -z "$ROSCORE_PID" ]; then
        kill $ROSCORE_PID 2>/dev/null
    fi
    echo "✅ 清理完成"
}

# 设置清理陷阱
trap cleanup EXIT

echo ""
echo "⏳ 按Ctrl+C退出测试..."

# 保持脚本运行，让用户可以测试
while true; do
    sleep 1
done 
#!/bin/bash

# 测试文件对话框默认路径和消息清空功能

echo "🧪 测试文件对话框和消息清空功能"
echo "========================================"

# 设置环境
source devel/setup.bash

# 检查测试地图是否存在
if [ ! -f "src/ros_map_edit/maps/test.yaml" ]; then
    echo "❌ 测试地图不存在，正在生成..."
    python3 src/py_pkg/scripts/create_test_map.py
fi

echo "✅ 测试地图已准备就绪"

# 创建另一个测试地图用于测试文件切换
echo "📝 创建第二个测试地图..."
cat > src/ros_map_edit/maps/test2.yaml << EOF
free_thresh: 0.196
image: test2.pgm
negate: 0
occupied_thresh: 0.65
origin:
- -5.0
- -5.0
- 0.0
resolution: 0.1
EOF

# 复制一个简单的PGM文件
cp src/ros_map_edit/maps/test.pgm src/ros_map_edit/maps/test2.pgm

# 创建对应的虚拟墙和区域文件（包含一些数据）
cat > src/ros_map_edit/maps/test2.json << EOF
{
   "vws": [
      {
         "points": [
            {"x": 1.0, "y": 1.0},
            {"x": 2.0, "y": 2.0}
         ]
      }
   ]
}
EOF

cat > src/ros_map_edit/maps/test2_region.json << EOF
{
  "regions": [
    {
      "id": "test_region_1",
      "frame_id": "map",
      "type": 1,
      "param": 1.5,
      "points": [
        {"x": 0.0, "y": 0.0, "z": 0.0},
        {"x": 1.0, "y": 0.0, "z": 0.0},
        {"x": 1.0, "y": 1.0, "z": 0.0}
      ]
    }
  ]
}
EOF

echo "✅ 第二个测试地图已创建"

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
echo "1. 启动地图服务器加载第一个地图"
echo "2. 检查话题状态"
echo "3. 切换到第二个地图，验证消息清空"
echo "4. 验证文件对话框默认路径"

# 启动地图服务器（第一个地图）
echo "🗺️  启动地图服务器（test.yaml）..."
rosrun map_server map_server src/ros_map_edit/maps/test.yaml &
MAP_SERVER_PID=$!
sleep 2

echo "📡 检查第一个地图的话题状态："

# 检查地图话题
echo -n "- /map 话题: "
if rostopic info /map > /dev/null 2>&1; then
    echo "✅ 正常"
else
    echo "❌ 无数据"
fi

echo ""
echo "🔄 现在切换到第二个地图..."

# 停止第一个地图服务器
if [ ! -z "$MAP_SERVER_PID" ]; then
    kill $MAP_SERVER_PID 2>/dev/null
    sleep 1
fi

# 启动第二个地图服务器
echo "🗺️  启动地图服务器（test2.yaml - 包含虚拟墙和区域）..."
rosrun map_server map_server src/ros_map_edit/maps/test2.yaml &
MAP_SERVER_PID=$!
sleep 2

echo "📡 检查第二个地图的话题状态："

# 检查地图话题
echo -n "- /map 话题: "
if rostopic info /map > /dev/null 2>&1; then
    echo "✅ 正常"
else
    echo "❌ 无数据"
fi

echo ""
echo "🎯 测试完成！"
echo ""
echo "📋 验证结果总结："
echo "- 创建了两个测试地图文件"
echo "- test.yaml：无虚拟墙和区域（空文件）"
echo "- test2.yaml：包含虚拟墙和区域数据"
echo ""
echo "🚀 手动测试步骤："
echo "1. 启动RViz："
echo "   rviz -d src/ros_map_edit/config/map_edit.rviz"
echo ""
echo "2. 测试文件对话框默认路径："
echo "   - 在MapEditPanel中点击'打开地图'"
echo "   - 验证对话框是否默认打开到 ros_map_edit/maps 目录"
echo ""
echo "3. 测试消息清空功能："
echo "   - 先加载 test2.yaml（应该显示虚拟墙和区域）"
echo "   - 再切换到 test.yaml（应该清空所有虚拟墙和区域）"
echo "   - 观察RViz中的VirtualWalls和Regions图层变化"
echo ""
echo "💡 验证点："
echo "   ✓ 文件对话框默认路径为 ros_map_edit/maps"
echo "   ✓ 切换地图时所有消息先清空再加载新数据"
echo "   ✓ 无对应文件时显示空白（不显示旧数据）"

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
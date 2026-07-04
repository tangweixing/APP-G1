#!/bin/bash

# 测试新地图的启动脚本 - 支持动态地图切换
echo "启动ROS Map Edit测试，支持动态地图切换"

# 检查地图文件是否存在
if [ ! -f "../maps/test.pgm" ]; then
    echo "测试地图不存在，需要手动创建"
    echo "请运行 python3 创建地图的脚本"
fi

# 启动 roscore
roscore &
ROSCORE_PID=$!
sleep 2

# 注意：不再启动独立的map_server，因为插件现在可以直接发布地图
echo "启动 RViz..."
rviz -d ../config/map_edit.rviz &
RVIZ_PID=$!

echo "测试环境已启动!"
echo "地图特点："
echo "- 包含'Welcome to ros_map_edit'文字"
echo "- 左上角有REINOVO logo"
echo "- 分辨率：0.05m/pixel"
echo "- 尺寸：480x640像素 (24x32米) - 已左旋90度"
echo ""
echo "新功能测试："
echo "1. 动态地图切换 - 使用'打开地图'按钮可以切换不同的地图文件"
echo "2. 虚拟墙工具 - 现在会自动加载保存的虚拟墙文件"
echo "3. 区域工具 - 现在会自动加载保存的区域文件"
echo "4. 橡皮擦工具 - 笔刷大小以米为单位显示"
echo ""
echo "使用说明："
echo "- 在MapEditPanel中点击'打开地图'按钮选择不同的YAML地图文件"
echo "- 插件会直接发布新地图到/map话题，无需重启map_server"
echo "- 支持YAML和PGM格式的地图文件"
echo ""
echo "按任意键停止所有进程..."
read -n 1

# 清理进程
echo "正在停止所有进程..."
kill $RVIZ_PID 2>/dev/null
kill $ROSCORE_PID 2>/dev/null

echo "测试完成!" 
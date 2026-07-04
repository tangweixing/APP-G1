#!/bin/bash

echo "测试保存功能..."

# 确保在正确的目录
cd /home/ln/ros_ws/cursor_ws

# 设置ROS环境
source /opt/ros/noetic/setup.bash
source devel/setup.bash

echo "1. 检查原始文件状态..."
echo "maps目录内容:"
ls -la src/ros_map_edit/maps/

echo -e "\n2. sample_map.json 内容:"
cat src/ros_map_edit/maps/sample_map.json

echo -e "\n3. sample_map_region.json 内容:"
cat src/ros_map_edit/maps/sample_map_region.json

echo -e "\n4. 现在请按以下步骤测试:"
echo "   - 启动系统: ./src/ros_map_edit/scripts/test_eraser.sh"
echo "   - 在RViz中使用各种工具编辑"
echo "   - 在MapEditPanel中点击'一键保存所有文件'"
echo "   - 然后重新运行此脚本查看文件变化"

echo -e "\n5. 如果您已经完成编辑和保存，按任意键继续检查结果..."
read -n 1 -s

echo -e "\n检查保存后的文件:"
echo "sample_map.json 内容:"
cat src/ros_map_edit/maps/sample_map.json

echo -e "\n\nsample_map_region.json 内容:"
cat src/ros_map_edit/maps/sample_map_region.json

echo -e "\n\n检查是否有新的PGM文件:"
ls -la src/ros_map_edit/maps/*.pgm

echo -e "\n测试完成!" 
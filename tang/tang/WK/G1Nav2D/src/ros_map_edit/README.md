# ROS Map Edit Plugin

一个用于RViz的地图编辑插件，支持虚拟墙绘制、区域标记和地图擦除功能。

![ros_map_edit Interface](images/ros_map_edit.png "ros_map_edit Interface")

## 项目构建

### 系统环境要求
Ubuntu 18.04 / 20.04
ROS Melodic / Noetic

```bash
sudo apt install -y \
  libyaml-cpp-dev \
  libopencv-dev \
  qtbase5-dev \
  qttools5-dev-tools \
  pkg-config
```

## 功能特点

### 🖤⚪ 黑白橡皮擦工具 (MapEraserTool)
- **左键**: 画黑色 (添加障碍物)
- **右键**: 画白色 (清除障碍物) 
- **拖拽**: 连续绘制
- **笔刷大小**: 1-10像素，可在属性面板调节

### 🧱 虚拟墙工具 (VirtualWallTool) 
- **限制**: 只能绘制两个点的墙体
- **左键**: 依次点击两个点创建墙体
- **右键**: 取消当前墙体绘制
- **自动完成**: 点击第二个点后自动完成墙体

### 📐 区域工具 (RegionTool)
- **左键**: 添加多边形顶点
- **右键**: 完成当前多边形区域
- **可视化**: 实时显示多边形填充和边界

### 💾 一键保存
- **统一保存**: 一个按钮保存所有文件
- **文件格式**:
  - `map.yaml` - 地图配置文件
  - `map.pgm` - 地图图像文件
  - `map.json` - 虚拟墙数据
  - `map_region.json` - 区域数据

## 安装和使用

### 1. 编译
```bash
cd ~/ros_ws/cursor_ws
catkin_make
source devel/setup.bash
```

### 2. 启动系统
```bash
# 启动编辑器
roslaunch ros_map_edit map_edit.launch

```

### 3. 使用工具

1. **在RViz工具栏中选择相应的工具**:
   - `MapEraserTool` - 黑白橡皮擦
   - `VirtualWallTool` - 虚拟墙绘制
   - `RegionTool` - 区域绘制

2. **编辑地图**:
   - 使用橡皮擦：左键画黑色，右键画白色
   - 绘制虚拟墙：左键点击两个点
   - 绘制区域：左键添加顶点，右键完成

3. **保存所有文件**:
   - 在`MapEditPanel`面板中输入地图名称
   - 点击"一键保存所有文件"按钮
   - 选择保存目录

## 文件格式

### 虚拟墙格式 (map.json)
```json
{
  "vws": [
    {
      "points": [
        {"x": 1.0, "y": 2.0},
        {"x": 3.0, "y": 4.0}
      ]
    }
  ]
}
```

### 区域格式 (map_region.json)  
```json
{
  "regions": [
    {
      "id": "region1",
      "frame_id": "map",
      "type": 0,
      "param": 1.0,
      "points": [
        {"x": 1.0, "y": 1.0, "z": 0.0},
        {"x": 2.0, "y": 1.0, "z": 0.0},
        {"x": 2.0, "y": 2.0, "z": 0.0}
      ]
    }
  ]
}
```

## 虚拟墙使用

详见./launch/map_server.launch
及./params/costmap_common_params.yaml
./params/global_costmap_params.yaml
./params/local_costmap_params.yaml

## 更新说明

### v2.0 简化版更新
- ✅ 橡皮擦改为直接左右键模式，无需属性面板选择
- ✅ 虚拟墙限制为两个点，自动完成
- ✅ 文件管理简化为一键保存所有文件
- ✅ 界面更加简洁易用

### 技术实现
- 基于RViz插件架构
- 使用Qt界面组件
- 支持实时可视化标记
- JSON格式数据存储

## 故障排除

1. **插件加载失败**: 确保已正确编译并source环境
2. **地图不显示**: 检查map_server是否正在运行
3. **保存失败**: 确保有写入权限并且地图话题正在发布

## 开发信息

- **ROS版本**: Noetic
- **Qt版本**: 5.x
- **依赖**: RViz, JsonCpp, OpenCV, tf2

## Authors

**Maintainer**:
- **LN**  
  Email: 825255961.com
- **REINOVO**

---
*最后更新: 2025年* 

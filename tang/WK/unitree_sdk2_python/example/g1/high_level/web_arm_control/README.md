# G1 机械臂 Web 控制界面

这是一个基于 Flask 的 Web 应用，用于通过浏览器控制宇树 G1 机器人的机械臂动作。

## 功能特性

- ✅ 可视化动作选择界面
- ✅ 实时动作执行状态反馈
- ✅ WebSocket 双向通信
- ✅ 操作日志记录
- ✅ 响应式设计（支持手机/平板）
- ✅ 16 种预设机械臂动作

## 快速开始

### 1. 安装依赖

```bash
cd /home/unitree/tang/WK/unitree_sdk2_python/example/g1/high_level/web_arm_control
pip3 install -r requirements.txt
```

### 2. 启动 Web 服务器

```bash
# 使用方法
./start_web_arm_test.sh <network_interface>

# 示例
./start_web_arm_test.sh eth0
```

如果不确定使用哪个网络接口，可以运行不带参数的脚本来查看可用接口：

```bash
./start_web_arm_test.sh
```

### 3. 访问 Web 界面

在浏览器中打开：
- 本地访问：`http://localhost:5000`
- 远程访问：`http://<机器人 IP>:5000`

## 可用动作列表

| ID | 动作名称 | 描述 |
|----|---------|------|
| 0 | release arm | 释放机械臂 |
| 1 | shake hand | 握手 |
| 2 | high five | 手举高，你好 |
| 3 | hug | 拥抱 |
| 4 | high wave | 拜拜 |
| 5 | clap | 拍手 |
| 6 | face wave | 手举低，你好 |
| 7 | left kiss | 飞吻 |
| 8 | heart | 比心 |
| 9 | right heart | 瞭望 |
| 10 | hands up | 要饭 |
| 11 | x-ray | 迪迦 |
| 12 | right hand up | 右手举起 |
| 13 | reject | 拒绝 1 |
| 14 | right kiss | 右手飞吻 |
| 15 | two-hand kiss | 双手飞吻 |

## 界面说明

### 状态栏
- 显示 WebSocket 连接状态
- 显示当前使用的网络接口
- 显示系统当前状态

### 动作卡片
- 点击任意动作卡片即可执行对应动作
- 执行中：卡片变为紫色渐变，显示加载动画
- 执行完成：卡片变为绿色
- 执行错误：卡片变为红色

### 操作日志
- 实时显示所有操作记录
- 支持清空日志
- 颜色区分不同类型的日志（信息/成功/错误/警告）

### 快捷操作
- **顺序执行所有动作**：按 ID 顺序执行所有 16 个动作
- **停止当前动作**：停止正在执行的动作（开发中）
- **刷新状态**：刷新系统状态信息

## 技术架构

```
┌─────────────┐     WebSocket     ┌─────────────┐
│   浏览器    │◄─────────────────►│   Flask     │
│  (前端界面) │                   │   (后端)    │
└─────────────┘                   └──────┬──────┘
                                         │
                                         │ unitree_sdk2_python
                                         │
                                  ┌──────▼──────┐
                                  │  G1 机器人  │
                                  │  (机械臂)   │
                                  └─────────────┘
```

## API 接口

### REST API

- `GET /api/actions` - 获取所有可用动作列表
- `GET /api/status` - 获取系统当前状态
- `POST /api/execute` - 执行指定动作

### WebSocket 事件

- `connect` - 客户端连接
- `disconnect` - 客户端断开
- `execute_action` - 执行动作请求
- `action_status` - 动作执行状态更新
- `system_message` - 系统消息

## 文件结构

```
web_arm_control/
├── app.py                          # Flask 后端应用
├── requirements.txt                # Python 依赖
├── start_web_arm_test.sh          # 启动脚本
├── README.md                      # 说明文档
└── templates/
    └── index.html                 # Web 前端界面
```

## 常见问题

### Q: 无法连接到机器人？
A: 请确保：
1. 网络接口名称正确
2. 机器人与计算机在同一网络
3. CycloneDDS 已正确配置

### Q: 动作执行失败？
A: 请检查：
1. 机器人是否已上电
2. 机械臂是否处于可控制状态
3. 周围是否有障碍物

### Q: 网页无法访问？
A: 请确认：
1. Flask 服务已启动
2. 端口 5000 未被防火墙阻止
3. 使用正确的 IP 地址访问

## 安全提示

⚠️ **重要安全注意事项：**

1. 执行动作前，确保机械臂周围没有障碍物
2. 不要在机器人附近放置易碎物品
3. 某些动作可能需要较大空间，请确保周围环境安全
4. 如发现异常，立即停止动作并检查

## 扩展开发

### 添加新动作

1. 在 `app.py` 的 `action_list` 中添加新动作定义
2. 在 `execute_action_internal` 函数中添加动作执行逻辑
3. 前端会自动显示新动作卡片

### 自定义界面

修改 `templates/index.html` 中的 CSS 和 JavaScript 来自定义界面样式和功能。

## 许可证

本项目仅供学习交流使用。

## 致谢

- [Unitree Robotics](https://www.unitree.com/)
- [Flask](https://flask.palletsprojects.com/)
- [Socket.IO](https://socket.io/)

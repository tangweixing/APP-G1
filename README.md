# APP-G1

宇树 G1 人形机器人 + 小智 AI 语音助手 + uni-app 控制前端的完整方案。

唤醒词 **「小野」**，语音驱动 G1 做动作、导航、人脸识别；前端 App 远程控制与配置。

---

## 目录结构

```
APP-G1/
├── app-g1/                          # uni-app 前端（小野 AI 模块，手机/平板控制端）
├── APK/                             # 前端构建产物（.apk）
├── tang/
│   ├── WK/
│   │   ├── PythonProject/py-xiaozhi-main/   # ★ 核心：py-xiaozhi 后端 + G1 适配
│   │   ├── unitree_sdk2_python/             # 宇树 G1 官方 SDK（动作/音频/导航示例）
│   │   └── G1Nav2D/                         # 2D 导航（fastlio2 + 点云地图 .pcd）
│   ├── noVNC/                       # 浏览器远程 VNC
│   ├── cyclonedds/                  # DDS 中间件（G1 通信底层）
│   ├── Livox-SDK2/                  # Livox 激光雷达 SDK
│   └── tang/                        # 备份副本（与上层重复，待清理）
└── .gitignore
```

> `tang/tang/` 是历史遗留的重复副本，两份内容基本一致，后续建议清理。
>
> ⚠️ **本仓库的 `tang/` 是备份**。实际运行的代码在机器人 `unitree@192.168.4.53` 上（`/home/unitree/tang/WK/PythonProject/py-xiaozhi-main`），改代码请到机器人上改，再 rsync 同步回本仓库。

---

## 核心能力（py-xiaozhi 后端）

后端代码在 `tang/WK/PythonProject/py-xiaozhi-main/`，在原版 py-xiaozhi 基础上接入 G1：

### 1. G1 音频系统
- **TTS 语音合成**：中/英文，本地离线
- **音量控制**：0–100 级
- **LED 灯带**：RGB 颜色控制（调用间隔需 >200ms）
- **四麦阵列**：16kHz / 单通道 / 16bit，支持声源定位

### 2. 语音唤醒
- 唤醒词 **「小野」**（Vosk 离线模型 `models/vosk-model-small-cn-0.22`）
- 配置项：`WAKE_WORD_OPTIONS`

### 3. G1 手臂动作（MCP 工具）

底层调 `unitree_sdk2_python/example/g1/high_level/g1_arm_action_example.py`，传 `网络接口 + actionId` 执行。G1 共 **16 个预设动作（ID 0–15），现已全部接入 MCP**：

| ID | 动作 | 工具 | 备注 |
|----|------|------|------|
| 0 | 释放手臂 release arm | — | 各动作执行后自动调用归位 |
| 1 | 握手 shake hand | `handshake` | |
| 2 | 击掌 high five | `jizhang` | |
| 3 | 拥抱 hug | `yongbao` | |
| 4 | 拜拜 high wave | `baibai` | |
| 5 | 鼓掌 clap | `guzhang` | |
| 6 | 你好 face wave | `nihao` | 附带人脸识别 |
| 7 | 飞吻 left kiss | `qin` | |
| 8 | 比心 heart | `bixin` | |
| 9 | 瞭望 right heart | `liaowang` | |
| 10 | 要饭 hands up | `yaofan` | |
| 11 | 迪迦 x-ray | `dijia` | |
| 12 | 右手抬 right hand up | `youshou` | |
| 13 | 拒绝 reject | `jujue` | |
| 14 | 右飞吻 right kiss | `youfeiwen` | |
| 15 | 双手飞吻 two-hand kiss | `shuangshoufeiwen` | |

> ℹ️ 关于 `bixin`：历史上 `bixin` 工具错用了 ID=2（实为击掌 high five）。已修复——`bixin` 改为 ID=8（真比心 heart），击掌功能由新增的 `jizhang`（ID=2）承担。

**新增动作工具**：在 `src/mcp/tools/` 下复制 `yaofan/`（最简模板，纯动作）改 `action_id` + 类名/函数名，并在 `src/mcp/mcp_server.py` 的 `add_common_tools` 里注册（参考现有 `baibai` 等工具的注册块）。`__init__.py` 必须 `from .manager import get_xxx_manager` 导出，否则 import 失败。

### 4. 其它 MCP 工具
- **`identify`** 人脸识别（调 `face/face.py`，30s 超时）
- **`daohang_dianti`** 导航到电梯/楼梯
- **`daohang_weishengjian`** 导航到卫生间
- `music` / `system` 等已启用；`calendar` / `timer` / `railway` / `search` / `recipe` / `check` / `amap` / `bazi` 已写好但被注释，取消注释即可启用

### 5. 智能体配置
- 智能体（人设 / 音色 / 对话语言 / LLM 模型）绑定在 **小智控制台** https://xiaozhi.me/console/agents
- 设备通过 `Device-Id` + `Client-Id` 自动关联控制台上的智能体，**控制台改完下次会话生效**
- G1 动作 / 导航 / 识别等 MCP 工具是**本地**的，智能体在对话中通过 MCP 协议调用

---

## 快速开始

### 环境要求
- Python 3.9（`start_g1.sh` 指定 `/usr/bin/python3.9`）
- `unitree_sdk2_python` 库
- CycloneDDS（运行时需设置 `CYCLONEDDS_HOME` 与 `LD_LIBRARY_PATH`，见 `run.sh`）
- Node.js ≥ 18（构建前端；见下方说明）
- G1 固件：`vui_service >= 2.0.3.8`，`vui module >= 2.0.0.3`

### 后端启动

```bash
cd tang/WK/PythonProject/py-xiaozhi-main

# 方式一：直接跑（会设置 DDS 环境并校时）
./run.sh

# 方式二：CLI + WebSocket
python3.9 main.py --mode cli --protocol websocket

# 调试模式（跳过激活流程）
python3.9 main.py --mode cli --skip-activation
```

`main.py` 参数：
- `--mode {gui,cli}` 运行模式（默认 cli）
- `--protocol {mqtt,websocket}` 通信协议（默认 websocket）
- `--skip-activation` 跳过设备激活
- `--audio-path` 启动后延迟播放的提示音（默认 `111.mp3`）

### 配置

编辑 `tang/WK/PythonProject/py-xiaozhi-main/config/config.json`：

```jsonc
{
  "AUDIO_OPTIONS": {
    "USE_G1_AUDIO": true,          // 启用 G1 音频
    "G1_NETWORK_INTERFACE": "eth0", // G1 网络接口
    "G1_VOLUME": 85,
    "G1_LED_COLOR": { "R": 0, "G": 255, "B": 0 }
  },
  "WAKE_WORD_OPTIONS": {
    "USE_WAKE_WORD": true,
    "MODEL_PATH": "models/vosk-model-small-cn-0.22",
    "WAKE_WORDS": ["小野"]
  }
}
```

> ⚠️ `config/config.json` 含 MQTT token 等密钥，**已被 .gitignore 排除**，勿提交。配置示例见同目录模板。

### 开机自启（systemd）

```bash
cd tang/WK/PythonProject/py-xiaozhi-main
sudo ./install_service.sh     # 安装 g1-xiaozhi.service
```

服务文件 `g1-xiaozhi.service`：开机后以 `unitree` 用户运行 `start_g1.sh`，崩溃自动重启（`Restart=on-failure`，间隔 5s）。

### 前端构建（app-g1）

```bash
cd app-g1
npm install
npm run build
```

> ⚠️ 已知坑：系统自带 Node v10 会覆盖 nvm 的高版本 Node，导致 `npm run build` 失败。需把 nvm 的 v20+ 加到 PATH 最前面再构建。

构建产物输出到 `app-g1/dist/`，打包后的 APK 放在仓库根 `APK/`。

---

## 架构概览

```
┌──────────────┐   语音   ┌─────────────────────┐  WebSocket/MQTT  ┌──────────────┐
│  G1 麦克风    │─────────▶│  py-xiaozhi 后端     │─────────────────▶│ xiaozhi.me   │
│  (四麦阵列)   │          │  (小野唤醒 + ASR)    │                  │  云端智能体   │
└──────────────┘          │                     │  MCP 工具调用     │ (人设/音色/LLM)│
                          │  G1 音频 / LED       │◀─────────────────│              │
┌──────────────┐  TTS/LED │  16 种手臂动作       │                  └──────────────┘
│  G1 扬声器    │◀────────│  人脸识别 / 导航     │
│  + LED 灯带   │          └─────────┬───────────┘
└──────────────┘                    │ subprocess
                                    ▼
                          ┌─────────────────────┐
                          │ unitree_sdk2_python │  DDS  ──▶ G1 本体
                          │  (g1_arm_action…)   │
                          │  G1Nav2D 导航        │
                          └─────────────────────┘

┌──────────────┐  HTTP   ┌─────────────────────┐
│  app-g1 前端 │────────▶│  Flask 控制面板      │
│  (uni-app)   │         │  (app.py / 网站搭建.py)│
└──────────────┘         └─────────────────────┘
```

---

## 文档

- `tang/WK/PythonProject/py-xiaozhi-main/G1_AUDIO_README.md` — G1 音频集成快速开始
- `tang/WK/PythonProject/py-xiaozhi-main/G1_AUDIO_GUIDE.md` — G1 音频详细 API 说明
- `tang/WK/unitree_sdk2_python/example/g1/high_level/g1_arm_action_example.py` — 16 个预设动作定义（MCP 工具底层调它）
- `tang/WK/unitree_sdk2_python/example/g1/high_level/g1_action_time_adjust_limit.py` — 自定义关节动作框架（软限位 + 时间自动估算，比耶/敬礼等非预设动作用它编排）
- `tang/WK/PythonProject/py-xiaozhi-main/src/dir_structure.txt` — 后端目录结构

---

## 常见问题

**Q: `git add .` 报 `'app-g1/' 没有检出一个提交`？**
A: 子目录是嵌套 git 仓库且无提交。本仓库已统一为单仓库，删掉了各嵌套 `.git`，作为普通文件跟踪。

**Q: G1 SDK 不可用 / 连不上 G1？**
A: 检查①`unitree_sdk2_python` 已安装；②`CYCLONEDDS_HOME` 与 `LD_LIBRARY_PATH` 已设置（见 `run.sh`）；③网络接口名与 `config.json` 的 `G1_NETWORK_INTERFACE` 一致（`eth0`）。

**Q: 前端 `npm run build` 失败？**
A: 系统 Node v10 覆盖了 nvm 的高版本，把 nvm v20+ 加到 PATH 最前面。

**Q: 改了智能体没生效？**
A: 智能体配置在 https://xiaozhi.me/console/agents 改，下次会话/重连后生效，不是本地改。

**Q: 改了 MCP 工具代码不生效？**
A: **实际运行的代码在机器人 `unitree@192.168.4.53` 上**（路径 `/home/unitree/tang/WK/PythonProject/py-xiaozhi-main`），本仓库的 `tang/` 只是备份。改代码必须 SSH 到机器人改（`ssh unitree`，配置在 `~/.ssh/config`）。改完后若要同步到本仓库，用 rsync 拉回再 commit。新工具加完需重启 py-xiaozhi 才会被 MCP 上报给智能体。

---

## 许可证

继承自 py-xiaozhi 原项目（见 `tang/WK/PythonProject/py-xiaozhi-main/LICENSE`）。第三方 SDK（unitree_sdk2_python / noVNC / cyclonedds / Livox-SDK2）遵循各自许可证。

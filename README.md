# 基于树莓派的边缘智能火灾监测系统

本项目是面向家居（厨房）场景的火灾监测系统，结合了传统传感器（温湿度、烟雾）和计算机视觉（摄像头），并接入大模型（LLM）进行多模态风险分析。

## 📁 目录结构

- `hardware/`: 硬件驱动层（传感器、摄像头读取）。包含模拟模式，可在无硬件环境下测试。
- `core/`: 核心业务逻辑（数据融合、大模型调用、状态管理）。
- `web/`: Web 服务器（FastAPI）和 API 接口。
- `templates/`: 前端监控大屏页面。
- `config.py`: 配置文件（引脚定义、API Key 等）。

## 🛠️ 硬件连接指南 (树莓派 4B)

| 硬件           | 树莓派引脚 (BCM) | 说明                                         |
| -------------- | ---------------- | -------------------------------------------- |
| DHT22 (温湿度) | GPIO 4           | 需要接上拉电阻 (通常模块自带)                |
| MQ-2 (烟雾)    | GPIO 17          | 使用数字输出 (DO) 引脚                       |
| CSI 摄像头     | CAMERA 接口      | 注意区分 Camera 和 Display 接口 (插中间那个) |

## 🚀 快速开始

### 1. 环境安装

在树莓派上打开终端：

```bash
# 更新系统
sudo apt update && sudo apt upgrade

# 安装系统依赖 (OpenCV, GPIO)
sudo apt install python3-opencv libgpiod2

# 创建虚拟环境 (推荐)
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
pip install -r requirements.txt
```

### 2. 配置系统

修改 `config.py` 文件：

- 如果你有 OpenAI 格式的 API Key (如 GPT-4, DeepSeek, 智谱等)，请填写 `LLM_API_KEY` 和 `LLM_BASE_URL`。
- 如果没有 Key，系统将仅基于规则（温度/烟雾）报警，不显示 AI 分析结果。

### 3. 运行系统

```bash
python run.py
```

### 4. 访问监控大屏

在局域网内的电脑或手机浏览器访问树莓派 IP：
`http://<树莓派IP>:8000`

## 🧪 模拟模式

如果在没有连接传感器的电脑上运行，系统会自动进入**模拟模式**：

- 产生随机温湿度数据。
- 摄像头显示黑屏或不可用提示。
- 此时可用于调试 Web 界面和逻辑流程。

## 🎓 毕业设计核心点对应

1. **多模态数据融合**: `core/fusion.py` 中结合了 Sensor 数据和 Image 数据。
2. **大模型赋能**: `core/llm_analyzer.py` 构建 Prompt 并调用 LLM 进行推理。
3. **边缘智能**: 所有数据采集、预处理和轻量级规则判断都在本地（Edge）完成。

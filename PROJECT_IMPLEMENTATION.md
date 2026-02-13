# 基于树莓派的边缘智能环境监测系统 - 项目技术实现文档

## 1. 系统概述

本项目旨在设计并实现一个面向家居厨房场景的火灾监测系统。系统基于树莓派 5 边缘计算平台，集成了 MQ-2 烟雾传感器、DHT22 温湿度传感器和 USB 摄像头，实现了多模态数据的实时采集。核心创新点在于结合了传统规则引擎与大语言模型（LLM）的视觉分析能力，实现了从“感知”到“认知”的火灾检测升级。

## 2. 系统架构设计

系统采用模块化分层架构设计，自下而上分为：**硬件驱动层**、**核心业务层**、**接口服务层** 和 **前端展示层**。

### 2.1 架构图示

```mermaid
graph TD
    subgraph Edge[边缘计算端 (Raspberry Pi)]
        HW[硬件层: GPIO/USB] --> Drivers[驱动层: Camera/Sensors]
        Drivers --> Fusion[融合引擎: DataFusionSystem]
        Fusion --> Logic[业务逻辑: 状态判定]
        Logic --> WebAPI[API服务: FastAPI]
    end

    subgraph Cloud[云端/大模型]
        Logic -- 图片+数据 --> LLM[大语言模型 (GPT-4o/Vision)]
        LLM -- 风险分析报告 --> Logic
    end

    subgraph Client[用户端]
        WebAPI -- 视频流/WebSocket --> Dashboard[Web监控大屏]
    end
```

## 3. 详细模块实现

### 3.1 硬件驱动层 (Hardware Layer)

位于 `hardware/` 目录。

- **传感器驱动 (`sensors.py`)**:

  - 使用 `adafruit_dht` 库读取 DHT22 温湿度数据。
  - 使用 `RPi.GPIO` 监听 MQ-2 数字引脚状态。
  - **模拟模式设计**: 为了方便开发和调试，加入了 `try-except` 机制检测硬件环境。当无法加载 GPIO 库时（如在 PC 上运行），自动切换到模拟模式，生成随机温湿度和烟雾状态。

- **摄像头驱动 (`camera.py`)**:
  - 基于 `OpenCV` (`cv2.VideoCapture`) 封装。
  - 实现了帧捕获的异常处理和自动重连机制（基础版）。
  - 同样支持模拟模式，当无法打开摄像头时，返回空数据，防止程序崩溃。

### 3.2 核心业务层 (Core Layer)

位于 `core/` 目录，是系统的“大脑”。

- **数据融合系统 (`fusion.py` - `DataFusionSystem`)**:

  - **多线程模型**: 启动一个后台守护线程 (`monitor_thread`) 持续循环读取传感器和摄像头数据，保证数据采集不阻塞 Web 服务。
  - **线程安全**: 使用 `threading.Lock` 保护共享状态 (`SystemState`)，确保 Web 接口读取的数据与采集线程写入的数据一致。
  - **融合逻辑**:
    1.  **一级判定 (规则)**: 当 `smoke_detected == True` 或 `temperature > 50℃` 时，立即标记风险等级。
    2.  **二级确认 (AI)**: 当规则判定为 Warning/Danger 时，触发 LLM 分析器，将当前帧和传感器数值打包发送。

- **大模型分析器 (`llm_analyzer.py` - `FireLLMAnalyzer`)**:
  - **Prompt 工程**: 构建了包含角色定义（安全专家）、上下文数据（温湿度、烟雾状态）和任务指令（JSON 格式输出）的结构化 Prompt。
  - **多模态输入**: 使用 `cv2` 将图像编码为 Base64 格式，结合文本 Prompt 调用 OpenAI 兼容接口（支持 GPT-4V, DeepSeek-VL 等）。
  - **输出解析**: 模型返回结构化的 JSON 数据（风险等级、描述、建议），供前端直接展示。

### 3.3 接口服务层 (Web Layer)

位于 `web/` 目录。

- **FastAPI 框架**: 选用 FastAPI 构建高性能异步 Web 服务。
- **视频流传输**: 实现了一个生成器 `generate_frames()`，使用 `multipart/x-mixed-replace` 协议推送 MJPEG 视频流，实现了低延迟的浏览器端视频直播。
- **API 设计**:
  - `GET /video_feed`: 视频流端点。
  - `GET /api/status`: 返回系统当前完整状态（JSON），包含传感器数值、风险等级和 AI 分析结果。

### 3.4 前端展示层 (Frontend)

位于 `templates/` 和 `static/` 目录。

- **技术栈**: HTML5 + Tailwind CSS +原生 JavaScript。
- **动态更新**: 使用 `setInterval` 定时轮询 `/api/status` 接口，动态更新 DOM 元素，无需刷新页面即可看到温湿度变化和报警状态。
- **视觉设计**: 采用暗色主题（Dark Mode），高亮显示关键数据，报警状态下文字颜色会发生变化（如变红闪烁）。

## 4. 关键代码解析

### 4.1 多模态数据融合逻辑 (`core/fusion.py`)

```python
# 伪代码逻辑展示
def _monitor_loop(self):
    while self.running:
        # 1. 同步采集异构数据
        temp, hum = sensors.read()
        image = camera.read()

        # 2. 规则引擎快速筛选
        if smoke or temp > THRESHOLD:
            risk = "Danger"

            # 3. 触发大模型进行视觉确认 (Edge-Cloud 协同)
            # 只有在规则引擎认为有风险时，才消耗 Token 调用大模型
            analysis = self.llm.analyze(temp, hum, smoke, image)
            self.state.llm_analysis = analysis
```

### 4.2 视频流生成 (`web/main.py`)

```python
def generate_frames():
    while True:
        frame = system.get_latest_frame()
        # 编码为 JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        # 构造 multipart 响应流
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
```

## 5. 总结

本系统通过软硬件协同设计，在树莓派有限的计算资源上实现了高效的环境监测。通过引入大模型技术，解决了传统烟雾传感器容易误报（如水蒸气、油烟干扰）的痛点，利用视觉能力对火灾现场进行二次确认，不仅能检测“有没有火”，还能分析“火势如何”并给出建议，非常符合当前边缘智能（Edge AI）的发展趋势。

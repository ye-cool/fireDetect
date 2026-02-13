# 树莓派本地大模型 (Local LLM) 部署指南

本指南将教你如何在树莓派 5 上使用 **Ollama** 部署完全离线的视觉大模型，无需 API Key，保护隐私且免费。

## 1. 为什么选择 Ollama + Moondream?

- **Ollama**: 目前最流行的本地大模型运行工具，支持树莓派（ARM64 架构），安装极其简单。
- **Moondream**: 专门为边缘设备设计的**微型视觉模型** (仅 1.8B 参数)。
    - 在树莓派 5 上运行速度快（几秒钟出结果）。
    - 能够理解图像内容（"图中有火吗？"）。
    - 相比 LLaVA (7B) 或 GPT-4，它非常轻量，不会卡死树莓派。

## 2. 安装 Ollama

在树莓派终端执行以下命令（只需一行）：

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

安装完成后，Ollama 会自动在后台启动。你可以通过以下命令验证：
```bash
ollama --version
```

## 3. 拉取模型

下载 moondream 模型（约 1GB 左右）：

```bash
ollama pull moondream
```

*如果你想尝试更强的模型（速度会变慢），可以拉取 `llava-phi3` (3.8B 参数)。*

## 4. 测试模型

先在终端里手动测试一下，看看模型能不能跑通。

```bash
# 运行模型
ollama run moondream

# 进入交互模式后，你可以尝试发送一张图片的路径，或者直接问它文本问题
# 例如输入: Describe this image.
# (按 Ctrl+D 退出)
```

## 5. 配置本项目使用本地模型

本项目已经为你做好了适配。

1. 打开 `config.py` 文件：
   ```bash
   nano config.py
   ```

2. 修改配置项：
   ```python
   # 将模式改为 local
   LLM_MODE = "local"
   
   # 确认模型名称正确
   LLM_MODEL_LOCAL = "moondream" 
   ```

3. 保存并退出 (`Ctrl+O` -> `Enter` -> `Ctrl+X`)。

## 6. 运行效果

重启你的火灾监测系统：
```bash
python run.py
```

现在，当系统检测到异常（高温或烟雾）时，它会：
1. 抓拍一张照片。
2. 发送给本机运行的 Ollama 服务 (端口 11434)。
3. Moondream 模型分析图片和数据。
4. 几秒钟后，Web 大屏上会显示分析结果。

**注意**: 
- 第一次调用可能会慢一点（加载模型到内存）。
- 树莓派 5 运行模型时 CPU 占用会很高，可能会导致视频流短暂卡顿，这是正常的边缘计算负载表现。

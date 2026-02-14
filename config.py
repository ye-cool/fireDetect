import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 传感器引脚配置 (BCM编码)
    PIN_DHT22 = 4
    PIN_MQ2 = 17  # MQ-2 Digital Pin (如果使用 ADC，此引脚可作为备用或移除)
    
    # ADC 配置 (I2C)
    USE_ADC = True  # 是否使用 ADS1115 读取模拟值
    I2C_BUS = 1
    ADS1115_ADDRESS = 0x48
    MQ2_ANALOG_CHANNEL = 0 # ADS1115 的 A0 通道
    SMOKE_THRESHOLD_ANALOG = 15000 # 模拟值阈值 (0-32767)，需校准
    
    # 摄像头ID
    CAMERA_ID = 0

    # YOLO 视觉检测配置 (ONNX + OpenCV DNN)
    USE_YOLO = True
    YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "models/fire_yolo.onnx")
    YOLO_CLASSES = ["fire", "smoke"]
    YOLO_INPUT_SIZE = 320
    YOLO_CONF_THRESHOLD = 0.2
    YOLO_IOU_THRESHOLD = 0.45
    YOLO_INFER_INTERVAL_SECONDS = 0.5
    YOLO_FIRE_LABELS = ["fire", "flame"]
    YOLO_FIRE_MIN_CONF = 0.2
    
    # 阈值设置
    TEMP_THRESHOLD = 50.0  # 摄氏度
    HUMIDITY_THRESHOLD = 20.0 # 湿度过低也是风险
    SMOKE_DETECTED_VALUE = 0 # 0通常代表检测到烟雾（低电平触发），视具体模块而定，这里假设低电平触发
    
    # 大模型配置
    # 模式: "cloud" (使用OpenAI/DeepSeek等云服务) 或 "local" (使用本地Ollama)
    LLM_MODE = "local" 
    
    # --- 云端配置 (LLM_MODE="cloud") ---
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL_CLOUD = "gpt-4o"
    
    # --- 本地配置 (LLM_MODE="local") ---
    # 推荐使用 Ollama 运行 moondream (轻量级视觉模型) 或 llava
    # 安装: curl -fsSL https://ollama.com/install.sh | sh
    # 拉取模型: ollama pull moondream
    LLM_LOCAL_URL = "http://localhost:11434/v1"
    LLM_MODEL_LOCAL = "moondream" # 仅在 LLM_USE_IMAGE=True 时使用
    LLM_MODEL_LOCAL_TEXT = os.getenv("LLM_MODEL_LOCAL_TEXT", "qwen2.5:1.5b")
    LLM_TIMEOUT_SECONDS = 60
    LLM_IMAGE_MAX_SIDE = 384
    LLM_IMAGE_JPEG_QUALITY = 55
    LLM_USE_IMAGE = False
    LLM_MAX_TOKENS = 60
    LLM_TEMPERATURE = 0.0
    LLM_TOP_P = 0.2
    LLM_NUM_CTX = 384
    LLM_SKIP_ON_NORMAL = True
    LLM_FORCE_CHINESE = True

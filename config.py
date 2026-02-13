import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 传感器引脚配置 (BCM编码)
    PIN_DHT22 = 4
    PIN_MQ2 = 17  # MQ-2 Digital Pin
    
    # 摄像头ID
    CAMERA_ID = 0
    
    # 阈值设置
    TEMP_THRESHOLD = 50.0  # 摄氏度
    HUMIDITY_THRESHOLD = 20.0 # 湿度过低也是风险
    SMOKE_DETECTED_VALUE = 0 # 0通常代表检测到烟雾（低电平触发），视具体模块而定，这里假设低电平触发
    
    # 大模型配置
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = "gpt-4o" # 或者其他支持视觉的模型

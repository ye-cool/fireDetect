import base64
import logging
from openai import OpenAI
from config import Config
import cv2

class FireLLMAnalyzer:
    def __init__(self):
        self.client = OpenAI(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL
        )
        self.model = Config.LLM_MODEL

    def encode_image(self, image):
        """将OpenCV图像转换为Base64字符串"""
        if image is None:
            return None
        _, buffer = cv2.imencode('.jpg', image)
        return base64.b64encode(buffer).decode('utf-8')

    def analyze(self, temperature, humidity, smoke_detected, image):
        """
        调用大模型进行多模态分析
        """
        if not Config.LLM_API_KEY:
            logging.warning("未配置 LLM API Key，跳过大模型分析")
            return "未配置大模型，仅依据传感器数据报警"

        base64_image = self.encode_image(image)
        if not base64_image:
            return "无法获取图像，无法进行视觉确认"

        prompt = f"""
        你是一个家庭火灾安全专家。请根据以下传感器数据和现场图像判断是否存在火灾风险。
        
        【传感器数据】
        - 温度: {temperature}°C
        - 湿度: {humidity}%
        - 烟雾传感器状态: {'检测到烟雾' if smoke_detected else '正常'}
        
        【任务】
        1. 分析传感器数据是否异常。
        2. 观察图像中是否有火焰、浓烟或高温引起的视觉扭曲。
        3. 综合判断火灾风险等级（正常/可疑/危险）。
        4. 给出简短的行动建议。
        
        请以JSON格式返回，包含字段: risk_level (String), description (String), suggestion (String)。
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ],
                    }
                ],
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"LLM分析失败: {e}")
            return "智能分析服务暂时不可用"

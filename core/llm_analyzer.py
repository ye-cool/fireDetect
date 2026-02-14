import base64
import logging
from openai import OpenAI
from config import Config
import cv2

class FireLLMAnalyzer:
    def __init__(self):
        # 根据配置决定使用本地还是云端
        if Config.LLM_MODE == "local":
            self.client = OpenAI(
                api_key="ollama", # Ollama 不需要真实Key，但库需要占位符
                base_url=Config.LLM_LOCAL_URL
            )
            self.model = Config.LLM_MODEL_LOCAL
            logging.info(f"LLM分析器已初始化 (本地模式: {self.model})")
        else:
            self.client = OpenAI(
                api_key=Config.LLM_API_KEY,
                base_url=Config.LLM_BASE_URL
            )
            self.model = Config.LLM_MODEL_CLOUD
            logging.info(f"LLM分析器已初始化 (云端模式: {self.model})")

    def encode_image(self, image):
        """将OpenCV图像转换为Base64字符串"""
        if image is None:
            return None
        try:
            h, w = image.shape[:2]
            max_side = int(getattr(Config, "LLM_IMAGE_MAX_SIDE", 384))
            if max(h, w) > max_side:
                scale = max_side / float(max(h, w))
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        except Exception:
            pass

        quality = int(getattr(Config, "LLM_IMAGE_JPEG_QUALITY", 55))
        _, buffer = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        return base64.b64encode(buffer).decode('utf-8')

    def analyze(self, temperature, humidity, smoke_detected, image):
        """
        调用大模型进行多模态分析
        """
        # 云端模式下如果没有Key则跳过
        if Config.LLM_MODE == "cloud" and not Config.LLM_API_KEY:
            logging.warning("未配置 LLM API Key，跳过大模型分析")
            return "未配置大模型，仅依据传感器数据报警"

        base64_image = self.encode_image(image)
        if not base64_image:
            prompt = f"""
            你是一个家庭火灾安全专家。请根据以下传感器数据判断是否存在火灾风险。

            【传感器数据】
            - 温度: {temperature}°C
            - 湿度: {humidity}%
            - 烟雾传感器状态: {'检测到烟雾' if smoke_detected else '正常'}

            【任务】
            1. 分析传感器数据是否异常。
            2. 综合判断火灾风险等级（正常/可疑/危险）。
            3. 给出简短的行动建议。

            请以JSON格式返回，包含字段: risk_level (String), description (String), suggestion (String)。
            """

            try:
                logging.info(f"正在调用大模型 ({self.model})...")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    timeout=Config.LLM_TIMEOUT_SECONDS,
                )
                return response.choices[0].message.content
            except Exception as e:
                logging.error(f"LLM分析失败: {e}")
                return f"智能分析服务暂时不可用 ({str(e)})"

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
            logging.info(f"正在调用大模型 ({self.model})...")
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
                                },
                            },
                        ],
                    }
                ],
                max_tokens=200,
                timeout=Config.LLM_TIMEOUT_SECONDS,
            )
            return response.choices[0].message.content
        except Exception as e:
            msg = str(e)
            logging.error(f"LLM分析失败: {e}")
            if "timed out" in msg.lower() or "timeout" in msg.lower():
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=200,
                        timeout=Config.LLM_TIMEOUT_SECONDS,
                    )
                    return response.choices[0].message.content
                except Exception as e2:
                    logging.error(f"LLM分析失败: {e2}")
                    return f"智能分析服务暂时不可用 ({str(e2)})"
            return f"智能分析服务暂时不可用 ({str(e)})"

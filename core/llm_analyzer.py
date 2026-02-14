import base64
import logging
import json
import re
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
            self.model = ""
            logging.info(f"LLM分析器已初始化 (本地模式: {self.model})")
        else:
            self.client = OpenAI(
                api_key=Config.LLM_API_KEY,
                base_url=Config.LLM_BASE_URL
            )
            self.model = ""
            logging.info(f"LLM分析器已初始化 (云端模式: {self.model})")

        self._refresh_model_from_config()

    def _refresh_model_from_config(self):
        if Config.LLM_MODE == "local":
            if getattr(Config, "LLM_USE_IMAGE", False):
                self.model = Config.LLM_MODEL_LOCAL
            else:
                self.model = getattr(Config, "LLM_MODEL_LOCAL_TEXT", "") or Config.LLM_MODEL_LOCAL
        else:
            self.model = Config.LLM_MODEL_CLOUD

    def _normalize_json(self, text: str, fallback_risk: str = "Normal") -> str:
        def _ensure(obj):
            risk = str(obj.get("risk_level", fallback_risk) or fallback_risk)
            if risk not in ("Normal", "Warning", "Danger"):
                risk = fallback_risk
            return {
                "risk_level": risk,
                "description": str(obj.get("description", "") or ""),
                "suggestion": str(obj.get("suggestion", "") or ""),
            }

        if not text:
            return json.dumps(_ensure({}), ensure_ascii=False)

        s = text.strip()
        try:
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                return json.dumps(_ensure(parsed), ensure_ascii=False)
        except Exception:
            pass

        m = re.search(r"\{[\s\S]*\}", s)
        if m:
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, dict):
                    return json.dumps(_ensure(parsed), ensure_ascii=False)
            except Exception:
                pass

        return json.dumps(
            _ensure({"description": s, "suggestion": "请结合现场情况核验。"}),
            ensure_ascii=False,
        )

    def _rule_risk(self, temperature, humidity, smoke_detected, mq2_value, vision_fire_detected) -> str:
        if vision_fire_detected is True:
            return "Danger"
        if smoke_detected is True:
            return "Danger"

        try:
            if (
                getattr(Config, "USE_ADC", False)
                and mq2_value is not None
                and float(mq2_value) > float(getattr(Config, "SMOKE_THRESHOLD_ANALOG", 15000))
            ):
                return "Danger"
        except Exception:
            pass

        try:
            if temperature is not None and float(temperature) > float(getattr(Config, "TEMP_THRESHOLD", 50.0)):
                return "Warning"
        except Exception:
            pass

        try:
            if humidity is not None and float(humidity) < float(getattr(Config, "HUMIDITY_THRESHOLD", 20.0)):
                return "Warning"
        except Exception:
            pass

        return "Normal"

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

    def analyze_summary(self, temperature, humidity, smoke_detected, mq2_value, vision_fire_detected, vision_detections):
        self._refresh_model_from_config()
        if Config.LLM_MODE == "cloud" and not Config.LLM_API_KEY:
            logging.warning("未配置 LLM API Key，跳过大模型分析")
            return "未配置大模型，仅依据规则引擎报警"

        rule_risk = self._rule_risk(temperature, humidity, smoke_detected, mq2_value, vision_fire_detected)

        dets = []
        if isinstance(vision_detections, list) and vision_detections:
            for d in vision_detections[:5]:
                dets.append(
                    {
                        "label": d.get("label"),
                        "confidence": float(d.get("confidence", 0) or 0),
                    }
                )

        if getattr(Config, "LLM_SKIP_ON_NORMAL", False) and rule_risk == "Normal":
            return self._normalize_json(
                json.dumps(
                    {
                        "risk_level": "Normal",
                        "description": "传感器与视觉检测均未发现异常。",
                        "suggestion": "继续保持监测，注意通风与用电用火安全。",
                    },
                    ensure_ascii=False,
                ),
                fallback_risk="Normal",
            )

        context = {
            "temperature_c": temperature,
            "humidity_pct": humidity,
            "smoke_digital": smoke_detected,
            "mq2_analog": mq2_value,
            "mq2_threshold": getattr(Config, "SMOKE_THRESHOLD_ANALOG", None) if getattr(Config, "USE_ADC", False) else None,
            "vision_fire": vision_fire_detected,
            "detections": dets,
            "risk_level": rule_risk,
            "temp_threshold": getattr(Config, "TEMP_THRESHOLD", 50.0),
            "humidity_threshold": getattr(Config, "HUMIDITY_THRESHOLD", 20.0),
        }

        if getattr(Config, "LLM_FORCE_CHINESE", True):
            prompt_prefix = (
                "你将收到来自传感器与YOLO的JSON数据。不得编造任何未给出的信息；"
                "遇到null/None必须写“未知”。严格只输出JSON，不要Markdown/解释文字。"
                "输出字段必须且仅包含：risk_level、description、suggestion。"
                "其中risk_level必须与输入的risk_level完全一致(只能是Normal/Warning/Danger)。"
                "description与suggestion必须使用中文。\n"
            )
        else:
            prompt_prefix = (
                "You will be given JSON data from sensors and YOLO. Do NOT invent values. "
                "If a field is null/None, say 'unavailable'. Output ONLY JSON with keys risk_level, description, suggestion. "
                "risk_level MUST equal input.risk_level.\n"
            )

        prompt = prompt_prefix + json.dumps(context, ensure_ascii=False, separators=(",", ":"))

        try:
            logging.info(f"正在调用大模型 ({self.model})...")
            extra_body = None
            if Config.LLM_MODE == "local":
                extra_body = {
                    "options": {
                        "num_predict": int(getattr(Config, "LLM_MAX_TOKENS", 80)),
                        "temperature": float(getattr(Config, "LLM_TEMPERATURE", 0.0)),
                        "top_p": float(getattr(Config, "LLM_TOP_P", 0.2)),
                        "num_ctx": int(getattr(Config, "LLM_NUM_CTX", 512)),
                    }
                }

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=getattr(Config, "LLM_MAX_TOKENS", 120),
                temperature=getattr(Config, "LLM_TEMPERATURE", 0.0),
                top_p=getattr(Config, "LLM_TOP_P", 0.3),
                timeout=Config.LLM_TIMEOUT_SECONDS,
                extra_body=extra_body,
            )
            return self._normalize_json(response.choices[0].message.content, fallback_risk=rule_risk)
        except Exception as e:
            logging.error(f"LLM分析失败: {e}")
            return self._normalize_json(f"智能分析服务暂时不可用 ({str(e)})", fallback_risk=rule_risk)

    def analyze(self, temperature, humidity, smoke_detected, image, mq2_value=None, vision_fire_detected=None, vision_detections=None):
        """调用大模型进行分析"""
        self._refresh_model_from_config()
        # 云端模式下如果没有Key则跳过
        if Config.LLM_MODE == "cloud" and not Config.LLM_API_KEY:
            logging.warning("未配置 LLM API Key，跳过大模型分析")
            return "未配置大模型，仅依据传感器数据报警"

        if not getattr(Config, "LLM_USE_IMAGE", False):
            return self.analyze_summary(
                temperature=temperature,
                humidity=humidity,
                smoke_detected=smoke_detected,
                mq2_value=mq2_value,
                vision_fire_detected=vision_fire_detected,
                vision_detections=vision_detections,
            )

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

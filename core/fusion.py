import time
import logging
import threading
import json
from hardware.sensors import SensorManager
from hardware.camera import CameraDriver
from core.llm_analyzer import FireLLMAnalyzer
from config import Config

class SystemState:
    def __init__(self):
        self.temperature = None
        self.humidity = None
        self.smoke_detected = None
        self.mq2_value = None
        self.last_update = 0
        self.fire_risk_level = "Normal" # Normal, Warning, Danger
        self.llm_analysis_result = ""
        self.latest_frame = None

class DataFusionSystem:
    def __init__(self):
        self.sensors = SensorManager()
        self.camera = CameraDriver()
        self.llm = FireLLMAnalyzer()
        self.state = SystemState()
        self.running = False
        self._lock = threading.Lock()
        
    def start(self):
        self.running = True
        self.camera.start()
        # 启动后台监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logging.info("多模态数据融合监控系统已启动")

    def stop(self):
        self.running = False
        self.camera.release()
        self.sensors.cleanup()
        logging.info("系统已停止")

    def get_state(self):
        with self._lock:
            return {
                "temperature": self.state.temperature,
                "humidity": self.state.humidity,
                "smoke_detected": self.state.smoke_detected,
                "mq2_value": self.state.mq2_value, # 暴露给前端
                "risk_level": self.state.fire_risk_level,
                "llm_analysis": self.state.llm_analysis_result,
                "timestamp": self.state.last_update
            }

    def get_latest_frame(self):
        with self._lock:
            return self.state.latest_frame

    def _monitor_loop(self):
        while self.running:
            # 1. 获取数据
            temp, hum = self.sensors.read_dht22()
            smoke = self.sensors.read_mq2()
            mq2_val = self.sensors.get_mq2_value() # 获取模拟值
            frame = self.camera.get_frame()

            # 更新当前状态
            with self._lock:
                self.state.temperature = temp
                self.state.humidity = hum
                self.state.smoke_detected = smoke
                self.state.mq2_value = mq2_val
                self.state.latest_frame = frame
                self.state.last_update = time.time()

            # 2. 规则引擎初步判定 (边缘计算层)
            risk = "Normal"
            if self.state.smoke_detected is True:
                risk = "Danger"
            elif self.state.temperature is not None and self.state.temperature > Config.TEMP_THRESHOLD:
                risk = "Warning"
            
            # 3. 触发大模型赋能 (如果判定为高风险 或 用户手动请求 - 这里演示自动触发逻辑)
            # 为了防止频繁调用耗尽Token，我们设置一个冷却机制
            
            current_risk = risk
            
            # 只有当状态发生变化（例如从Normal变成Danger），或者距离上次分析超过一定时间（如60秒）时，才调用LLM
            # 这里简单实现：增加一个 last_analysis_time 变量
            now = time.time()
            if not hasattr(self, 'last_analysis_time'):
                self.last_analysis_time = 0

            # 如果规则判定危险，且距离上次分析超过60秒，调用大模型确认
            if current_risk in ["Warning", "Danger"] and (now - self.last_analysis_time > 60):
                logging.info(f"检测到异常 ({current_risk})，正在请求大模型分析...")
                analysis = self.llm.analyze(
                    self.state.temperature, 
                    self.state.humidity, 
                    self.state.smoke_detected, 
                    frame
                )
                with self._lock:
                    self.state.llm_analysis_result = analysis
                self.last_analysis_time = now
            elif current_risk == "Normal":
                 with self._lock:
                    self.state.llm_analysis_result = "系统运行正常"


            with self._lock:
                self.state.fire_risk_level = current_risk

            time.sleep(2) # 采样间隔

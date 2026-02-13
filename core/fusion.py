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
        self.temperature = 0.0
        self.humidity = 0.0
        self.smoke_detected = False
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
            frame = self.camera.get_frame()

            # 更新当前状态
            with self._lock:
                if temp is not None: self.state.temperature = temp
                if hum is not None: self.state.humidity = hum
                self.state.smoke_detected = smoke
                self.state.latest_frame = frame
                self.state.last_update = time.time()

            # 2. 规则引擎初步判定 (边缘计算层)
            risk = "Normal"
            if self.state.smoke_detected:
                risk = "Danger"
            elif self.state.temperature > Config.TEMP_THRESHOLD:
                risk = "Warning"
            
            # 3. 触发大模型赋能 (如果判定为高风险 或 用户手动请求 - 这里演示自动触发逻辑)
            # 为了防止频繁调用耗尽Token，我们设置一个冷却机制，或者只在状态变化为Danger时触发
            # 这里简化逻辑：如果是Danger且没有分析过，或者每隔一段时间分析一次
            
            current_risk = risk
            
            # 如果规则判定危险，调用大模型确认 (Edge-Cloud Collaboration)
            if current_risk in ["Warning", "Danger"]:
                logging.info(f"检测到异常 ({current_risk})，正在请求大模型分析...")
                analysis = self.llm.analyze(
                    self.state.temperature, 
                    self.state.humidity, 
                    self.state.smoke_detected, 
                    frame
                )
                with self._lock:
                    self.state.llm_analysis_result = analysis
            else:
                with self._lock:
                    self.state.llm_analysis_result = "系统运行正常"

            with self._lock:
                self.state.fire_risk_level = current_risk

            time.sleep(2) # 采样间隔

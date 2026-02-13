import time
import random
import logging
from config import Config

# 尝试导入硬件库，如果失败则启用模拟模式
try:
    import board
    import adafruit_dht
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except (ImportError, NotImplementedError):
    logging.warning("未检测到树莓派GPIO环境，启用传感器模拟模式")
    HARDWARE_AVAILABLE = False

class SensorManager:
    def __init__(self):
        self.dht_device = None
        self.mq2_pin = Config.PIN_MQ2
        self._setup()

    def _setup(self):
        if HARDWARE_AVAILABLE:
            try:
                # 初始化 DHT22
                self.dht_device = adafruit_dht.DHT22(board.D4) # 对应 Config.PIN_DHT22 (BCM 4)
                
                # 初始化 MQ-2
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.mq2_pin, GPIO.IN)
            except Exception as e:
                logging.error(f"传感器硬件初始化失败: {e}")
                global HARDWARE_AVAILABLE
                HARDWARE_AVAILABLE = False

    def read_dht22(self):
        """读取温湿度"""
        if HARDWARE_AVAILABLE and self.dht_device:
            try:
                temperature = self.dht_device.temperature
                humidity = self.dht_device.humidity
                if temperature is None or humidity is None:
                    # 硬件读取偶尔会失败，返回None
                    return None, None
                return temperature, humidity
            except RuntimeError as error:
                # DHT读取频率过快经常会报错，这是正常的
                # logging.debug(f"DHT读取错误: {error.args[0]}")
                return None, None
            except Exception as error:
                self.dht_device.exit()
                return None, None
        else:
            # 模拟数据
            return round(random.uniform(20.0, 60.0), 1), round(random.uniform(30.0, 70.0), 1)

    def read_mq2(self):
        """读取烟雾状态. True表示有烟雾 (假设低电平触发)"""
        if HARDWARE_AVAILABLE:
            try:
                # 如果是数字输出，0通常代表检测到阈值
                state = GPIO.input(self.mq2_pin)
                return state == Config.SMOKE_DETECTED_VALUE
            except Exception:
                return False
        else:
            # 模拟偶尔检测到烟雾 (1% 概率)
            return random.random() > 0.99

    def cleanup(self):
        if HARDWARE_AVAILABLE:
            if self.dht_device:
                self.dht_device.exit()
            GPIO.cleanup()

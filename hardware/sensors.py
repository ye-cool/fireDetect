import time
import random
import logging
from config import Config

# 尝试导入硬件库，如果失败则启用模拟模式
try:
    import board
    import busio
    import adafruit_dht
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except (ImportError, NotImplementedError):
    logging.warning("未检测到树莓派GPIO环境或ADC库，启用传感器模拟模式")
    HARDWARE_AVAILABLE = False

class SensorManager:
    def __init__(self):
        self.dht_device = None
        self.mq2_pin = Config.PIN_MQ2
        self.ads = None
        self.mq2_analog = None
        self._setup()

    def _setup(self):
        global HARDWARE_AVAILABLE
        if HARDWARE_AVAILABLE:
            try:
                # 初始化 DHT22
                self.dht_device = adafruit_dht.DHT22(board.D4)
                
                # 初始化 ADS1115 (I2C)
                if Config.USE_ADC:
                    try:
                        i2c = busio.I2C(board.SCL, board.SDA)
                        self.ads = ADS.ADS1115(i2c)
                        # 创建单端输入通道 (A0)
                        # 修正: adafruit-circuitpython-ads1x15 最新版库 API 变更
                        # 必须从 adafruit_ads1x15.ads1x15 导入 P0 (注意是 ads1x15 不是 ads1115)
                        try:
                            from adafruit_ads1x15.ads1x15 import P0, P1, P2, P3
                        except ImportError:
                            # 极少数旧版本可能在这里
                            from adafruit_ads1x15.analog_in import AnalogIn
                            # 如果真的找不到 P0，我们就不折腾了，直接用 ADS1115 对象
                            # 但通常上面的 import 是对的
                            pass

                        channel_map = {0: P0, 1: P1, 2: P2, 3: P3}
                        self.mq2_analog = AnalogIn(self.ads, channel_map[Config.MQ2_ANALOG_CHANNEL])
                        logging.info("ADS1115 ADC 初始化成功")
                    except Exception as e:
                        logging.error(f"ADS1115 初始化失败: {e}")
                
                # 初始化 MQ-2 数字引脚 (作为备份或不使用)
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.mq2_pin, GPIO.IN)
            except Exception as e:
                logging.error(f"传感器硬件初始化失败: {e}")
                HARDWARE_AVAILABLE = False

    def read_dht22(self):
        # ... (保持不变) ...
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
        """
        读取烟雾状态。
        如果启用了 ADC，返回模拟电压值是否超过阈值。
        否则返回数字引脚状态。
        """
        if HARDWARE_AVAILABLE:
            # 优先使用 ADC 读取模拟值
            if Config.USE_ADC and self.mq2_analog:
                try:
                    value = self.mq2_analog.value
                    # logging.debug(f"MQ-2 Analog Value: {value}")
                    return value > Config.SMOKE_THRESHOLD_ANALOG
                except Exception as e:
                    logging.error(f"ADC 读取失败: {e}")
            
            # 降级到数字引脚读取
            try:
                state = GPIO.input(self.mq2_pin)
                return state == Config.SMOKE_DETECTED_VALUE
            except Exception:
                return False
        else:
            # 模拟模式
            return False

    def get_mq2_value(self):
        """获取 MQ-2 的原始模拟值 (用于前端显示波形等)"""
        if HARDWARE_AVAILABLE and Config.USE_ADC and self.mq2_analog:
            try:
                return self.mq2_analog.value
            except:
                return 0
        return 0

    def cleanup(self):
        # ... (保持不变) ...
        if HARDWARE_AVAILABLE:
            if self.dht_device:
                self.dht_device.exit()
            GPIO.cleanup()

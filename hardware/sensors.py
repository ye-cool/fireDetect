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
                        # 修正: adafruit-circuitpython-ads1x15 库 API 变更
                        # 正确用法是直接使用 ADS.P0 (如果导入正确)
                        # 如果 ADS.P0 不存在，说明库结构不同，尝试最通用的方式
                        
                        # 在最新版库中，通道是作为 AnalogIn 的参数传入的，通常是 ADS.P0
                        # 让我们打印一下 ADS 的属性看看
                        # logging.info(dir(ADS)) 
                        
                        # 尝试直接使用 ADS.P0 (假设上面的 import adafruit_ads1x15.ads1115 as ADS 生效)
                        # 注意：上面的 import 是 import adafruit_ads1x15.ads1115 as ADS
                        # 在这个模块里，P0 是存在的
                        
                        self.mq2_analog = AnalogIn(self.ads, getattr(ADS, f'P{Config.MQ2_ANALOG_CHANNEL}'))
                        logging.info("ADS1115 ADC 初始化成功")
                    except AttributeError:
                        # 如果 ADS.P0 真的没有，尝试从 analog_in 构造
                        # 有些版本可能不需要 P0 常量，而是直接传数字？不，AnalogIn 需要 Pin 对象
                        logging.warning("ADS 模块缺少 P0 属性，尝试备用方案...")
                        # 备用方案：手动查找 Pin 类? 不太可能。
                        # 让我们试回最原始的 import 方式，可能是命名空间污染
                        import adafruit_ads1x15.ads1115 as ADS1115_Module
                        self.mq2_analog = AnalogIn(self.ads, getattr(ADS1115_Module, f'P{Config.MQ2_ANALOG_CHANNEL}'))
                        logging.info("ADS1115 ADC 初始化成功 (备用方案)")
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

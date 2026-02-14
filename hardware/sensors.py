import time
import random
import logging
from config import Config

try:
    import board
    import adafruit_dht
    import RPi.GPIO as GPIO
    _LIBS_AVAILABLE = True
except (ImportError, NotImplementedError):
    logging.warning("未检测到树莓派GPIO环境，启用传感器模拟模式")
    _LIBS_AVAILABLE = False

class SensorManager:
    def __init__(self):
        self.dht_device = None
        self.mq2_pin = Config.PIN_MQ2
        self.i2c_bus = None
        self._adc_disabled = False
        self._dht_ok = False
        self._gpio_ok = False
        self._adc_ok = False
        self._setup()

    def _setup(self):
        if not _LIBS_AVAILABLE:
            return

        try:
            self.dht_device = adafruit_dht.DHT22(board.D4)
            self._dht_ok = True
        except Exception as e:
            self.dht_device = None
            self._dht_ok = False
            logging.error(f"DHT22 初始化失败: {e}")

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.mq2_pin, GPIO.IN)
            self._gpio_ok = True
        except Exception as e:
            self._gpio_ok = False
            logging.error(f"GPIO 初始化失败: {e}")

        if Config.USE_ADC:
            try:
                from smbus2 import SMBus

                self.i2c_bus = SMBus(Config.I2C_BUS)
                self._adc_ok = True
                logging.info("ADS1115 I2C 初始化成功")
            except Exception as e:
                self.i2c_bus = None
                self._adc_ok = False
                logging.error(f"ADS1115 初始化失败: {e}")

    def _read_ads1115_raw(self, channel: int) -> int:
        if self._adc_disabled:
            return 0
        if not (_LIBS_AVAILABLE and Config.USE_ADC and self.i2c_bus and self._adc_ok):
            return 0

        mux_map = {0: 0x4, 1: 0x5, 2: 0x6, 3: 0x7}
        mux = mux_map.get(int(channel), 0x4)
        config = (
            0x8000
            | (mux << 12)
            | (0x1 << 9)
            | 0x0100
            | (0x4 << 5)
            | 0x0003
        )

        addr = int(Config.ADS1115_ADDRESS)
        try:
            self.i2c_bus.write_i2c_block_data(addr, 0x01, [(config >> 8) & 0xFF, config & 0xFF])
            time.sleep(0.01)
            data = self.i2c_bus.read_i2c_block_data(addr, 0x00, 2)
        except OSError as e:
            logging.error(f"ADS1115 I2C 读写失败: {e}")
            self._adc_disabled = True
            try:
                self.i2c_bus.close()
            except Exception:
                pass
            self.i2c_bus = None
            return 0
        raw = (data[0] << 8) | data[1]
        if raw & 0x8000:
            raw -= 1 << 16
        if raw < 0:
            logging.warning(f"ADS1115 读到负值 {raw} (channel={channel})，可能接线/配置异常")
            raw = 0
        return int(raw)

    def read_dht22(self):
        """读取温湿度"""
        if _LIBS_AVAILABLE and self._dht_ok and self.dht_device:
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
                try:
                    self.dht_device.exit()
                except Exception:
                    pass
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
        if _LIBS_AVAILABLE:
            # 优先使用 ADC 读取模拟值
            if Config.USE_ADC and self.i2c_bus and self._adc_ok and not self._adc_disabled:
                try:
                    value = self._read_ads1115_raw(Config.MQ2_ANALOG_CHANNEL)
                    return value > Config.SMOKE_THRESHOLD_ANALOG
                except Exception as e:
                    logging.error(f"ADC 读取失败: {e}")
            elif Config.USE_ADC and not self.i2c_bus:
                logging.warning("已启用 ADC，但 I2C 未就绪；将回退为数字 DO 读取")
            
            # 降级到数字引脚读取
            if self._gpio_ok:
                try:
                    state = GPIO.input(self.mq2_pin)
                    return state == Config.SMOKE_DETECTED_VALUE
                except Exception:
                    return False
            return False
        else:
            # 模拟模式
            return False

    def get_mq2_value(self):
        """获取 MQ-2 的原始模拟值 (用于前端显示波形等)"""
        if _LIBS_AVAILABLE and Config.USE_ADC and self.i2c_bus and self._adc_ok and not self._adc_disabled:
            try:
                return self._read_ads1115_raw(Config.MQ2_ANALOG_CHANNEL)
            except Exception:
                return 0
        if _LIBS_AVAILABLE and Config.USE_ADC and not self.i2c_bus:
            return -1
        return 0

    def cleanup(self):
        if _LIBS_AVAILABLE:
            if self.dht_device:
                try:
                    self.dht_device.exit()
                except Exception:
                    pass
            try:
                GPIO.cleanup()
            except Exception:
                pass
        if self.i2c_bus:
            try:
                self.i2c_bus.close()
            except Exception:
                pass

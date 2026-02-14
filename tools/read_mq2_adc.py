import time

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from hardware.sensors import SensorManager


def main():
    sensors = SensorManager()
    try:
        print(f"USE_ADC={Config.USE_ADC} I2C_BUS={getattr(Config, 'I2C_BUS', None)} ADS1115_ADDRESS={hex(getattr(Config, 'ADS1115_ADDRESS', 0x48))}")
        while True:
            mq2_value = sensors.get_mq2_value()
            mq2_detected = sensors.read_mq2()
            print(f"mq2_value={mq2_value} smoke_detected={mq2_detected}")
            time.sleep(0.5)
    finally:
        sensors.cleanup()


if __name__ == "__main__":
    main()

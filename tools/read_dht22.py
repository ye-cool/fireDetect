import time

from hardware.sensors import SensorManager


def main():
    sensors = SensorManager()
    try:
        while True:
            t, h = sensors.read_dht22()
            print(f"temperature={t} humidity={h}")
            time.sleep(1)
    finally:
        sensors.cleanup()


if __name__ == "__main__":
    main()


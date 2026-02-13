# 树莓派硬件连接超详细图文指南

本指南将手把手教你如何将传感器连接到树莓派 5。请仔细阅读，**接错线可能会烧坏主板！**

## 1. 认识树莓派 GPIO 引脚

将树莓派有 USB 接口的一侧对着自己，双排 GPIO 针脚在上方。

- **最左上角**的引脚是 **Pin 1 (3.3V)**，它是个方块形的焊盘（如果看背面的话），通常旁边印有 P1。
- **Pin 1** 的右边是 **Pin 2 (5V)**。
- 下图是前 20 个引脚的定义（只需关注我们要用的）：

```
[树莓派边缘]
-----------------------------------------
(3.3V) Pin 1  | . . | Pin 2  (5V)   <-- 给MQ-2供电
(GPIO2)Pin 3  | . . | Pin 4  (5V)
(GPIO3)Pin 5  | . . | Pin 6  (GND)  <-- DHT22 地线
(GPIO4)Pin 7  | . . | Pin 8  (TXD)  <-- DHT22 数据线
(GND)  Pin 9  | . . | Pin 10 (RXD)  <-- MQ-2 地线
(GPIO17)Pin11 | . . | Pin 12 (GPIO18)<-- MQ-2 数据线
...
-----------------------------------------
```

---

## 2. 详细接线方案 (方案 B: 利用多引脚供电)

由于 DHT22 和 ADS1115 都需要 3.3V 供电，而 Pin 1 只有一个，我们利用树莓派上的第二个 3.3V 引脚 (Pin 17) 来解决冲突。

### A. DHT22 温湿度传感器 (接 Pin 1)
*   **VCC (+)** --> **Pin 1 (3.3V)** [左上角第1根]
*   **GND (-)** --> **Pin 6 (GND)** [上排第3根]
*   **DAT (Out)** --> **Pin 7 (GPIO 4)** [下排第4根]

### B. ADS1115 ADC 模块 (接 Pin 17)
*   **VDD** --> **Pin 17 (3.3V)** [左边一列，从上往下数第9根]
*   **GND** --> **Pin 14 (GND)** [上排第7根] (或者任意其他GND)
*   **SCL** --> **Pin 5 (GPIO 3/SCL)** [左边一列，从上往下数第3根]
*   **SDA** --> **Pin 3 (GPIO 2/SDA)** [左边一列，从上往下数第2根]
*   **ADDR** --> **GND** (和上面的GND连在一起，或者接Pin 20/25等任意GND)
*   **A0** --> 接 **MQ-2 的 AO 引脚**

### C. MQ-2 烟雾传感器
*   **VCC** --> **Pin 2 (5V)** [上排第2根]
*   **GND** --> **Pin 9 (GND)** [下排第5根]
*   **AO (模拟输出)** --> 接 **ADS1115 的 A0**
*   **DO (数字输出)** --> **不接** (已废弃)

### D. 摄像头
*   **USB 摄像头** --> 任意蓝色 USB 3.0 接口
*   **或者 CSI 摄像头** --> CAMERA 接口

---

## 3. 引脚图示参考

```
[树莓派边缘 - 远离USB口的一侧]
(3.3V) Pin 1  [DHT22 VCC] | . . | Pin 2  (5V)   [MQ-2 VCC]
(SDA)  Pin 3  [ADS SDA]   | . . | Pin 4  (5V)
(SCL)  Pin 5  [ADS SCL]   | . . | Pin 6  (GND)  [DHT22 GND]
(GPIO4)Pin 7  [DHT22 DAT] | . . | Pin 8  (TXD)
(GND)  Pin 9  [MQ-2 GND]  | . . | Pin 10 (RXD)
(GPIO17)Pin11             | . . | Pin 12 (GPIO18)
(GPIO27)Pin13             | . . | Pin 14 (GND)  [ADS GND]
(GPIO22)Pin15             | . . | Pin 16 (GPIO23)
(3.3V) Pin 17 [ADS VDD]   | . . | Pin 18 (GPIO24)
...
```

---

## 4. 连接摄像头

### 选项 A: USB 摄像头
直接插入树莓派任意一个 USB 接口（推荐蓝色的 USB 3.0 接口）。

### 选项 B: CSI 摄像头 (15-pin 宽排线)
如果你使用的是树莓派 4B，它的摄像头接口是 **Standard CSI (15-pin)**，这种接口比树莓派 5/Zero 的宽。

1.  **找到接口**: 树莓派 4B 上有两个相似的接口，一个是 `DISPLAY` (靠近USB口)，一个是 `CAMERA` (在 HDMI 接口和音频接口之间)。请插在 **CAMERA** 接口上！
2.  **连接步骤**:
    *   轻轻拨起接口上的黑色卡扣。
    *   将排线插入，**蓝色胶带面朝向以太网/USB接口方向** (也就是金属触点朝向 HDMI 接口方向)。
    *   按下卡扣固定。
3.  **系统配置**:
    *   旧版树莓派 OS (Bullseye之前) 需要 `raspi-config` -> Interface Options -> Legacy Camera -> Enable。
    *   新版 OS (Bookworm/Bullseye) 默认使用 `libcamera`，通常插上就能用。
    *   如果无法识别，尝试编辑 `/boot/config.txt` (旧版) 或 `/boot/firmware/config.txt` (新版)，添加 `dtoverlay=ov5647` (如果是500万像素) 或 `dtoverlay=imx219` (如果是800万像素)。

---

## 5. 检查清单

在通电之前，请进行最后的“灵魂三问”：

1.  **VCC 和 GND 反了吗？** (接反必烧模块，甚至烧树莓派)
2.  **5V 连到 3.3V 针脚了吗？** (严禁将 5V 电源线碰到 3.3V 或 GPIO 针脚)
3.  **线头有裸露接触吗？** (防止短路)

确认无误后，给树莓派通电开机。

---

## 6. 软件测试

连接好后，在树莓派终端运行这个简单的 Python 脚本测试一下（在 `fireDetect` 目录下）：

```python
# test_gpio.py
import RPi.GPIO as GPIO
import time

# 设置模式
GPIO.setmode(GPIO.BCM)

# 定义引脚
MQ2_PIN = 17

# 设置输入
GPIO.setup(MQ2_PIN, GPIO.IN)

try:
    while True:
        status = GPIO.input(MQ2_PIN)
        print(f"MQ-2 状态: {status} (0代表有烟, 1代表正常)") # 具体0/1定义看模块
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()
```

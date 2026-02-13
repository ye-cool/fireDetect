import cv2
import time
import logging
from config import Config

class CameraDriver:
    def __init__(self):
        self.camera_id = Config.CAMERA_ID
        self.cap = None
        self.is_open = False

    def start(self):
        try:
            # 优先尝试 Libcamera (树莓派 CSI 摄像头)
            # 在 OpenCV 中，通常使用 gstreamer 管道或者特定的 backend 来调用 libcamera
            # 但最简单的方法是尝试 index 0，如果树莓派 OS 配置正确 (dtoverlay=imx219等)，OpenCV 也能读取
            
            # 尝试打开摄像头 (USB 摄像头通常对应 index 0 或 1)
            # 如果同时插了 USB 和 CSI，USB 可能是 0 也可能是 1，建议先只插 USB 测试
            self.cap = cv2.VideoCapture(self.camera_id)
            
            # 检查是否成功
            if not self.cap.isOpened():
                logging.info(f"无法打开默认ID {self.camera_id}，尝试遍历 ID 0-5...")
                for i in range(5):
                    if i == self.camera_id: continue
                    temp_cap = cv2.VideoCapture(i)
                    if temp_cap.isOpened():
                        logging.info(f"成功打开摄像头 ID {i}")
                        self.cap = temp_cap
                        self.camera_id = i
                        break
            
            if not self.cap.isOpened():
                logging.warning(f"无法打开任何摄像头，尝试使用模拟模式")
                self.is_open = False
            else:
                self.is_open = True
                # 设置分辨率，降低负载
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                # 设置 FPS 为 15，避免摄像头采集占用过高带宽和CPU
                self.cap.set(cv2.CAP_PROP_FPS, 15)
                # 设置缓冲区大小，减少延迟
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception as e:
            logging.error(f"摄像头初始化失败: {e}")
            self.is_open = False

    def get_frame(self):
        """获取当前帧，如果摄像头未打开则返回None或黑图"""
        if self.is_open and self.cap:
            ret, frame = self.cap.read()
            if ret:
                return frame
        
        # 模拟模式：如果没有摄像头，返回None，业务层处理
        return None

    def release(self):
        if self.cap:
            self.cap.release()
            self.is_open = False

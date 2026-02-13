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
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                logging.warning(f"无法打开摄像头 ID {self.camera_id}，尝试使用模拟模式")
                self.is_open = False
            else:
                self.is_open = True
                # 设置分辨率，降低负载
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
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

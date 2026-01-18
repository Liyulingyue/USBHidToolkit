import cv2
import threading
import time

class CameraService:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.latest_frame = None
        self.is_running = False
        self._lock = threading.Lock()

    def start(self):
        if self.is_running:
            return
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise Exception(f"Could not open camera {self.camera_index}")
        
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self):
        while self.is_running:
            ret, frame = self.cap.read()
            if ret:
                with self._lock:
                    self.latest_frame = frame
            time.sleep(0.01) # 控制采样率

    def get_frame(self):
        with self._lock:
            return self.latest_frame

    def stop(self):
        self.is_running = False
        if self.cap:
            self.cap.release()

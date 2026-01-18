import cv2
import numpy as np
import mss
from flask import Flask, Response
import time

app = Flask(__name__)

# 配置
FPS = 15  # 限制帧率以减轻网络负担
QUALITY = 70  # JPEG 编码质量

def generate_frames():
    with mss.mss() as sct:
        # 获取第一块显示器
        monitor = sct.monitors[1]
        
        while True:
            start_time = time.time()
            
            # 截取屏幕，包含鼠标光标
            img = np.array(sct.grab(monitor, include_cursor=True))
            
            # mss 抓取的是 BGRA，转换为 BGR 供 OpenCV 使用
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 如果屏幕太大，可以考虑缩放以降低带宽
            # frame = cv2.resize(frame, (1280, 720))

            # 编码为 JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, QUALITY])
            if not ret:
                continue
                
            frame_bytes = buffer.tobytes()
            
            # 使用 MJPEG 格式输出
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # 控制帧率
            process_time = time.time() - start_time
            sleep_time = max(0, (1.0 / FPS) - process_time)
            time.sleep(sleep_time)

@app.route('/stream')
def video_feed():
    """MJPEG 视频流路由"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return "Screen Streamer is Running. Access /stream for MJPEG."

if __name__ == '__main__':
    # 启动服务器。注意：由于是屏幕共享，默认只监听本地。
    # 如果 Agent 在另一台机器，请改为 host='0.0.0.0'
    print("Starting Screen Streamer on port 5001...")
    print("Access the stream at http://localhost:5001/stream")
    app.run(host='0.0.0.0', port=5001, threaded=True)

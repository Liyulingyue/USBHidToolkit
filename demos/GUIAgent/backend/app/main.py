from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from .camera import CameraService
from .hid import hid_service
from .agent import GUIAgent
import cv2
import base64
import asyncio

app = FastAPI()

# ... existing CORS middleware ...

camera = CameraService(camera_index=0)
gui_agent = GUIAgent(camera)

@app.on_event("startup")
async def startup_event():
    camera.start()

@app.on_event("shutdown")
async def shutdown_event():
    camera.stop()

@app.get("/")
def read_root():
    return {"status": "GUIAgent Backend Running"}

@app.websocket("/ws/video")
async def video_feed(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            frame = camera.get_frame()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    base64_frame = base64.b64encode(buffer).decode('utf-8')
                    await websocket.send_text(base64_frame)
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        print("Client disconnected from video feed")

@app.post("/connect")
def connect_hid(config: dict):
    res = hid_service.connect(config['host'], config.get('port', 80))
    return {"message": res}

@app.post("/agent/task")
async def start_task(data: dict):
    # data: {"goal": "打开浏览器"}
    if gui_agent.is_running:
        return {"status": "error", "message": "Agent is already thinking"}
    
    result = await gui_agent.think_and_act(data['goal'])
    return {"status": "success", "data": result}

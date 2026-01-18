from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from .camera import CameraService
from .hid import hid_service
from .agent import GUIAgent
import cv2
import base64
import asyncio

app = FastAPI()

# 必须启用 CORS，否则前端 OPTIONS 请求会失败
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os

# 从环境变量读取摄像头源，可以是索引 0 或 URL
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")
if CAMERA_SOURCE.isdigit():
    CAMERA_SOURCE = int(CAMERA_SOURCE)

camera = CameraService(camera_source=CAMERA_SOURCE)
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
    # config: {"host": "192.168.2.121", "port": 80}
    success, message = hid_service.connect(config['host'], config.get('port', 80))
    if success:
        return {"status": "success", "message": message}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=message)

@app.websocket("/ws/agent")
async def agent_task_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 等待前端发送任务目标
            data = await websocket.receive_json()
            goal = data.get('goal')
            max_steps = data.get('max_steps', 10)
            
            if not goal:
                continue

            if gui_agent.is_running:
                await websocket.send_json({"status": "error", "message": "Agent is already busy"})
                continue

            print(f"[WS Agent] 开始任务: {goal}")
            
            for i in range(max_steps):
                # 思考并执行一步
                result = await gui_agent.think_and_act(goal)
                
                # 立即将这一步的结果发给前端
                await websocket.send_json({
                    "status": "step",
                    "step": i + 1,
                    "data": result
                })
                
                if result.get("status") == "finished":
                    break
                
                if "error" in result:
                    break
                
                await asyncio.sleep(0.5)
            
            await websocket.send_json({"status": "completed"})
            
    except WebSocketDisconnect:
        print("Agent WS disconnected")
    except Exception as e:
        print(f"Agent WS Error: {e}")

@app.post("/agent/task")
async def start_task(data: dict):
    """
    保留原 HTTP 接口供非 WS 场景使用。
    """
    if gui_agent.is_running:
        return {"status": "error", "message": "Agent is already busy"}
    
    goal = data.get('goal')
    result = await gui_agent.think_and_act(goal)
    return {"status": "success", "data": result}

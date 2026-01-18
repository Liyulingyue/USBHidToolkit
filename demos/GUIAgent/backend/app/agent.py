import os
import base64
import cv2
import httpx
import json
import asyncio
from dotenv import load_dotenv
from .camera import CameraService
from .hid import hid_service

load_dotenv()

class GUIAgent:
    def __init__(self, camera: CameraService):
        self.camera = camera
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.history = []
        self.is_running = False

    async def think_and_act(self, user_goal: str):
        self.is_running = True
        
        # 1. 采集当前画面
        frame = self.camera.get_frame()
        if frame is None:
            return "No camera frame available"

        # 2. 编码图片
        _, buffer = cv2.imencode('.jpg', frame)
        base64_image = base64.b64encode(buffer).decode('utf-8')

        # 3. 构造 Prompt
        prompt = f"""
你是一个操作电脑桌面的智能体。你现在通过摄像头观察用户的屏幕。
用户目标："{user_goal}"

你可以观察屏幕画面，并决定下一步动作。
由于连接的是 USB HID 设备，你只能执行【相对移动】。

请输出 JSON 格式：
{{
    "thought": "你的思考过程，包括观察到了什么，对比上一步移动是否到位",
    "action": "move" | "click" | "type" | "wait",
    "params": {{
        "dx": 整数 (x轴位移),
        "dy": 整数 (y轴位移),
        "button": "left" | "right",
        "text": "要输入的文本"
    }}
}}
注意：如果目标还没对准，先使用 move。如果已经对准，使用 click。
"""

        # 4. 请求 VLM
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            "response_format": { "type": "json_object" }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                res_data = response.json()
                content = res_data['choices'][0]['message']['content']
                decision = json.loads(content)
                
                # 5. 执行动作并返回
                await self._execute(decision)
                return decision

        except Exception as e:
            return {"error": str(e)}
        finally:
            self.is_running = False

    async def _execute(self, decision):
        action = decision.get("action")
        params = decision.get("params", {})

        if action == "move":
            hid_service.execute_mouse_relative(params.get("dx", 0), params.get("dy", 0))
        elif action == "click":
            hid_service.execute_mouse_click(params.get("button", "left"))
        elif action == "type":
            for char in params.get("text", ""):
                hid_service.execute_keyboard_tap(char)
                await asyncio.sleep(0.05)
        
        # 执行动作后的冷却等待，确保下一帧画面能反映变化
        await asyncio.sleep(0.5)

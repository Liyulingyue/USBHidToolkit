import os
import base64
import cv2
import httpx
import json
import asyncio
import re
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
        self.history = [] # 记录最近几次的动作与思考，实现闭环反思
        self.is_running = False

    async def think_and_act(self, user_goal: str):
        self.is_running = True
        
        # 1. 采集当前画面
        frame = self.camera.get_frame()
        if frame is None:
            return {"error": "No camera frame available"}

        # 2. 编码图片
        _, buffer = cv2.imencode('.jpg', frame)
        base64_image = base64.b64encode(buffer).decode('utf-8')

        # 3. 构造带历史信息的 Prompt
        history_text = ""
        if self.history:
            history_text = "\n最近动作记录：\n" + "\n".join([
                f"- 动作: {h['action']}, 位移: {h.get('params',{}).get('dx')},{h.get('params',{}).get('dy')}, 思考: {h['thought'][:50]}..."
                for h in self.history[-3:] # 提供最近3步作为参考
            ])

        prompt = f"""
你是一个专业的视觉控制智能体。你通过摄像头观察物理主机的屏幕画面，并控制一套额外的 HID 键鼠设备。
用户目标："{user_goal}"
{history_text}

【操作规范】：
由于物理移动可能存在比例误差，请采用“观察-决策-反思”闭环模式：
1. **现状识别**：当前鼠标指针在画面的坐标（大致位置）？目标元素在哪里？
2. **误差对比**：如果之前有过移动，对比上图，鼠标是否精准到达了你预期的位置？
3. **精准打击**：根据误差调整 dx, dy。
4. **状态确认**：若已点击目标并看到窗口弹出/变化，请使用 "finish"。

请务必回复一个 ```json ``` 代码块：
```json
{{
    "thought": "你的详细反思：观察到了什么 -> 之前动作是否有偏差 -> 本次计划如何修正",
    "action": "move" | "click" | "type" | "wait" | "finish",
    "params": {{
        "dx": 整数 (x轴像素位移),
        "dy": 整数 (y轴像素位移),
        "button": "left" | "right",
        "text": "要输入的文本"
    }}
}}
```
注意：单次移动 dx/dy 建议控制在 [-400, 400] 内。
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
            # 移除强制 JSON 模式，允许模型自由发挥但通过 Markdown 包裹关键数据
        }

        try:
            print(f"\n[Agent] 正在请求 VLM (Model: {self.model})...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    print(f"[Agent] API 请求失败！状态码: {response.status_code}")
                    return {"error": f"API Error {response.status_code}"}

                res_data = response.json()
                raw_content = res_data['choices'][0]['message']['content']
                print(f"[Agent] 模型原始回复: \n{raw_content}")

                # 解析内容：提取 ```json ... ``` 之间的内容
                try:
                    json_match = re.search(r'```json\s*(.*?)\s*```', raw_content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1).strip()
                    else:
                        # 兜底：尝试寻找第一个 { 和最后一个 }
                        content_match = re.search(r'(\{.*\})', raw_content, re.DOTALL)
                        content = content_match.group(1) if content_match else raw_content
                    
                    # 针对 Ernie 连续输出对象的兜底处理（如有必要）
                    if "}{" in content or "}\s*{" in content:
                         content = re.sub(r'\}\s*\{', '},{', content)
                         if not content.startswith("["): content = f"[{content}]"

                    decision_data = json.loads(content)
                    decisions = decision_data if isinstance(decision_data, list) else [decision_data]
                except Exception as parse_err:
                    print(f"[Agent] 解析失败! Content: {raw_content}")
                    return {"error": "Parse error"}

                last_decision = {"status": "processing"}
                for decision in decisions:
                    print(f"[Agent] 思考: {decision.get('thought')}")
                    print(f"[Agent] 执行: {decision.get('action')} {decision.get('params')}")
                    
                    if decision.get('action') == 'finish':
                        print("[Agent] 任务完成。")
                        return {"status": "finished", "thought": decision.get('thought')}
                    
                    await self._execute(decision)
                    # 将本次动作存入历史记录，供下一轮思考
                    self.history.append(decision)
                    last_decision = decision
                    if len(decisions) > 1: await asyncio.sleep(0.3)

                return last_decision

        except Exception as e:
            print(f"[Agent] 发生未预期错误: {str(e)}")
            import traceback
            traceback.print_exc()
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

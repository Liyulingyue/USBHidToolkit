import os
import base64
import cv2
import httpx
import json
import asyncio
import re
import ast
from dotenv import load_dotenv
from .camera import CameraService
from .hid import hid_service

load_dotenv()

class GUIAgent:
    def __init__(self, camera: CameraService):
        self.camera = camera
        
        # 基础配置 (用于单模型模式)
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # 布局感知模型 (Layout model, e.g. ShowUI)
        self.layout_base_url = os.getenv("LAYOUT_BASE_URL")
        self.layout_api_key = os.getenv("LAYOUT_API_KEY")
        self.layout_model = os.getenv("LAYOUT_MODEL")
        
        # 决策推理模型 (Reasoner model, e.g. Ernie, GPT-4o)
        self.reasoner_base_url = os.getenv("REASONER_BASE_URL")
        self.reasoner_api_key = os.getenv("REASONER_API_KEY")
        self.reasoner_model = os.getenv("REASONER_MODEL")
        
        self.history = [] # 记录最近几次的动作与思考，实现闭环反思
        self.is_running = False

    async def think_and_act(self, user_goal: str):
        self.is_running = True
        try:
            # 1. 采集当前画面
            frame = self.camera.get_frame()
            if frame is None:
                return {"error": "No camera frame available"}

            # 2. 编码图片
            _, buffer = cv2.imencode('.jpg', frame)
            base64_image = base64.b64encode(buffer).decode('utf-8')

            # 3. 构造历史信息
            history_text = ""
            if self.history:
                history_text = "\n最近动作记录：\n" + "\n".join([
                    f"- 动作: {h.get('action')}, 思考: {h.get('thought','')[:50]}..."
                    for h in self.history[-3:]
                ])

            raw_content = ""
            
            # 判断是否进入混合模式 (Hybrid Mode)
            if self.layout_model and self.reasoner_model:
                print(f"\n[Agent] 进入混合模式: Layout({self.layout_model}) + Reasoner({self.reasoner_model})")
                
                # --- 第一阶段: 规划 (Planning) ---
                # 推理模型先理解任务，确定需要交互的元素或位置
                plan_prompt = f"""你是一个 GUI 操作规划器。基于用户目标和屏幕画面，分析需要的具体操作步骤。

用户目标："{user_goal}"
{history_text}

请分析并返回 ```json``` 代码块，包括：
1. 需要定位的目标UI元素（与任务相关）
2. 参考元素（如当前鼠标指针位置，用于计算相对位移）

格式如下：
```json
[
    {{
        "target_element": "目标UI元素的名称（如'关闭按钮'、'搜索框'）",
        "description": "这个元素的特征描述（如'通常位于窗口右上角，呈现为X图标'）",
        "action": "CLICK|INPUT|ENTER|SCROLL|etc",
        "is_reference": false
    }},
    {{
        "target_element": "鼠标指针",
        "description": "当前屏幕上的鼠标指针位置",
        "action": "NONE",
        "is_reference": true
    }}
]
```

示例：
```json
[
    {{
        "target_element": "close button",
        "description": "typically a small X icon at the top-right corner of the window",
        "action": "CLICK",
        "is_reference": false
    }},
    {{
        "target_element": "mouse cursor",
        "description": "the current position of the mouse pointer on the screen",
        "action": "NONE",
        "is_reference": true
    }}
]
```

注意：必须包括鼠标指针位置，这样执行阶段才能精确计算相对位移。
"""
                async with httpx.AsyncClient() as client:
                    plan_payload = {
                        "model": self.reasoner_model,
                        "messages": [{"role": "user", "content": plan_prompt}]
                    }
                    headers = {"Authorization": f"Bearer {self.reasoner_api_key or self.api_key}", "Content-Type": "application/json"}
                    plan_resp = await client.post(f"{self.reasoner_base_url or self.base_url}/chat/completions", 
                                                  headers=headers,
                                                  json=plan_payload, timeout=60.0)
                    plan_text = plan_resp.json()['choices'][0]['message']['content'] if plan_resp.status_code == 200 else ""
                    print(f"[Agent] 规划步骤:\n{plan_text}")
                    
                    # 提取规划中的 JSON
                    import re
                    plan_json_match = re.search(r'```json\s*(.*?)\s*```', plan_text, re.DOTALL)
                    plan_info = plan_json_match.group(1).strip() if plan_json_match else plan_text

                # --- 第二阶段: 定位 (Grounding with ShowUI) ---
                # 为每个规划中的元素定位坐标
                locations = {}
                try:
                    plan_list = json.loads(plan_info)
                except:
                    plan_list = []
                
                if isinstance(plan_list, list):
                    for element in plan_list:
                        if not isinstance(element, dict):
                            continue
                        target_name = element.get("target_element", "")
                        description = element.get("description", "")
                        
                        # 为每个元素单独调用 ShowUI
                        query = f"Find: {target_name}\nDescription: {description}"
                        element_location = await self._get_layout_info(base64_image, query)
                        locations[target_name] = element_location
                        print(f"[Agent] 定位 '{target_name}': {element_location}")
                
                layout_info = json.dumps(locations, ensure_ascii=False)
                print(f"[Agent] 所有元素定位结果:\n{layout_info}\n" + "-"*30)

                # --- 第三阶段: 执行 (Execution) ---
                # 推理模型根据规划和坐标，精确计算位移并执行
                exec_prompt = f"""你是一个 GUI 操作执行器。基于规划、视觉定位结果和屏幕画面，精确计算并执行操作。

用户目标："{user_goal}"

操作规划：
{plan_info}

视觉定位结果（ShowUI 返回的目标坐标，归一化 0-1）：
{layout_info}

【坐标系统】：
- 定位结果中的坐标 [x, y] 是归一化坐标（0-1范围）
- 屏幕分辨率：1920x1080
- 转换公式：pixel_x = x * 1920, pixel_y = y * 1080

【执行策略】：
1. 根据定位结果找到"鼠标指针"的当前位置
2. 根据定位结果找到目标元素的位置
3. 精确计算 dx = target_pixel_x - cursor_pixel_x，dy = target_pixel_y - cursor_pixel_y
4. 如果位移超过 250 像素，分步执行但保持正确方向

返回操作指令，格式为：
```json
[
    {{
        "thought": "根据鼠标位置 [cursor_x, cursor_y] 和目标位置 [target_x, target_y]，计算位移逻辑",
        "action": "CLICK" | "INPUT" | "ENTER" | "FINISH",
        "dx": 像素位移,
        "dy": 像素位移,
        "value": "输入内容（仅INPUT需要）"
    }}
]
```
"""
                raw_content = await self._get_reasoner_decision(exec_prompt)
                print(f"[Agent] 执行指令: \n{raw_content}")

            else:
                # --- 单模型传统模式 (Original Mode) ---
                print(f"\n[Agent] 正在请求单模型 VLM (Model: {self.model})...")
                model_str = (self.model or "").lower()
                is_showui = "showui" in model_str
                
                if is_showui:
                    system_prompt = """You are an AI assistant controlling a real mouse via relative movements (dx, dy).
You see the current screen image. You need to identify where the mouse cursor IS and where it SHOULD BE.

Action Space:
1. CLICK: Click the current position. 
2. INPUT: Type 'value'.
3. ENTER: Press enter.
4. FINISH: Task completed.

IMPORTANT: Because our hardware uses RELATIVE movement, you MUST include "dx" and "dy" in pixels.
MUST return your response in a ```json code block.
Format your response as:
```json
[
  {'thought': 'current mouse is at [100, 100], target is [200, 300], so dx=100, dy=200', 'action': 'CLICK', 'dx': 100, 'dy': 200}
]
```
"""
                    prompt = f"{system_prompt}\n\nTask: {user_goal}\n{history_text}"
                else:
                    prompt = f"""你是一个智能视觉助手，通过观察屏幕截图来操作电脑。
你不能直接看到坐标，但你可以通过观察鼠标指针的位置来决定如何移动。

用户目标: "{user_goal}"
{history_text}

请在```json代码块中返回一个 JSON 列表。每个对象必须包含：
- thought: 你的思考过程，说明你看到了什么，鼠标在哪，目标在哪。
- action: 动作类型 ("CLICK", "INPUT", "ENTER", "WAIT", "FINISH")。
- dx, dy: 鼠标的相对位移像素值（例如：dx: 100 表示向右移动100像素）。
- value: 如果是 INPUT，请输入字符串内容。

示例格式:
```json
[
  {{"thought": "我看到任务栏图标在右侧，当前鼠标在中间。我需要向右移动并点击。", "action": "CLICK", "dx": 200, "dy": 0}}
]
```
"""
                raw_content = await self._get_vlm_response(prompt, base64_image)
                print(f"[Agent] VLM 原始回复: \n{raw_content}")

            # 4. 解析与执行
            return await self._parse_and_execute_content(raw_content, user_goal)

        except Exception as e:
            print(f"[Agent] 发生未预期错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
        finally:
            self.is_running = False

    async def _get_layout_info(self, base64_image, user_goal):
        """调用 Layout 模型 (ShowUI) 结合用户目标提取 UI 信息
        参考 ShowUI 官方文档的 UI Grounding 模式
        """
        headers = {"Authorization": f"Bearer {self.layout_api_key or self.api_key}", "Content-Type": "application/json"}
        
        # 使用官方推荐的 UI Grounding System Prompt
        system_prompt = "Based on the screenshot of the page, I give a text description and you give its corresponding location. The coordinate represents a clickable location [x, y] for an element, which is a relative coordinate on the screenshot, scaled from 0 to 1."
        
        payload = {
            "model": self.layout_model,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": system_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                {"type": "text", "text": user_goal}
            ]}]
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.layout_base_url}/chat/completions", headers=headers, json=payload, timeout=60.0)
                if resp.status_code == 200:
                    content = resp.json()['choices'][0]['message']['content']
                    return content
                return f"Error: {resp.status_code}"
        except Exception as e:
            return f"Layout Error: {str(e)}"

    async def _get_reasoner_decision(self, prompt):
        """调用推理模型做出决策"""
        headers = {"Authorization": f"Bearer {self.reasoner_api_key or self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.reasoner_model,
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.reasoner_base_url or self.base_url}/chat/completions", headers=headers, json=payload, timeout=60.0)
                if resp.status_code == 200:
                    return resp.json()['choices'][0]['message']['content']
                return f"Error: {resp.status_code}"
        except Exception as e:
            return f"Reasoner Error: {str(e)}"

    async def _get_vlm_response(self, prompt, base64_image):
        """单 VLM 模式下的原始请求"""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}]
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=60.0)
                if resp.status_code == 200:
                    return resp.json()['choices'][0]['message']['content']
                return f"Error: {resp.status_code}"
        except Exception as e:
            return f"VLM Error: {str(e)}"

    async def _parse_and_execute_content(self, content, user_goal):
        try:
            # 尝试提取代码块
            json_match = re.search(r'```(?:json|python)?\s*(.*?)\s*```', content, re.DOTALL)
            clean_content = json_match.group(1).strip() if json_match else content.strip()
            
            decisions = []
            try:
                parsed = ast.literal_eval(clean_content)
                if isinstance(parsed, list): decisions = parsed
                elif isinstance(parsed, tuple): decisions = list(parsed)
                else: decisions = [parsed]
            except Exception:
                # 兜底：寻找多个 {}
                potential_dicts = re.findall(r'\{[^{}]*\}', clean_content)
                for d_str in potential_dicts:
                    try: decisions.append(ast.literal_eval(d_str))
                    except: continue
            
            if not decisions:
                return {"error": "Could not parse any valid actions"}

            last_result = None
            for decision in decisions:
                if not isinstance(decision, dict): continue
                
                action = str(decision.get('action', '')).upper()
                if action == 'FINISH':
                    return {"status": "finished", "thought": decision.get('thought')}
                
                last_result = await self._execute(decision)
                self.history.append(decision)
                await asyncio.sleep(0.5)
            
            return last_result or {"status": "empty"}
            
        except Exception as e:
            return {"error": f"Parse/Exec Error: {str(e)}"}

    async def _execute(self, decision):
        action = str(decision.get("action", "")).upper()
        params = decision.get("params", {})
        
        def get_p(key, default=None):
            return decision.get(key, params.get(key, default))

        print(f"[Agent] 执行动作: {action}")
        if not hid_service.client:
            return {"error": "HID not connected"}

        try:
            dx = get_p("dx")
            dy = get_p("dy")
            if dx is not None or dy is not None:
                dx, dy = int(dx or 0), int(dy or 0)
                # 硬件限制通常单次较小，这里做个保护
                dx, dy = max(-400, min(400, dx)), max(-400, min(400, dy))
                print(f"[Agent] 执行位移: dx={dx}, dy={dy}")
                hid_service.execute_mouse_relative(dx, dy)
                await asyncio.sleep(0.2)

            if action in ["CLICK", "TAP"]:
                hid_service.execute_mouse_click(get_p("button", "left"))
                await asyncio.sleep(0.8)
            elif action in ["TYPE", "INPUT"]:
                text = get_p("text") or get_p("value", "")
                for char in str(text):
                    hid_service.execute_keyboard_tap(char)
                    await asyncio.sleep(0.05)
            elif action == "ENTER":
                hid_service.execute_keyboard_tap("\n")
            elif action == "WAIT":
                await asyncio.sleep(float(get_p("seconds", 1.0)))
            
            return {"status": "success", "action": action}
        except Exception as e:
            return {"error": f"HID execution error: {str(e)}"}

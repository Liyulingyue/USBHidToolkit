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
2. **坐标系说明**：
   - 屏幕左上角是坐标原点 (0,0)
   - dx > 0 表示向右移动，dx < 0 表示向左移动
   - dy > 0 表示向下移动，dy < 0 表示向上移动
   - 关闭按钮通常在屏幕右上角，需要 dx > 0, dy < 0 的组合移动
3. **误差对比**：如果之前有过移动，对比上图，鼠标是否精准到达了你预期的位置？
4. **视觉验证**：执行点击后，必须观察屏幕是否有预期变化（如窗口关闭、页面变化），如果没有变化则需要重新定位。**只有当你确信看到目标结果时，才使用 "finish"**。
5. **小步快跑**：单次移动不要超过 200 像素，避免超出屏幕边界。

请务必回复一个 ```json ``` 代码块：
```json
[
    {{
        "thought": "你的详细反思：观察到了什么 -> 之前动作是否有偏差 -> 本次计划如何修正（明确dx/dy的方向和意义）",
        "action": "move" | "click" | "type" | "wait" | "finish",
        "params": {{
            "dx": 整数 (x轴像素位移，正右负左，建议-200到200之间),
            "dy": 整数 (y轴像素位移，正下负上，建议-200到200之间),
            "button": "left" | "right",
            "text": "要输入的文本"
        }}
    }}
]
```
注意：移动后要观察鼠标位置是否到达预期，点击后要确认是否有视觉反馈。如果只需要一步操作，返回单个对象的数组。
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
                    
                    print(f"[Agent] 提取的 JSON 内容: {content}")
                    
                    # 处理多种可能的格式
                    if content.startswith('[') and content.endswith(']'):
                        # 已经是数组格式
                        decision_data = json.loads(content)
                    elif '},{' in content or '}\s*,?\s*{' in content:
                        # 多个对象用逗号分隔，包装成数组
                        content = re.sub(r'}\s*,?\s*{', '},{', content)
                        if not content.startswith('['):
                            content = f"[{content}]"
                        print(f"[Agent] 修复后的数组格式: {content}")
                        decision_data = json.loads(content)
                    else:
                        # 单个对象
                        decision_data = json.loads(content)
                        if isinstance(decision_data, dict):
                            decision_data = [decision_data]
                    
                    decisions = decision_data if isinstance(decision_data, list) else [decision_data]
                except Exception as parse_err:
                    print(f"[Agent] 解析失败! Content: {raw_content}")
                    return {"error": "Parse error"}

                last_decision = {"status": "processing"}
                for decision in decisions:
                    print(f"[Agent] 思考: {decision.get('thought')}")
                    print(f"[Agent] 执行: {decision.get('action')} {decision.get('params')}")
                    
                    if decision.get('action') == 'finish':
                        # 在宣布完成前，进行最终的视觉验证
                        print("[Agent] 模型认为任务完成，进行最终视觉验证...")
                        await asyncio.sleep(1.0)  # 等待系统响应
                        
                        verification_frame = self.camera.get_frame()
                        if verification_frame is not None:
                            _, verification_buffer = cv2.imencode('.jpg', verification_frame)
                            verification_base64 = base64.b64encode(verification_buffer).decode('utf-8')
                            
                            verification_prompt = f"""
请验证任务"{user_goal}"是否真的完成了。观察当前屏幕：
- 如果浏览器确实关闭了，返回 "verified": true
- 如果浏览器还在，返回 "verified": false

{history_text}

```json
{{
    "verified": true | false,
    "reason": "你的判断理由"
}}
```"""

                            verification_payload = {
                                "model": self.model,
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "text", "text": verification_prompt},
                                            {
                                                "type": "image_url",
                                                "image_url": {"url": f"data:image/jpeg;base64,{verification_base64}"}
                                            }
                                        ]
                                    }
                                ]
                            }

                            try:
                                verification_response = await httpx.AsyncClient().post(
                                    f"{self.base_url}/chat/completions",
                                    headers=headers,
                                    json=verification_payload,
                                    timeout=20.0
                                )
                                
                                if verification_response.status_code == 200:
                                    verification_data = verification_response.json()
                                    verification_content = verification_data['choices'][0]['message']['content']
                                    
                                    verification_match = re.search(r'```json\s*(.*?)\s*```', verification_content, re.DOTALL)
                                    if verification_match:
                                        verification_result = json.loads(verification_match.group(1))
                                        if verification_result.get('verified'):
                                            print("[Agent] 视觉验证确认：任务完成！")
                                            return {"status": "finished", "thought": decision.get('thought')}
                                        else:
                                            print(f"[Agent] 视觉验证失败：{verification_result.get('reason')}，继续执行...")
                                            # 不返回 finish，继续下一轮思考
                                            continue
                            except Exception as e:
                                print(f"[Agent] 验证失败，继续执行: {e}")
                        
                        print("[Agent] 跳过验证，继续执行...")
                        continue
                    
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

        print(f"[Agent] 开始执行动作: {action}, 参数: {params}")
        
        # 检查 HID 服务状态
        if not hid_service.client:
            print("[Agent] 错误: HID 服务未连接或客户端为空")
            return False

        try:
            if action == "move":
                dx = params.get("dx", 0)
                dy = params.get("dy", 0)
                # 强制限制移动距离，避免超出屏幕边界
                dx = max(-200, min(200, dx))
                dy = max(-200, min(200, dy))
                print(f"[Agent] 执行鼠标位移: dx={dx}, dy={dy} (已限制在±200范围内)")
                result = hid_service.execute_mouse_relative(dx, dy)
                print(f"[Agent] 鼠标位移执行结果: {result}")
                
            elif action == "click":
                button = params.get("button", "left")
                print(f"[Agent] 执行鼠标点击: button={button}")
                result = hid_service.execute_mouse_click(button)
                print(f"[Agent] 鼠标点击执行结果: {result}")
                # 点击后等待更长时间，让系统响应
                await asyncio.sleep(1.0)
                
            elif action == "type":
                text = params.get("text", "")
                print(f"[Agent] 执行键盘输入: text='{text}'")
                for char in text:
                    result = hid_service.execute_keyboard_tap(char)
                    print(f"[Agent] 键盘敲击 '{char}' 执行结果: {result}")
                    await asyncio.sleep(0.05)
                    
            elif action == "wait":
                wait_time = params.get("seconds", 0.5)
                print(f"[Agent] 执行等待: {wait_time} 秒")
                await asyncio.sleep(wait_time)
                result = True
                
            else:
                print(f"[Agent] 未知动作类型: {action}")
                result = False
                
        except Exception as e:
            print(f"[Agent] 执行动作时发生异常: {str(e)}")
            import traceback
            traceback.print_exc()
            result = False
        
        print(f"[Agent] 动作 '{action}' 执行完成")
        
        # 执行动作后的冷却等待，确保下一帧画面能反映变化
        await asyncio.sleep(0.5)
        return result

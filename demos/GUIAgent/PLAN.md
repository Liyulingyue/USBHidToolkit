# GUIAgent 规划文档

本项目旨在通过 `USBHidToolkit` 结合视觉大语言模型 (VLM)，实现一个能够通过视觉反馈自动操作电脑桌面的智能代理。

## 1. 核心流程 (Loop)
1.  **感知 (Perceive)**: 后端通过摄像头捕获当前屏幕画面。
2.  **规划 (Plan)**: 将画面与用户目标（如："帮我点开浏览器"）发送给 VLM (如 GPT-4o 或 Claude 3.5 Sonnet)。
3.  **动作 (Act)**: VLM 返回坐标或指令，后端通过 `USBHidToolkit` 转换为 HID 指令并发送给硬件。
4.  **验证 (Verify)**: 重复感知步骤，确认动作是否生效，形成闭环。

## 2. 技术栈
-   **前端**: Vite + React + TypeScript + TailwindCSS (用于实时视频流监控、聊天对话框、动作日志)。
-   **后端**: FastAPI (提供 WebSocket 流传输画面，处理 LLM 请求，调用 HID 接口)。
-   **大模型**: OpenAI 格式的 Vision 接口 (支持自定义 Base URL，如 DeepSeek, GPT-4o 等)。
-   **智能体逻辑**: 采用原生 Python 或 LangGraph 实现状态管理。

## 3. 模块设计
-   **CameraService**: 负责从本地摄像头（可通过 OpenCV）读取画面并进行压缩。
-   **ActionExecutor**: 封装 `USBHidToolkit`，将 LLM 的相对/绝对坐标指令转换为鼠标/键盘报文。
-   **AgentEngine**: 管理思考链路 (Thinking process)。
-   **Frontend UI**: 
    -   中央区域：Canvas 实时显示摄像头画面。
    -   右侧区域：Agent 聊天窗口及思考状态（Thoughts）。
    -   控制栏：配置串口/网口 IP、API Key 等。

## 4. 关键挑战与待确认点 (Uncertainties)

### 4.1 视觉反馈尝试机制 (Visual Feedback Loop)
-   **策略**: 放弃复杂的几何坐标映射。
-   **方案**: 借鉴人类操作逻辑——观察 -> 小幅移动 -> 再次观察 -> 修正。
-   **实现**: Agent 发出一个移动指令（如“向右上方大幅移动”），执行后等待画面稳定，再次截图。Agent 对比前后两张图，意识到“移动得太多”或“方向偏了”，从而在下一轮中下达更精细的指令。

### 4.2 侧重“移动多少”而非“移动到哪”
-   **优势**: 完美契合 `USBHidToolkit` 的相对移动接口 (`client.mouse.move(x, y)`)。
-   **逻辑**: LLM 输出不再是 `(800, 600)` 这种坐标，而是 `{"direction": "right-down", "amount": "medium"}` 或者像素估值 `{"dx": 50, "dy": 20}`。

### 4.3 异步按需请求
-   **原则**: 拒绝高频轮询。
-   **流程**: 
    1. 用户发出任务指令。
    2. Agent 采集快照 A -> 发送给 VLM -> 决定动作。
    3. 执行动作（通过 `USBHidToolkit`）。
    4. **强制等待 (Cooling down)**: 等待（如 500ms）确保硬件执行完毕且视频流采集到运动后的画面。
    5. 采集快照 B -> 进入下一轮循环。

### 4.4 硬件与库集成
-   **原则**: **完全基于 `USBHidToolkit`**。
-   **意义**: 这是一个典型的“包应用”案例。演示如何导入 `USBHidClient` 并配合 AI 逻辑完成复杂的跨设备（开发机 -> 目标机）控制任务。

## 5. 开发蓝图
1.  **Step 1**: 实现 FastAPI 基础后端，负责 OpenCV 摄像头采集与 WebUI 的实时预览。
2.  **Step 3**: 编写 Agent 思考逻辑：一个“请求-执行-等待-重取样”的状态机，接入 OpenAI Vision 格式接口。
3.  **Step 4**: 优化 Prompt：教导大模型如何理解“相对位移”以及如何利用前一帧的失败结果来修正下一帧的动作。

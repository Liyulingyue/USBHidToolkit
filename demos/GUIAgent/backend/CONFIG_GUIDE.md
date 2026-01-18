# GUIAgent 后端配置指南

本文档介绍 `backend/.env` 文件中各配置项的详细说明及其可选值。

## 1. 视觉大模型 (VLM) 配置
Agent 依赖大模型的视觉处理能力。

*   **`OPENAI_API_KEY`**: 你的 API 密钥。
*   **`OPENAI_BASE_URL`**: API 基础地址。如果是使用本地中转或特定厂商（如百度 Ernie、阿里 Qwen），请修改此处。
*   **`OPENAI_MODEL`**: 指定模型名称。
    *   推荐值: `gpt-4o`, `claude-3-5-sonnet`, 或支持多模态的 `ernie-4.0-turbo-vision` 等。

## 2. 视频源配置 (`CAMERA_SOURCE`)
这是 Agent 的“眼睛”。程序通过此配置决定去哪里获取画面。

*   **本地设备 (索引模式)**:
    *   值: `0`, `1`, `2` 等。
    *   场景: 物理 USB 摄像头直接插在运行 Agent 的电脑上。
*   **远程流 (MJPEG 模式)**:
    *   值: `http://<IP>:5001/stream`
    *   场景: 配合 `scripts/screen_streamer.py` 使用，或者连接到网络采集卡/树莓派节点。
    *   **优点**: 图像无畸变，不受物理光线影响，适合调试。

## 3. HID 硬件连接配置
这是 Agent 的“手”。

*   **`HID_HOST`**: 你的物理控制盒（ESP32/树莓派等）在局域网中的 IP 地址。
*   **`HID_PORT`**: 控制盒监听的端口（默认通常是 `80`）。

## 4. 快速切换建议
- **调试阶段**: 将目标机作为 MJPEG 源启动 `screen_streamer.py`，配置 `CAMERA_SOURCE` 为该 URL。
- **实战阶段**: 将采集卡接入 Agent 主机，配置 `CAMERA_SOURCE` 为摄像头索引（如 `0`）。

# ShowUI-2B OpenAI Compatible Service

这是一个为 [ShowUI-2B](https://huggingface.co/showlab/ShowUI-2B) 提供 OpenAI 格式 API 调用的服务。它可以被用于 GUIAgent 作为一个本地的 VLM 后端。

## 特点

- **OpenAI 兼容**: 支持 `/v1/chat/completions` 接口。
- **专门为 GUI 优化**: 基于 ShowUI-2B (Qwen2-VL 2B 微调)，能够精确理解 UI 界面并输出操作指令。
- **本地化运行**: 模型权重将下载到当前目录下的 `models--showlab--ShowUI-2B` 文件夹中，避免占用系统盘空间。

## 安装

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 确保已安装 CUDA（推荐）以获得推理加速。

## 运行

在当前目录下运行：
```bash
python run.py --port 8005
```

## 在 GUIAgent 中配置

修改 `demos/GUIAgent/backend/.env` 文件：

```env
OPENAI_BASE_URL=http://localhost:8005/v1
OPENAI_API_KEY=any_value
OPENAI_MODEL=showlab/ShowUI-2B
```

## ShowUI 输出说明

ShowUI-2B 通常会输出类似以下格式的内容：
- 坐标点击：`{"point": [500, 500]}` (注意：坐标通常是归一化的 0-1000)
- 动作描述：点击 "OK" 按钮。

在 GUIAgent 的 Prompt 中，可以针对性地要求它以 ShowUI 熟悉的格式进行对话。

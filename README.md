# USBHidToolkit

一个用于将键盘/鼠标动作转换为 USB HID 指令并发送至硬件设备（如 ESP32、树莓派 Pico 等）的 Python 工具包。

## 简介

本工具包抽象了底层的 HID 通讯协议，允许开发者通过简单的 Python API 控制远端硬件实现模拟输入。支持多种传输协议（如 TCP），并提供了高级的按键状态管理。

## 安装

### 本地开发安装
如果你想在本地进行开发或直接运行 Demo，建议使用可编辑模式（-e）安装：
```bash
pip install -e .
```

### 通过 GitHub 远程安装
由于这是一个开源项目，你也可以直接通过 git 仓库地址进行安装：
```bash
# 使用 HTTPS
pip install git+https://github.com/Liyulingyue/USBHidToolkit.git

# 使用 SSH（推荐）
pip install git+git@github.com:Liyulingyue/USBHidToolkit.git
```

## 快速开始

```python
from usb_hid_toolkit import USBHidClient
from usb_hid_toolkit.transmitters import TCPTransmitter

# 初始化客户端（指定硬件 IP 和端口）
transmitter = TCPTransmitter(host="192.168.2.239", port=80)
client = USBHidClient(transmitter=transmitter)

# 发送简单键盘指令
client.keyboard.tap('a')

# 组合键
client.keyboard.hotkey('left_ctrl', 'c')

# 鼠标移动
client.mouse.move(x=10, y=0)
client.mouse.click('left')
```

## 详细文档与示例

更多详细用法请参考 [docs/usage_examples.md](docs/usage_examples.md)：
- [键盘高级操作（组合键、持续按住）](docs/usage_examples.md#1-键盘操作)
- [鼠标高级操作（拖拽、滚轮）](docs/usage_examples.md#2-鼠标操作)
- [多设备批量管理](docs/usage_examples.md#3-多设备管理)
- [底层拼包模式](docs/usage_examples.md#4-自定义数据包模式-packet-builder)

## 特性

- **即插即用**：支持标准的 `0x57 0xAB` HID 协议。
- **状态维持**：自动追踪键盘/鼠标按下状态。
- **多设备支持**：内置管理器轻松控制多台硬件。
- **可扩展传输层**：默认支持 TCP，可自行扩展 BLE 或 Serial。

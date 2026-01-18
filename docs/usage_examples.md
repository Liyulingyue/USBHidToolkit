# USBHidToolkit 使用详解

本手册提供了 `USBHidToolkit` 的详细使用示例，涵盖了从基础指令到复杂逻辑的实现。

## 1. 键盘操作

`client.keyboard` 提供了对键盘的精确控制。

### 基础输入
```python
# 单击按键
client.keyboard.tap('a')

# 输入字符串（需自行遍历）
for char in "hello":
    client.keyboard.tap(char)
```

### 持续按住与松开
```python
# 按住不放（例如在游戏中移动）
client.keyboard.press('w')
# ... 做其他操作 ...
client.keyboard.release('w')

# 紧急状态：松开所有按键
client.keyboard.release_all()
```

### 组合键（快捷键）
```python
# 复制
client.keyboard.hotkey('left_ctrl', 'c')

# 复杂的组合键：Ctrl + Shift + T
client.keyboard.hotkey('left_ctrl', 'left_shift', 't')
```

---

## 2. 鼠标操作

`client.mouse` 支持相对位移、按键和滚轮。

### 相对移动
```python
# 向右移动 100 像素，向下移动 50 像素
client.mouse.move(x=100, y=50)

# 滚轮操作 (正数向上，负数向下)
client.mouse.move(wheel=1)
```

### 点击与拖拽
```python
# 左键点击
client.mouse.click('left')

# 实现拖拽动作
client.mouse.press('left')
client.mouse.move(x=200, y=0) # 拖向右侧
client.mouse.release('left')
```

---

## 3. 复杂交互：Shift + 鼠标拖拽

由于键盘和鼠标是独立的 HID Report，你需要分别控制它们的状态。

```python
# 1. 先按住 Shift
client.keyboard.press('left_shift')

# 2. 调用鼠标拖拽逻辑
client.mouse.press('left')
client.mouse.move(x=100, y=100)
client.mouse.release('left')

# 3. 最后释放 Shift
client.keyboard.release('left_shift')
```

---

## 4. 多设备管理

如果你有多个硬件设备（例如多个 ESP32），可以使用 `USBHidManager`。

```python
from usb_hid_toolkit import USBHidManager, USBHidClient
from usb_hid_toolkit.transmitters import TCPTransmitter

manager = USBHidManager()

# 添加设备
manager.add_device("Device_A", USBHidClient(TCPTransmitter("192.168.1.10")))
manager.add_device("Device_B", USBHidClient(TCPTransmitter("192.168.1.11")))

# 针对特定设备操作
manager.get_device("Device_A").keyboard.tap('enter')

# 批量广播：所有设备一起按 'Esc'
manager.broadcast_keyboard_tap('esc')
```

---

## 5. 自定义数据包模式 (Packet Builder)

当你需要在一个数据包中包含极其精确的状态（例如多个键同时按下，且没有任何先后延迟），可以使用 `Packet` 类。

### 键盘多键并发
```python
from usb_hid_toolkit import KeyboardPacket

pkt = KeyboardPacket()
pkt.add_key('a').add_key('s').add_key('d') # 同时按下 ASD
client.send_packet(pkt)
```

### 鼠标复合状态
```python
from usb_hid_toolkit import MousePacket

pkt = MousePacket()
pkt.set_buttons(left=True, right=False).move(x=10, y=0)
client.send_packet(pkt)
```

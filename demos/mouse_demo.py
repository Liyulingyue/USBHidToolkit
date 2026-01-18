from usb_hid_toolkit import USBHidClient
from usb_hid_toolkit.transmitters import TCPTransmitter
import time

def run_mouse_demo():
    # 初始化客户端
    client = USBHidClient(TCPTransmitter(host="192.168.2.239", port=80))

    print("--- 鼠标基础操作演示 ---")

    # 1. 相对移动
    print("向右下移动...")
    client.mouse.move(x=100, y=100)
    time.sleep(1)

    # 2. 点击演示
    print("右键点击...")
    client.mouse.click('right')
    time.sleep(1)

    # 3. 拖拽演示
    print("开始拖拽操作...")
    client.mouse.press('left')  # 按住左键
    for _ in range(10):
        client.mouse.move(x=20, y=0)
        time.sleep(0.05)
    client.mouse.release('left') # 松开左键
    
    # 4. 滚轮演示
    print("滚轮向上滚动...")
    client.mouse.move(wheel=2)

if __name__ == "__main__":
    run_mouse_demo()

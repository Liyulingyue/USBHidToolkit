from usb_hid_toolkit import USBHidClient
from usb_hid_toolkit.transmitters import TCPTransmitter
import time

def run_complex_demo():
    # 初始化客户端
    client = USBHidClient(TCPTransmitter(host="192.168.2.239", port=80))

    print("--- 复杂交互演示：Shift + 鼠标拖拽 ---")

    # 1. 按住 Shift
    print("按住 Left Shift...")
    client.keyboard.press('left_shift')
    time.sleep(0.5)

    # 2. 执行鼠标左键拖拽
    print("按住鼠标左键并移动...")
    client.mouse.press('left')
    for i in range(20):
        client.mouse.move(x=10, y=5)
        time.sleep(0.02)
    
    # 3. 释放左键
    print("松开鼠标左键...")
    client.mouse.release('left')
    time.sleep(0.5)

    # 4. 释放 Shift
    print("松开 Shift...")
    client.keyboard.release('left_shift')

    print("操作完成。")

if __name__ == "__main__":
    run_complex_demo()

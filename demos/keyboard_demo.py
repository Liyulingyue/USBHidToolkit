from usb_hid_toolkit import USBHidClient
from usb_hid_toolkit.transmitters import TCPTransmitter
import time

def run_keyboard_demo():
    # 初始化客户端，替换为你自己的硬件 IP
    client = USBHidClient(TCPTransmitter(host="192.168.2.239", port=80))

    print("--- 键盘基础操作演示 ---")
    
    # 1. 单击按键
    print("输入 'a'...")
    client.keyboard.tap('a')
    time.sleep(1)

    # 2. 输入字符串
    print("输入 'hello'...")
    for char in "hello":
        client.keyboard.tap(char)
        time.sleep(0.1)
    
    # 3. 组合键示例
    print("触发快捷键 Ctrl+C...")
    client.keyboard.hotkey('left_ctrl', 'c')
    
    # 4. 持续按住示例
    print("按住 'w' 2秒...")
    client.keyboard.press('w')
    time.sleep(2)
    client.keyboard.release('w')
    
    print("演示结束，松开所有按键...")
    client.keyboard.release_all()

if __name__ == "__main__":
    run_keyboard_demo()

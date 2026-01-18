from usb_hid_toolkit import USBHidClient, USBHidManager
from usb_hid_toolkit.transmitters import TCPTransmitter
import time

def run_manager_demo():
    manager = USBHidManager()

    # 添加多个虚拟地址作为示例
    print("注册设备 A (192.168.2.101)...")
    manager.add_device("Device_A", USBHidClient(TCPTransmitter("192.168.2.101")))
    
    print("注册设备 B (192.168.2.102)...")
    manager.add_device("Device_B", USBHidClient(TCPTransmitter("192.168.2.102")))

    # 单独对特定设备操作
    print("向设备 A 发送 'Enter'...")
    dev_a = manager.get_device("Device_A")
    if dev_a:
        dev_a.keyboard.tap('enter')

    # 广播操作
    print("全局广播发送 'Esc'...")
    manager.broadcast_keyboard_tap('esc')

    # 释放资源
    manager.remove_device("Device_A")
    manager.remove_device("Device_B")

if __name__ == "__main__":
    run_manager_demo()

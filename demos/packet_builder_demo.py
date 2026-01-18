from usb_hid_toolkit import USBHidClient, KeyboardPacket, MousePacket
from usb_hid_toolkit.transmitters import TCPTransmitter
import time

def run_packet_builder_demo():
    client = USBHidClient(TCPTransmitter(host="192.168.2.239", port=80))

    print("--- 自定义数据包构造器演示 ---")

    # 1. 键盘多键并发 (例如 ASD 同时按下)
    print("构造并发送键盘多键数据包 (ASD)...")
    kb_pkt = KeyboardPacket()
    kb_pkt.add_key('a').add_key('s').add_key('d')
    client.send_packet(kb_pkt)
    
    time.sleep(1)
    
    # 发送空包松开所有键
    client.send_packet(KeyboardPacket())

    # 2. 鼠标复合状态 (按住键的同时移动)
    print("构造并发送鼠标复合数据包 (左键按下 + 位移)...")
    mouse_pkt = MousePacket()
    mouse_pkt.set_buttons(left=True).move(x=50, y=50)
    client.send_packet(mouse_pkt)
    
    time.sleep(1)
    
    # 释放鼠标按键
    client.send_packet(MousePacket().set_buttons(left=False))

if __name__ == "__main__":
    run_packet_builder_demo()

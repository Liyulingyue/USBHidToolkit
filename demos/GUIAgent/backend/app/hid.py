from usb_hid_toolkit import USBHidClient
from usb_hid_toolkit.transmitters import TCPTransmitter
import os

class HIDService:
    def __init__(self):
        self.client = None

    def connect(self, host: str, port: int = 80):
        """
        配置设备地址。对于 TCP 传输，我们进行一次简单的连接测试（Ping）。
        并通过发送一个“释放所有按键”的空包来验证协议是否联通。
        """
        self.host = host
        self.port = port
        
        # 尝试进行一个简单的 TCP 连接测试
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            if result == 0:
                transmitter = TCPTransmitter(host=host, port=port)
                self.client = USBHidClient(transmitter=transmitter)
                # 握手验证：发送一个全释放指令，确保协议层能正常送达
                self.client.keyboard.release_all()
                return True, f"成功连接并验证硬件: {host}"
            else:
                return False, f"无法连接到 {host}:{port} (错误码: {result})"
        except Exception as e:
            return False, f"连接异常: {str(e)}"
        finally:
            if 'sock' in locals():
                sock.close()

    def execute_mouse_relative(self, dx: int, dy: int):
        if self.client:
            print(f"[HID] 鼠标位移: dx={dx}, dy={dy}")
            self.client.mouse.move(x=dx, y=dy)
            return True
        return False

    def execute_mouse_click(self, button: str = 'left'):
        if self.client:
            print(f"[HID] 鼠标按钮点击: {button}")
            self.client.mouse.click(button)
            return True
        return False

    def execute_keyboard_tap(self, key: str):
        if self.client:
            print(f"[HID] 键盘敲击: {key}")
            self.client.keyboard.tap(key)
            return True
        return False

# 单例模式
hid_service = HIDService()

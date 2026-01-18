from usb_hid_toolkit import USBHidClient
from usb_hid_toolkit.transmitters import TCPTransmitter
import os

class HIDService:
    def __init__(self):
        self.client = None

    def connect(self, host: str, port: int = 80):
        transmitter = TCPTransmitter(host=host, port=port)
        self.client = USBHidClient(transmitter=transmitter)
        return f"Connected to {host}:{port}"

    def execute_mouse_relative(self, dx: int, dy: int):
        if self.client:
            self.client.mouse.move(x=dx, y=dy)
            return True
        return False

    def execute_mouse_click(self, button: str = 'left'):
        if self.client:
            self.client.mouse.click(button)
            return True
        return False

    def execute_keyboard_tap(self, key: str):
        if self.client:
            self.client.keyboard.tap(key)
            return True
        return False

# 单例模式
hid_service = HIDService()

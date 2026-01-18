from .keyboard import Keyboard
from .mouse import Mouse
from .transmitters import BaseTransmitter
from .packets import KeyboardPacket, MousePacket

class USBHidClient:
    def __init__(self, transmitter: BaseTransmitter):
        self.transmitter = transmitter
        self.keyboard = Keyboard(transmitter)
        self.mouse = Mouse(transmitter)

    def send_packet(self, packet_obj):
        """
        发送一个预先构造好的数据包对象 (KeyboardPacket 或 MousePacket)
        """
        raw_bytes = packet_obj.build()
        self.transmitter.send(raw_bytes)

    def close(self):
        self.transmitter.close()

class USBHidManager:
    """
    管理多个 HID 设备（客户端）。
    """
    def __init__(self):
        self._devices = {}

    def add_device(self, name: str, client: USBHidClient):
        self._devices[name] = client

    def get_device(self, name: str) -> USBHidClient:
        return self._devices.get(name)

    def remove_device(self, name: str):
        if name in self._devices:
            self._devices[name].close()
            del self._devices[name]

    def all_devices(self):
        return self._devices.values()

    def broadcast_keyboard_tap(self, key):
        """向所有设备发送同一个按键指令"""
        for device in self._devices.values():
            device.keyboard.tap(key)

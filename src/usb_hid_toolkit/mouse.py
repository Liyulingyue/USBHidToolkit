import time
from .protocol import build_mouse_packet

class Mouse:
    def __init__(self, transmitter):
        self.transmitter = transmitter
        self._button_mask = 0x00

    def move(self, x=0, y=0, wheel=0):
        """相对移动鼠标"""
        packet = build_mouse_packet(self._button_mask, x, y, wheel)
        self.transmitter.send(packet)

    def click(self, button='left', delay=0.01):
        """
        单次点击（按下并立刻松开）。
        """
        self.press(button)
        time.sleep(delay)
        self.release(button)

    def press(self, button='left'):
        """按下鼠标按键不松开"""
        mask = self._get_mask(button)
        self._button_mask |= mask
        self._send_status()

    def release(self, button='left'):
        """松开鼠标按键"""
        mask = self._get_mask(button)
        self._button_mask &= ~mask
        self._send_status()

    def _get_mask(self, button):
        if button == 'left': return 0x01
        if button == 'right': return 0x02
        if button == 'middle': return 0x04
        return 0x00

    def _send_status(self):
        packet = build_mouse_packet(self._button_mask, 0, 0, 0)
        self.transmitter.send(packet)

from .constants import KEYBOARD_CODES
from .protocol import build_keyboard_packet, build_mouse_packet

class KeyboardPacket:
    """
    用于构建单个键盘数据包。
    支持链式调用：packet.add_key('a').add_key('b')
    """
    def __init__(self):
        self.keys = []

    def add_key(self, key):
        if key in KEYBOARD_CODES:
            code = KEYBOARD_CODES[key]
            if code not in self.keys and len(self.keys) < 6:
                self.keys.append(code)
        return self

    def build(self):
        return build_keyboard_packet(self.keys)


class MousePacket:
    """
    用于构建单个鼠标数据包。
    """
    def __init__(self):
        self.button_mask = 0x00
        self.x = 0
        self.y = 0
        self.wheel = 0

    def set_buttons(self, left=False, right=False, middle=False):
        if left: self.button_mask |= 0x01
        if right: self.button_mask |= 0x02
        if middle: self.button_mask |= 0x04
        return self

    def move(self, x=0, y=0, wheel=0):
        self.x = x
        self.y = y
        self.wheel = wheel
        return self

    def build(self):
        return build_mouse_packet(self.button_mask, self.x, self.y, self.wheel)

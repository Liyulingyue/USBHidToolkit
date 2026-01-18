import time
from .constants import KEYBOARD_CODES
from .protocol import build_keyboard_packet

class Keyboard:
    def __init__(self, transmitter):
        self.transmitter = transmitter
        self._current_keys = []

    def press(self, key):
        """按下按键（不松开）。支持组合键，例如先 press('left_ctrl') 再 press('c')"""
        if key in KEYBOARD_CODES:
            code = KEYBOARD_CODES[key]
            if code not in self._current_keys:
                if len(self._current_keys) >= 6: # HID standard: max 6 keys
                    self._current_keys.pop(0)
                self._current_keys.append(code)
            self._send_status()
        else:
            print(f"Unknown key: {key}")

    def release(self, key):
        """松开特定按键"""
        if key in KEYBOARD_CODES:
            code = KEYBOARD_CODES[key]
            if code in self._current_keys:
                self._current_keys.remove(code)
            self._send_status()

    def release_all(self):
        """松开所有按键"""
        self._current_keys = []
        self._send_status()

    def tap(self, key, delay=0.01):
        """按下并松开一个按键"""
        self.press(key)
        time.sleep(delay)
        self.release(key)

    def hotkey(self, *keys, delay=0.01):
        """
        触发快捷键组合，例如 hotkey('left_ctrl', 'c')
        """
        for k in keys:
            self.press(k)
        time.sleep(delay)
        for k in reversed(keys):
            self.release(k)

    def _send_status(self):
        packet = build_keyboard_packet(self._current_keys)
        self.transmitter.send(packet)

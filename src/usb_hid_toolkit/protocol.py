def build_packet(header=None, addr=0x00, cmd=0x00, data=None):
    """
    Builds a packet according to the custom protocol.
    Format: [Header (2B)] [Addr (1B)] [Cmd (1B)] [Len (1B)] [Data (nB)] [Checksum (1B)]
    """
    if header is None:
        header = [0x57, 0xAB]
    if data is None:
        data = []
    
    data_length = len(data)
    
    # Calculate checksum: sum(header + addr + cmd + len + data) % 256
    checksum = (sum(header) + addr + cmd + data_length + sum(data)) % 256
    
    packet = (
        bytes(header) + 
        bytes([addr, cmd, data_length]) + 
        bytes(data) + 
        bytes([checksum])
    )
    return packet

def build_keyboard_packet(scancodes):
    """
    Builds a keyboard command packet (Cmd 0x02).
    Expects a list of up to 6 scancodes (plus potential modifiers if handled by protocol).
    In this implementation, it seems to expect 8 bytes of data.
    """
    # Pad to 8 bytes if needed
    padded_data = [0x00] * (8 - len(scancodes)) + scancodes
    return build_packet(cmd=0x02, data=padded_data)

def build_mouse_packet(button_mask, x_rel, y_rel, wheel):
    """
    Builds a relative mouse command packet (Cmd 0x05).
    Data Format (5 bytes):
    [0x01 (Mode)] [Buttons] [X] [Y] [Wheel]
    """
    data = [
        0x01,                   # Relative mode
        button_mask & 0xFF,
        x_rel & 0xFF,
        y_rel & 0xFF,
        wheel & 0xFF
    ]
    return build_packet(cmd=0x05, data=data)

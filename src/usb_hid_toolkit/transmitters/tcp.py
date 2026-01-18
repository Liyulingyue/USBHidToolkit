import socket
from .base import BaseTransmitter

class TCPTransmitter(BaseTransmitter):
    def __init__(self, host: str, port: int = 80, timeout: float = 1.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, packet: bytes):
        """
        Sends a packet over TCP.
        Note: The original implementation creates a new socket for each send.
        We'll follow that pattern but could optimize if needed.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.host, self.port))
            sock.sendall(packet)
        except Exception as e:
            print(f"TCP Send Error: {e}")
        finally:
            sock.close()

    def close(self):
        pass

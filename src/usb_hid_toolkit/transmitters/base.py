from abc import ABC, abstractmethod

class BaseTransmitter(ABC):
    @abstractmethod
    def send(self, packet: bytes):
        pass

    @abstractmethod
    def close(self):
        pass

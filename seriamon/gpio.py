import abc
import threading
from typing import List

class SeriaMonGpioInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def port_power(self, port, onoff=None) -> bool:
        pass

    @abc.abstractmethod
    def configure(self) -> None:
        pass

    @abc.abstractmethod
    def get_list(self, verbose=False) -> list:
        pass


class GpioManager:
    _lock = threading.Lock()
    _classes: List[SeriaMonGpioInterface] = []

    def register(name, obj) -> None:
        with GpioManager._lock:
            GpioManager._classes.append(obj)

    @staticmethod
    def get_list() -> list:
        devices = []
        for cls in GpioManager._classes:
            devices.extend(cls.get_list())
        return devices

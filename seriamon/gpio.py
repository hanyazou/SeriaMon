import abc
import threading

class SeriaMonGpioInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def port_power(self, port, onoff=None) -> bool:
        pass

    @abc.abstractmethod
    def configure() -> None:
        pass

    @abc.abstractmethod
    def get_list(verbose=False) -> list:
        pass


class GpioManager:
    _lock = threading.Lock()
    _classes = []

    def register(name, obj) -> None:
        with GpioManager._lock:
            GpioManager._classes.append(obj)

    def get_list() -> list:
        devices = []
        for cls in GpioManager._classes:
            devices.extend(cls.get_list())
        return devices

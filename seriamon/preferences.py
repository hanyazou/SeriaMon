import threading

class Preferences(object):

    _lock = threading.Lock()
    _instance = None

    __slots__ = ('scroll_buffer', 'default_log_level')

    @staticmethod
    def getInstance():
        with Preferences._lock:
            if not Preferences._instance:
                Preferences._instance = Preferences()
            return Preferences._instance

    def __init__(self) -> None:
        self.default_log_level = 2  # SeriaMonComponent.LOG_INFO
        self.scroll_buffer = 10000

from seriamon.component import SeriaMonPort
from seriamon.utils import Util

class ScriptRuntime:
    Port = SeriaMonPort

    def __init__(self):
        self._logger = None

    def set_logger(self, logger):
        self._logger = logger

    def log(self, level, message=None):
        if self._logger:
            self._logger.log(level, message)

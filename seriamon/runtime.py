import threading
from seriamon.component import SeriaMonComponent
from seriamon.utils import Util

class FilterWrapper:
    def __init__(self, filter):
        self.filter = filter
        self.pattern = None
        self.timeout = None

    def setPattern(self, pattern):
        self.pattern = pattern

    def setTimeout(self, timeout):
        (self.timeout, timeout) = (timeout, self.timeout)
        return timeout

    def getSource(self):
        return self.filter.getSource()

    def putLog(self, value, compId=None, types=None, timestamp=None):
        return self.filter.putLog(value, compId, types, timestamp)

    def hook(self, callback, pattern=None):
        return self.filter.hook(callback, pattern)

    def unhook(self, hook):
        return self.filter.unhook(hook)

    def flush(self):
        return self.filter.flush()

    def write(self, data, block=True, timeout=None):
        if not timeout:
            timeout = self.timeout
        return self.filter.write(data, block, timeout)

    def waitFor(self, pattern=None, timeout=None, silence=None):
        if not pattern:
            pattern = self.pattern
        if not timeout:
            timeout = self.timeout
        return self.filter.waitFor(pattern, timeout, silence)

    def command(self, command, pattern=None, silence=None, timeout=None):
        if not pattern:
            pattern = self.pattern
        if not timeout:
            timeout = self.timeout
        return self.filter.command(command, pattern, silence, timeout)


class ScriptRuntime:
    LOG_DEBUG = SeriaMonComponent.LOG_DEBUG
    LOG_INFO = SeriaMonComponent.LOG_INFO
    LOG_WARNING = SeriaMonComponent.LOG_WARNING
    LOG_ERROR = SeriaMonComponent.LOG_ERROR
    LOG_NONE = SeriaMonComponent.LOG_NONE

    Port = FilterWrapper
    deadline = Util.deadline

    def __init__(self):
        self._logger = None
        self._condvar = threading.Condition()

    def set_logger(self, logger):
        self._logger = logger

    def log(self, level, message=None):
        if self._logger:
            self._logger.log(level, message)

    def sleep(self, timeout):
        deadline = Util.deadline(timeout)
        with self._condvar:
            while Util.now() < deadline and Util.thread_alive():
                Util.thread_wait(self._condvar, Util.remaining_seconds(deadline))

    @staticmethod
    def now():
        return Util.now()

    @staticmethod
    def alive():
        return Util.thread_alive()
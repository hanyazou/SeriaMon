import threading
import time
import re
from datetime import datetime
from PyQt5 import QtCore
from .component import SeriaMonComponent
from .utils import Util

class FilterManagerThread(QtCore.QThread):
    def run(self):
        while True:
            with FilterManager._lock:
                for filter in FilterManager._filters:
                    filter['filter']._update()
            time.sleep(0.1)


class FilterManager:
    _lock = threading.Lock()
    _filters = []
    _thread = FilterManagerThread()

    def register(filter, name):
        with FilterManager._lock:
            if not FilterManager._thread.isRunning():
                FilterManager._thread.start()
            FilterManager._filters.append({'filter': filter, 'name': name})

    def getFilters():
        return FilterManager._filters


class FilterHook:
    def __init__(self, filter, callback):
        self.filter = filter
        self.callback = callback

    def __enter__(self):
        return self

    def __exit__(self, type, value, trace):
        self.filter.unhook(self)


class PortFilter(SeriaMonComponent):
    _condvar = threading.Condition()

    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)
        self._source = None
        self._remain = None
        self._hooks = []

    def setSource(self, source):
        self._source = source
        FilterManager.register(self, source.getComponentName())

    def getSource(self):
        return self._source

    def putLog(self, value, compId=None, types=None, timestamp=None):
        if len(value) == 0:
            return
        if timestamp is None:
            timestamp = datetime.now()
        with self._condvar:
            value = Util.decode(value).strip('\r')
            if self._remain:
                value = self._remain + value
                remain_ts = self.remain_ts
                self._remain = None
            else:
                remain_ts = None
            lines = value.split('\n')
            for i in lines[0:-1]:
                if remain_ts:
                    self._handleLine(i, compId, types, remain_ts)
                    remain_ts = None
                else:
                    self._handleLine(i, compId, types, timestamp)
            if lines[-1] == '':
                return
            self._remain = lines[-1]
            self.remain_compId = compId
            self.remain_types = types
            self.remain_ts = timestamp

    def hook(self, callback, pattern=None):
        with self._condvar:
            if pattern:
                pattern = re.compile(pattern)
            hook = FilterHook(self, callback)
            hook.pattern = pattern
            self._hooks.append(hook)
            return hook

    def unhook(self, hook):
        with self._condvar:
            self._hooks.remove(hook)

    def flush(self):
        with self._condvar:
            if self._remain == '':
                return
            self._handleLine(self._remain, self.remain_compId, self.remain_types, self.remain_ts)
            self._remain = None

    def write(self, data, block=True, timeout=None):
        return self._source.write(data, block=block, timeout=timeout)

    def waitFor(self, pattern=None, timeout=None, silence=None):
        deadline = Util.deadline(timeout)
        print("waitFor({}, pattern='{}', silence={}, deadline={})".format(self._source.getComponentName(), pattern, silence, deadline))
        lines = []
        with self._condvar, self.hook(lambda line: [ lines.append(line) ], pattern=pattern):
            while Util.now() < deadline:
                if silence:
                    if not self._condvar.wait(silence) and len(lines) == 0:
                        return True
                    else:
                        lines = []
                else:
                    if self._condvar.wait(Util.remaining_seconds(deadline)) and 0 < len(lines):
                        return True
        return False

    def command(self, command, pattern=None, silence=None, timeout=None):
        deadline = Util.deadline(timeout)
        res = []
        if pattern is None and silence is None:
            silence = 1
        if silence and not self.waitFor(silence=silence, timeout=deadline):
            raise TimeoutError()
        with self.hook(lambda line: res.append(line)):
            if not self.write(command, timeout=deadline):
                print("failed to write command {}".format(command))
                raise TimeoutError()
            if pattern and not self.waitFor(pattern=pattern, timeout=deadline):
                raise TimeoutError()
            if silence and not self.waitFor(silence=silence, timeout=deadline):
                raise TimeoutError()
        return res

    # This must be called after the lock has been acquired.
    def _handleLine(self, line, compId, types, ts):
        self.sink.putLog(line, compId, types, ts)
        for hook in self._hooks:
            if hook.pattern is None or hook.pattern.match(line):
                hook.callback(line)
        self._condvar.notifyAll()

    def _update(self):
        if self._source:
            self.setStatus(self._source.getStatus())
        if self._remain and self.remain_ts < Util.before_seconds(1):
            self.flush()

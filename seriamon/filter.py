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


class PortFilter(SeriaMonComponent):
    _lock = threading.RLock()

    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)
        self._source = None
        self._remain = None
        self._hooks = {}

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
        with self._lock:
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
        with self._lock:
            if pattern:
                pattern = re.comple(pattern)
            self._hooks[callback] = pattern

    def unhook(self, callback):
        with self._lock:
            del self._hooks[callback]

    def flush(self):
        with self._lock:
            if self._remain == '':
                return
            self._handleLine(self._remain, self.remain_compId, self.remain_types, self.remain_ts)
            self._remain = None

    def write(self, data, block=True, timeout=None):
        return self._source.write(data, block=block, timeout=timeout)

    def _handleLine(self, line, compId, types, ts):
        with self._lock:
            for cb in self._hooks:
                if self._hooks[cb] is None:
                    cb(line)
                else:
                    match =  self._hooks[cb].match(line)
                    if match:
                        cb(line)
        self.sink.putLog(line, compId, types, ts)

    def _update(self):
        if self._source:
            self.setStatus(self._source.getStatus())
        if self._remain and self.remain_ts < Util.before_seconds(2):
            self.flush()

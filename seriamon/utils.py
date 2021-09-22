import datetime
import threading

from PyQt5.QtWidgets import *
from PyQt5 import QtCore

from seriamon.preferences import Preferences

class ComboBox(QComboBox):
    aboutToBeShown = QtCore.pyqtSignal()
    def showPopup(self):
        self.aboutToBeShown.emit()
        super(ComboBox, self).showPopup()

    def showEvent(self, e):
        self.aboutToBeShown.emit()
        super(ComboBox, self).showEvent(e)

class Util:

    _logger = None
    _thread_storage_name = '__seriamon_thread_storage__'

    def _hexstr(buf):
        return ''.join(["\\%02x" % ord(chr(x)) for x in buf]).strip()

    def decode(data):
        if isinstance(data, str):
            return data
        try:
            return data.decode()
        except UnicodeDecodeError as e:
            return data[:e.start].decode() + Util._hexstr(data[e.start:e.end]) + Util.decode(data[e.end:])
    
    def after_seconds(seconds):
        return Util.now() + datetime.timedelta(seconds=seconds)
    
    def before_seconds(seconds):
        return Util.now() + datetime.timedelta(seconds=-seconds)
    
    def remaining_seconds(deadline):
        return min(threading.TIMEOUT_MAX, (deadline - Util.now()).total_seconds())
    
    def now():
        return datetime.datetime.now()

    def deadline(timeout=None, seconds=None):
        if seconds:
            return Util.after_seconds(seconds)
        if timeout:
            if isinstance(timeout, datetime.timedelta):
                return Util.now() + timeout
            elif isinstance(timeout, datetime.datetime):
                return timeout
            elif isinstance(timeout, (float, int)):
                return Util.after_seconds(timeout)
        if timeout:
            raise Exception("Could not interplet value of type {} to deadline.".format(type(timeout)))
        return datetime.datetime.max

    def set_logger(logger):
        Util._logger = logger

    def log(level, message=None):
        if Util._logger:
            Util._logger.log(level, message)

    class _ThreadStorage:
        def __init__(self):
            self.killed = False
            self.exception = None
            self.waitchannel = None

    class ThreadKilledException(Exception):
        def __init__(self):
            pass

        def __str__(self):
            return 'Killed'

    def _thread_storage(thread: threading.Thread = None) -> _ThreadStorage:
        if not thread:
            thread = threading.current_thread()
        storage = getattr(thread, Util._thread_storage_name, None)
        return storage

    def thread_context(name: str = None) -> threading.Thread:
        ctx = threading.current_thread()
        if name:
            ctx.name = name
        setattr(ctx, Util._thread_storage_name, Util._ThreadStorage())
        return ctx

    def thread_alive() -> None:
        if not (storage := Util._thread_storage()):
            return True
        if storage.killed:
            raise storage.exception
        return True

    def thread_wait(condvar: threading.Condition, timeout: float = None):
        if not (storage := Util._thread_storage()):
            return
        storage.waitchannel = condvar
        condvar.wait(timeout)
        storage.waitchannel = None

    def thread_kill(ctx: threading.Thread, e: Exception = None):
        if not (storage := getattr(ctx, Util._thread_storage_name, None)):
            return
        storage.exception = e if e else Util.ThreadKilledException()
        storage.killed = True
        if storage.waitchannel:
            with storage.waitchannel:
                storage.waitchannel.notifyAll()
        storage.waitchannel = None

import datetime
import threading

from PyQt5.QtWidgets import *
from PyQt5 import QtCore

class ComboBox(QComboBox):
    aboutToBeShown = QtCore.pyqtSignal()
    def showPopup(self):
        self.aboutToBeShown.emit()
        super(ComboBox, self).showPopup()

    def showEvent(self, e):
        self.aboutToBeShown.emit()
        super(ComboBox, self).showEvent(e)

class Util:
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
            raise Exception(print("Could not interplet value of type {} to deadline.".format(type(timeout))))
        return datetime.datetime.max

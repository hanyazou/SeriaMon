import datetime

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
    
    def now():
        return datetime.datetime.now()

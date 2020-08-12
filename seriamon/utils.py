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

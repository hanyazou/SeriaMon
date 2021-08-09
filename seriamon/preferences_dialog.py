import threading
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtCore import QVariant

from seriamon.preferences import Preferences
from seriamon.component import SeriaMonComponent

class PreferencesDialog(QDialog, SeriaMonComponent, object):
    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)

        self.setWindowTitle('Preferences')
        self.prefs = Preferences.getInstance()

        self.scrollBufferTextEdit = QLineEdit()
        width = self.scrollBufferTextEdit.fontMetrics().boundingRect('______').width()
        self.scrollBufferTextEdit.setMinimumWidth(width)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._onOK)
        self.buttons.rejected.connect(self._onCancel)

        self.logLevelComboBox = QComboBox()
        self.logLevelComboBox.addItem('none', QVariant(SeriaMonComponent.LOG_NONE))
        self.logLevelComboBox.addItem('error', QVariant(SeriaMonComponent.LOG_ERROR))
        self.logLevelComboBox.addItem('warning', QVariant(SeriaMonComponent.LOG_WARNING))
        self.logLevelComboBox.addItem('info', QVariant(SeriaMonComponent.LOG_INFO))
        self.logLevelComboBox.addItem('debug', QVariant(SeriaMonComponent.LOG_DEBUG))
        
        grid = QGridLayout()
        grid.addWidget(QLabel('log level:'), 0, 0, 1, 1)
        grid.addWidget(self.logLevelComboBox, 0, 1, 1, 1)
        grid.addWidget(QLabel('scroll buffer:'), 1, 0, 1, 1)
        grid.addWidget(self.scrollBufferTextEdit, 1, 1, 1, 6)
        grid.addWidget(self.buttons, 2, 0, 1, 7, alignment=QtCore.Qt.AlignRight)
        grid.setColumnStretch(0, 1)
        self.setLayout(grid)

        self.initPreferences('seriamon.prefeerences.',
                             [[ int,    'scroll_buffer',     self.prefs.scroll_buffer,     self.scrollBufferTextEdit ],
                              [ int,    'default_log_level', self.prefs.default_log_level, self.logLevelComboBox     ]
                             ])

    def __setattr__(self, name, value) -> None:
        prefs = Preferences.getInstance()
        if hasattr(prefs, name):
            self.log(SeriaMonComponent.LOG_DEBUG, 'prefs.{} <- {}'.format(name, value))
            prefs.__setattr__(name, value)
        super().__setattr__(name, value)

    def __getattr__(self, name):
        prefs = Preferences.getInstance()
        if hasattr(prefs, name):
            self.log(SeriaMonComponent.LOG_DEBUG, 'prefs.{} -> {}'.format(name, getattr(prefs, name)))
            getattr(prefs, name)
        return super().__getattr__(name)

    def setupDialog(self):
        return self

    def _onOK(self):
        self.reflectFromUi()
        self.close()

    def _onCancel(self):
        self.reflectToUi()
        self.close()

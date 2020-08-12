import sys
import os
import serial
import serial.tools.list_ports
import errno
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QTextCursor
from .component import SeriaMonComponent

class UartReader(QWidget, SeriaMonComponent):

    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)

        self.thread = _ReaderThread(self)
        self.port = serial.Serial()

        self.portnameComboBox = QComboBox()
        iterator = sorted(serial.tools.list_ports.comports(include_links=True))
        for (port, desc, hwid) in iterator:
            self.portnameComboBox.addItem(port, port)
        
        self.plotCheckBox = QCheckBox('plot')

        self.baudrateComboBox = QComboBox()
        self.baudrateComboBox.addItem('9600', 9600)
        self.baudrateComboBox.addItem('115200', 115200)

        self.bytesizeComboBox = QComboBox()
        self.bytesizeComboBox.addItem('7', QVariant(serial.SEVENBITS))
        self.bytesizeComboBox.addItem('8', QVariant(serial.EIGHTBITS))

        self.parityComboBox = QComboBox()
        self.parityComboBox.addItem('none', QVariant(serial.PARITY_NONE))
        self.parityComboBox.addItem('odd', QVariant(serial.PARITY_ODD))
        self.parityComboBox.addItem('even', QVariant(serial.PARITY_EVEN))

        self.stopbitsComboBox = QComboBox()
        self.stopbitsComboBox.addItem('1', QVariant(serial.STOPBITS_ONE))
        self.stopbitsComboBox.addItem('1.5', QVariant(serial.STOPBITS_ONE_POINT_FIVE))
        self.stopbitsComboBox.addItem('2', QVariant(serial.STOPBITS_TWO))

        self.initPreferences('seriamon.uartreader.{}.'.format(instanceId),
                             [[ str,    'portname', None,   self.portnameComboBox ],
                              [ bool,   'plot',     False,  self.plotCheckBox ],
                              [ int,    'baudrate', 9600,   self.baudrateComboBox ],
                              [ int,    'bytesize', 8,      self.bytesizeComboBox ],
                              [ str,    'parity',   'N',    self.parityComboBox ],
                              [ float,  'stopbits', 1,      self.stopbitsComboBox ]])

        self.applyButton = QPushButton('Apply')
        self.applyButton.clicked.connect(self.reflectFromUi)

        self.connectButton = QPushButton()
        self.connectButton.clicked.connect(self._buttonClicked)
        self.connected = True
        self._buttonClicked()

        layout = QHBoxLayout()
        layout.addWidget(QLabel('baud rate:'))
        layout.addWidget(self.baudrateComboBox)
        layout.addWidget(QLabel('    byte size:'))
        layout.addWidget(self.bytesizeComboBox)
        layout.addWidget(QLabel('    parity bit:'))
        layout.addWidget(self.parityComboBox)
        layout.addWidget(QLabel('    stop bit:'))
        layout.addWidget(self.stopbitsComboBox)

        grid = QGridLayout()
        grid.addWidget(self.portnameComboBox, 0, 1, 1, 2)
        grid.addWidget(self.plotCheckBox, 0, 3)
        grid.addLayout(layout, 1, 1, 1, 4)
        grid.addWidget(self.applyButton, 2, 3)
        grid.addWidget(self.connectButton, 2, 4)
        self.setLayout(grid)

        self.thread.start()

    def _buttonClicked(self):
        sender = self.sender()

        if self.port.is_open:
            self.thread.ignoreErrors = True
            self.port.close()
            self.sink.putLog('---- close port {} -----'.format(self.port.port), self.compId)

        self.port.port = self.portnameComboBox.currentText()
        self.port.baudrate = self.baudrateComboBox.currentData()
        self.port.bytesize = self.bytesizeComboBox.currentData()
        self.port.parity = self.parityComboBox.currentData()
        self.port.stopbits = self.stopbitsComboBox.currentData()

        self.connected = not self.connected
        self.portnameComboBox.setEnabled(not self.connected)
        self.plotCheckBox.setEnabled(not self.connected)
        self.baudrateComboBox.setEnabled(not self.connected)
        self.bytesizeComboBox.setEnabled(not self.connected)
        self.parityComboBox.setEnabled(not self.connected)
        self.stopbitsComboBox.setEnabled(not self.connected)
        self.connectButton.setText('Disconnect' if self.connected else 'Connect')
        self.reflectFromUi()

        if self.connected:
            self.sink.putLog('---- open port {} -----'.format(self.port.port), self.compId)
            self.thread.ignoreErrors = False
            self.port.open()

class _ReaderThread(QtCore.QThread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.stayAlive = True
        self.ignoreErrors = False

    def run(self):
        while self.stayAlive:
            if self.parent.port.is_open:
                try:
                    compId = self.parent.compId
                    value = self.parent.port.readline().decode().rstrip('\n\r')
                    if self.parent.plotCheckBox.isChecked():
                        types = 'p'
                    else:
                        types = None
                    self.parent.sink.putLog(value, compId, types)
                except Exception as e:
                    if not self.ignoreErrors:
                        print(e)
                    self.msleep(100)
            else:
                self.msleep(100)

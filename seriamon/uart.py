import sys
import os
import serial
import serial.tools.list_ports
import errno
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QTextCursor

class UartReader(QWidget):

    def __init__(self, compId, sink, instanceId=0):
        super().__init__()

        self.initPreferences('seriamon.uartreader.{}.'.format(instanceId),
                             [[ str, 'portname', None ],
                              [ bool, 'plot', False ],
                              [ int, 'baudrate', 9600 ],
                              [ int, 'bytesize', 1 ],
                              [ str, 'parity', 1 ],
                              [ float, 'stopbits', 1 ],
                              [ bool, 'connected', False ]])

        self.compId = compId
        self.sink = sink
        self.thread = _ReaderThread(self)
        self.port = serial.Serial()

        self.portnameComboBox = QComboBox()
        iterator = sorted(serial.tools.list_ports.comports(include_links=True))
        for (port, desc, hwid) in iterator:
            self.portnameComboBox.addItem(port)
        
        self.plotCheckBox = QCheckBox('plot')
        self.plotCheckBox.setChecked(False)

        self.baudrateComboBox = QComboBox()
        self.baudrateComboBox.addItem('9600', 9600)
        self.baudrateComboBox.addItem('115200', 115200)

        self.bytesizeComboBox = QComboBox()
        self.bytesizeComboBox.addItem('7', QVariant(serial.SEVENBITS))
        self.bytesizeComboBox.addItem('8', QVariant(serial.EIGHTBITS))
        self.bytesizeComboBox.setCurrentText('8')

        self.parityComboBox = QComboBox()
        self.parityComboBox.addItem('none', QVariant(serial.PARITY_NONE))
        self.parityComboBox.addItem('odd', QVariant(serial.PARITY_ODD))
        self.parityComboBox.addItem('even', QVariant(serial.PARITY_EVEN))
        self.parityComboBox.setCurrentText('none')

        self.stopbitsComboBox = QComboBox()
        self.stopbitsComboBox.addItem('1', QVariant(serial.STOPBITS_ONE))
        self.stopbitsComboBox.addItem('1.5', QVariant(serial.STOPBITS_ONE_POINT_FIVE))
        self.stopbitsComboBox.addItem('2', QVariant(serial.STOPBITS_TWO))
        self.stopbitsComboBox.setCurrentText('1')

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

    def savePreferences(self, prefs):
        for prop in self.preferencePoperties:
            typ = prop[0]
            name = prop[1]
            value = getattr(self, name)
            if typ == bool:
                value = int(value)
            prefs[self.preferenceKeyPrefix + name] = str(value)

    def loadPreferences(self, prefs):
        for prop in self.preferencePoperties:
            typ = prop[0]
            name = prop[1]
            key = self.preferenceKeyPrefix + name
            if not key in prefs:
                continue
            value = str(prefs[key])
            if not value:
                continue
            if typ == bool:
                value = int(value)
            setattr(self, name, typ(value))
        self.reflectToUi()

    def initPreferences(self, prefix, prefprops):
        self.preferenceKeyPrefix = prefix
        self.preferencePoperties = prefprops
        for prop in prefprops:
            typ = prop[0]
            name = prop[1]
            value = prop[2]
            setattr(self, name, typ(value))

    def reflectToUi(self):
        self.portnameComboBox.setCurrentText(self.portname)
        self.plotCheckBox.setChecked(self.plot)
        index = self.baudrateComboBox.findData(self.baudrate)
        if 0 <= index:
            self.baudrateComboBox.setCurrentIndex(index)
        else:
            print('WARNING: failed to set baudrate to {}'.format(self.baudrate))
        index = self.bytesizeComboBox.findData(self.bytesize)
        if 0 <= index:
            self.bytesizeComboBox.setCurrentIndex(index)
        else:
            print('WARNING: failed to set bytesize to {}'.format(self.bytesize))
        index = self.parityComboBox.findData(self.parity)
        if 0 <= index:
            self.parityComboBox.setCurrentIndex(index)
        else:
            print('WARNING: failed to set parity to {}'.format(self.parity))
        index = self.stopbitsComboBox.findData(self.stopbits)
        if 0 <= index:
            self.stopbitsComboBox.setCurrentIndex(index)
        else:
            print('WARNING: failed to set stopbits to {}'.format(self.stopbits))
        #
        # XXX, 'connected' should be handled here also
        #
        # self.connectButton.setText('Disconnect' if self.connected else 'Connect')

    def reflectFromUi(self):
        self.portname = self.portnameComboBox.currentText()
        self.plot = self.plotCheckBox.isChecked()
        self.baudrate = self.baudrateComboBox.currentData()
        self.bytesize = self.bytesizeComboBox.currentData()
        self.parity = self.parityComboBox.currentData()
        self.stopbits = self.stopbitsComboBox.currentData()

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

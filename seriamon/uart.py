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

        self._initPreferences('seriamon.uartreader.{}.'.format(instanceId),
                              [[ 's', 'portname', None ],
                               [ 'b', 'plot', False ],
                               [ 'i', 'baudrate', 9600 ],
                               [ 'i', 'bytesize', 1 ],
                               [ 's', 'parity', 1 ],
                               [ 'f', 'stopbits', 1 ],
                               [ 'b', 'connected', False ]])

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
        grid.addWidget(self.connectButton, 2, 4)
        self.setLayout(grid)

        self.thread.start()

    def savePreferences(self, prefs):
        self._putPreference(prefs, 'portname', self.portname)
        self._putPreference(prefs, 'plot', int(self.plot))
        self._putPreference(prefs, 'baudrate', self.baudrate)
        self._putPreference(prefs, 'bytesize', self.bytesize)
        self._putPreference(prefs, 'parity', self.parity)
        self._putPreference(prefs, 'stopbits', self.stopbits)
        self._putPreference(prefs, 'connected', int(self.connected))

    def loadPreferences(self, prefs):
        portname = self._getPreference(prefs, 'portname')
        if portname:
            self.portname = portname
        plot = self._getPreference(prefs, 'plot')
        if plot:
            self.plot = bool(int(plot))
        baudrate = self._getPreference(prefs, 'baudrate')
        if baudrate:
            self.baudrate = int(baudrate)
        bytesize = self._getPreference(prefs, 'bytesize')
        if bytesize:
            self.bytesize = int(bytesize)
        parity = self._getPreference(prefs, 'parity')
        if parity:
            self.parity = str(parity)
        stopbits = self._getPreference(prefs, 'stopbits')
        if stopbits:
            self.stopbits =float(stopbits)
        connected = self._getPreference(prefs, 'connected')
        if connected:
            self.connected =bool(int(connected))
        self._reflectToUi()

    def _putPreference(self, prefs, key, value):
        prefs[self.precerenceKeyPrefix + key] = str(value)

    def _getPreference(self, prefs, key) -> str:
        key = self.precerenceKeyPrefix + key
        if key in prefs:
            return str(prefs[key])
        else:
            return None

    def _initPreferences(self, prefix, prefprops):
        self.precerenceKeyPrefix = prefix
        self.preferencePoperties = prefprops
        self.portname = None
        self.plot = False
        self.baudrate = 115200
        self.bytesize = 1
        self.parity = 0
        self.stopbits = 0
        self.connected = False

    def _reflectToUi(self):
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

    def _reflectFromUi(self):
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
        self._reflectFromUi()

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

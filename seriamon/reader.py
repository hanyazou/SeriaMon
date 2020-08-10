import sys
import os
import serial
import serial.tools.list_ports
import errno
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QTextCursor

class serialReaderThread(QtCore.QThread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.stayAlive = True
        self.ignoreErrors = False

    def run(self):
        while self.stayAlive:
            if self.parent.port.is_open:
                try:
                    text = '{} {}'.format(self.parent.id,
                                          self.parent.port.readline().decode().rstrip('\n\r'))
                    if self.parent.plotCheckBox.isChecked():
                        self.parent.dataQueue.put(text)
                    else:
                        self.parent.msgQueue.put(text)
                    self.parent.signal.emit('s')
                except Exception as e:
                    if not self.ignoreErrors:
                        print(e)
                    self.msleep(100)
            else:
                self.msleep(100)

class serialReader(QWidget):

    def __init__(self, id, signal, dataQueue, msgQueue):
        super().__init__()

        self.id = id
        self.signal = signal
        self.dataQueue = dataQueue
        self.msgQueue = msgQueue
        self.serialReaderThread = serialReaderThread(self)
        self.port = serial.Serial()

        self.portComboBox = QComboBox()
        iterator = sorted(serial.tools.list_ports.comports(include_links=True))
        for (port, desc, hwid) in iterator:
            self.portComboBox.addItem(port)
        
        self.plotCheckBox = QCheckBox('plot')
        self.plotCheckBox.setChecked(False)

        self.baudrateComboBox = QComboBox()
        self.baudrateComboBox.addItem('9600')
        self.baudrateComboBox.addItem('115200')

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
        self.connectButton.clicked.connect(self.buttonClicked)
        self.connected = True
        self.buttonClicked()

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
        grid.addWidget(self.portComboBox, 0, 1, 1, 2)
        grid.addWidget(self.plotCheckBox, 0, 3)
        grid.addLayout(layout, 1, 1, 1, 4)
        grid.addWidget(self.connectButton, 2, 4)
        self.setLayout(grid)

        self.serialReaderThread.start()

    def buttonClicked(self):
        sender = self.sender()

        if self.port.is_open:
            self.serialReaderThread.ignoreErrors = True
            self.port.close()
            self.msgQueue.put('{} close port'.format(self.id))

        self.port.port = self.portComboBox.currentText()
        self.port.baudrate = int(self.baudrateComboBox.currentText())
        self.port.bytesize = self.bytesizeComboBox.currentData()
        self.port.parity = self.parityComboBox.currentData()
        self.port.stopbits = self.stopbitsComboBox.currentData()

        self.connected = not self.connected
        self.portComboBox.setEnabled(not self.connected)
        self.plotCheckBox.setEnabled(not self.connected)
        self.baudrateComboBox.setEnabled(not self.connected)
        self.bytesizeComboBox.setEnabled(not self.connected)
        self.parityComboBox.setEnabled(not self.connected)
        self.stopbitsComboBox.setEnabled(not self.connected)
        self.connectButton.setText('Disconnect' if self.connected else 'Connect')

        if self.connected:
            self.msgQueue.put('{} open port'.format(self.id))
            print(self.port)
            self.serialReaderThread.ignoreErrors = False
            self.port.open()

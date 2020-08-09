import sys
import os
from datetime import datetime
import serial
import serial.tools.list_ports
import errno
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QTextCursor


class serialReaderThread(QtCore.QThread):
    def __init__(self, port, signal):
        super().__init__()
        self.port = port
        self.signal = signal
        self.stayAlive = True
        self.ignoreErrors = False

    def run(self):
        print("start thread...")
        while self.stayAlive:
            if self.port.is_open:
                try:
                    s = self.port.read().decode().rstrip('\r')
                    self.signal.emit(s)
                except Exception as e:
                    if not self.ignoreErrors:
                        print(e)
                    self.msleep(100)
            else:
                self.msleep(100)
        print("end thread")

class mainWindow(QWidget):

    serialPortSignal = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.port = serial.Serial()
        self.serialPortSignal.connect(self.textHandler)
        self.newline = True

        self.portComboBox = QComboBox()
        iterator = sorted(serial.tools.list_ports.comports(include_links=True))
        for (port, desc, hwid) in iterator:
            self.portComboBox.addItem(port)
        
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

        self.autoScrollCheckBox = QCheckBox('auto scroll')
        self.autoScrollCheckBox.setChecked(True)

        self.timestampCheckBox = QCheckBox('timestamp')
        self.timestampCheckBox.setChecked(True)

        self.textEdit = QPlainTextEdit()
        self.textEdit.setReadOnly(True)
        doc = self.textEdit.document()
        font = doc.defaultFont()
        font.setFamily("Courier New")
        doc.setDefaultFont(font)

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
        grid.addWidget(self.textEdit, 1, 0, 1, 5)
        grid.addWidget(self.portComboBox, 2, 1, 1, 2)
        grid.addLayout(layout, 3, 1, 1, 4)
        grid.addWidget(self.autoScrollCheckBox, 4, 1)
        grid.addWidget(self.timestampCheckBox, 4, 2)
        grid.addWidget(self.connectButton, 4, 4)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        self.setLayout(grid)
        self.show()

        self.serialReaderThread = serialReaderThread(self.port, self.serialPortSignal)
        self.serialReaderThread.start()

    def buttonClicked(self):
        sender = self.sender()

        if self.port.is_open:
            print("close port...")
            self.serialReaderThread.ignoreErrors = True
            self.port.close()
            print("close port...done")
            if not self.newline:
                textHandler('\n')
                self.newline = True

        self.port.port = self.portComboBox.currentText()
        self.port.baudrate = int(self.baudrateComboBox.currentText())
        self.port.bytesize = self.bytesizeComboBox.currentData()
        self.port.parity = self.parityComboBox.currentData()
        self.port.stopbits = self.stopbitsComboBox.currentData()

        self.connected = not self.connected
        self.portComboBox.setEnabled(not self.connected)
        self.baudrateComboBox.setEnabled(not self.connected)
        self.bytesizeComboBox.setEnabled(not self.connected)
        self.parityComboBox.setEnabled(not self.connected)
        self.stopbitsComboBox.setEnabled(not self.connected)
        self.connectButton.setText('Disconnect' if self.connected else 'Connect')

        if self.connected:
            print("open port...")
            print(self.port)
            self.serialReaderThread.ignoreErrors = False
            self.port.open()
            print("open port...done")

    def textHandler(self, text):
        cursor = QTextCursor(self.textEdit.document())
        cursor.movePosition(QTextCursor.End)
        if self.newline and self.timestampCheckBox.isChecked():
            timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
            cursor.insertText("{} ".format(timestamp))
            self.newline = False
        cursor.insertText(text)
        if text == '\n':
            self.newline = True
            scrollbar = self.textEdit.verticalScrollBar()
            if self.autoScrollCheckBox.isChecked():
                scrollbar.setValue(scrollbar.maximum() - 1) 

import sys
import os
import queue
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtGui import QTextCursor

from seriamon import plotter
from seriamon import reader

class mainWindow(QWidget):

    serialPortSignal = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.NUMPORTS = 4;
        self.MAXQUEUESIZE = 10;
        self.dataQueue = queue.Queue(self.MAXQUEUESIZE)
        self.msgQueue = queue.Queue(self.MAXQUEUESIZE)
        self.serialPortSignal.connect(self.handler)
        self.readers = []
        for i in range(0, self.NUMPORTS):
            self.readers.append(reader.serialReader(i, self.serialPortSignal,
                                                    self.dataQueue, self.msgQueue))

        self.plotter = plotter.Plotter()

        self.textEdit = QPlainTextEdit()
        self.textEdit.setReadOnly(True)
        doc = self.textEdit.document()
        font = doc.defaultFont()
        font.setFamily("Courier New")
        doc.setDefaultFont(font)

        self.autoScrollCheckBox = QCheckBox('auto scroll')
        self.autoScrollCheckBox.setChecked(True)

        self.timestampCheckBox = QCheckBox('timestamp')
        self.timestampCheckBox.setChecked(True)

        self.tabs = QTabWidget()
        for i in range(0, self.NUMPORTS):
            self.tabs.addTab(self.readers[i], 'Port {}'.format(i))

        grid = QGridLayout()
        grid.addWidget(self.plotter, 0, 0, 1, 7)
        grid.addWidget(self.textEdit, 1, 0, 1, 7)
        grid.addWidget(self.autoScrollCheckBox, 2, 5)
        grid.addWidget(self.timestampCheckBox, 2, 6)
        # grid.addWidget(QLabel('T'), 3, 0)
        grid.addWidget(self.tabs, 3, 0, 1, 7, alignment=QtCore.Qt.AlignRight)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        self.setLayout(grid)
        self.show()

    def handler(self, msg):
        timestamp = datetime.now()
        while not self.msgQueue.empty():
            text = self.msgQueue.get()
            self.textHandler(timestamp, text)
        while not self.dataQueue.empty():
            text = self.dataQueue.get()
            self.textHandler(timestamp, text)
            self.dataHandler(timestamp, text[2:])

    def textHandler(self, timestamp, text):
        cursor = QTextCursor(self.textEdit.document())
        cursor.movePosition(QTextCursor.End)
        if self.timestampCheckBox.isChecked():
            cursor.insertText("{} ".format(timestamp.isoformat(sep=' ', timespec='milliseconds')))
        cursor.insertText(text)
        cursor.insertText('\n')
        if self.autoScrollCheckBox.isChecked():
            scrollbar = self.textEdit.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum() - 1)

    def dataHandler(self, timestamp, text):
        try:
            values = [float(v.split(':')[-1]) for v in text.split()]
        except Exception as e:
            values = None
        if values:
            self.plotter.insert(timestamp.timestamp(), values)
            self.plotter.update()

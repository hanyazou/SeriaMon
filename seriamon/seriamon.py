import sys
import os
import queue
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5 import QtCore

from .plotter import Plotter
from .uart import UartReader
from .text import TextViewer
from .logger import Logger

class mainWindow(QMainWindow):

    serialPortSignal = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()

        """
           initialize properties
        """
        self.NUMPORTS = 4;
        self.MAXQUEUESIZE = 10;
        self.queue = queue.Queue(self.MAXQUEUESIZE)
        self.serialPortSignal.connect(self.handler)

        """
           create components
        """
        id = 0
        self.uartReaders = []
        for i in range(0, self.NUMPORTS):
            self.uartReaders.append(UartReader(compId=str(id), sink=self))
            id += 1
        self.plotter = Plotter(compId=str(id), sink=self)
        id += 1
        self.textViewer = TextViewer(compId=str(id), sink=self)
        id += 1
        self.logger = Logger(compId=str(id), sink=self)
        id += 1

        """
           widgets
        """
        self.tabs = QTabWidget()
        for i in range(0, self.NUMPORTS):
            self.tabs.addTab(self.uartReaders[i], 'Port {}'.format(i))

        grid = QGridLayout()
        grid.addWidget(self.plotter, 0, 0, 1, 7)
        grid.addWidget(self.textViewer, 1, 0, 1, 7)
        grid.addWidget(self.tabs, 2, 0, 1, 7, alignment=QtCore.Qt.AlignRight)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        widget = QWidget()
        widget.setLayout(grid)
        self.setCentralWidget(widget)

        """
           menu
        """
        logmenu = QAction('&Log...', self)
        logmenu.triggered.connect(self.logger.setup)

        menubar = self.menuBar()
        filemenu = menubar.addMenu('&File')
        filemenu.addAction(logmenu)

        self.show()

    def putLog(self, value, compId=None, types=None, timestamp=None):
        if not compId:
            compId = '?'
        if not types:
            types = ''
        if not timestamp:
            timestamp = datetime.now()
        self.queue.put([value, compId, types, timestamp ])
        self.serialPortSignal.emit('s')

    def handler(self, msg):
        while not self.queue.empty():
            item = self.queue.get()
            value = item[0]
            compId = item[1]
            types = item[2]
            timestamp = item[3]
            self.textViewer.putLog(value, compId, types, timestamp)
            if 'p' in types:
                self.plotter.putLog(value, compId, types, timestamp)
            self.logger.putLog(value, compId, types, timestamp)


class SeriaMon:
    def __init__(self):
        pass

    def run(self):
        app = QApplication([])
        window = mainWindow()
        window.setWindowTitle('Serial Monitor')
        sys.exit(app.exec_())


if __name__ == '__main__':
    SeriaMon().run()

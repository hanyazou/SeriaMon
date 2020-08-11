import sys
import os
import queue
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5 import QtCore

from seriamon import plotter
from seriamon import reader
from seriamon import viewer
from seriamon import logger

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
           widgets
        """
        self.readers = []
        for i in range(0, self.NUMPORTS):
            self.readers.append(reader.serialReader(sourceId=str(i), logger=self))

        self.plotter = plotter.Plotter()
        self.viewer = viewer.Viewer()
        self.logger = logger.Logger()

        self.tabs = QTabWidget()
        for i in range(0, self.NUMPORTS):
            self.tabs.addTab(self.readers[i], 'Port {}'.format(i))

        grid = QGridLayout()
        grid.addWidget(self.plotter, 0, 0, 1, 7)
        grid.addWidget(self.viewer, 1, 0, 1, 7)
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

    def putLog(self, value, sourceId=None, op=None, timestamp=None):
        if not sourceId:
            sourceId = '?'
        if not op:
            op = ''
        if not timestamp:
            timestamp = datetime.now()
        self.queue.put([value, sourceId, op, timestamp ])
        self.serialPortSignal.emit('s')

    def handler(self, msg):
        while not self.queue.empty():
            item = self.queue.get()
            value = item[0]
            sourceId = item[1]
            op = item[2]
            timestamp = item[3]
            self.viewer.putLog(value, sourceId, op, timestamp)
            if 'p' in op:
                self.plotter.putLog(value, sourceId, op, timestamp)
            self.logger.putLog(value, sourceId, op, timestamp)

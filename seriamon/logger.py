import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5 import QtCore

class Logger(QDialog):
    def __init__(self, compId, sink, instanceId=0):
        super().__init__()

        self.writer = None
        self.filename = os.path.join(os.path.expanduser('~'), 'Documents', 'seriamon.log')
        self.doWrite = False

        self.setWindowTitle('Log settings')

        self.saveCheckBox = QCheckBox('Save log as')
        self.saveCheckBox.stateChanged.connect(self._onSaveStateChanged)
        self.saveCheckBox.setChecked(False)

        self.fileTextEdit = QLineEdit()
        width = self.fileTextEdit.fontMetrics().boundingRect(self.filename+'____').width()
        self.fileTextEdit.setMinimumWidth(width)

        self.selectFileButton = QPushButton('...')
        self.selectFileButton.clicked.connect(self._selectFile)

        self.setObjectName('Logger')
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._onOK)
        self.buttons.rejected.connect(self.close)

        grid = QGridLayout()
        grid.addWidget(self.saveCheckBox, 0, 0)
        grid.addWidget(self.fileTextEdit, 1, 0, 1, 6)
        grid.addWidget(self.selectFileButton, 1, 6)
        grid.addWidget(self.buttons, 2, 0, 1, 7, alignment=QtCore.Qt.AlignRight)
        grid.setColumnStretch(0, 1)
        self.setLayout(grid)

    def putLog(self, value, compId=None, types=None, timestamp=None):
        if not types:
            types = '-'
        if self.writer:
            self.writer.write('{} {} {} {}\n'.format(timestamp, compId, types, value))
            self.writer.flush()

    def setup(self):
        self.fileOpenError = None
        self.fileTextEdit.setText(self.filename)
        self.exec()
        if self.fileOpenError:
            QMessageBox.critical(self, "Error", '{}'.format(self.fileOpenError))

    def _onSaveStateChanged(self):
        doWrite = self.saveCheckBox.isChecked()
        self.fileTextEdit.setEnabled(doWrite)
        self.selectFileButton.setEnabled(doWrite)
        
    def _selectFile(self):
        filename = self.fileTextEdit.text()
        filename,_ = QFileDialog.getSaveFileName(self, 'Open file', filename,
                                                 "Log files (*.log *.txt)")
        if filename:
            self.fileTextEdit.setText(filename)

    def _onOK(self):
        filename = self.fileTextEdit.text()
        doWrite = self.saveCheckBox.isChecked()
        updated = self.filename != filename or self.doWrite != doWrite
        if updated:
            newWriter = None
            if doWrite:
                try:
                    newWriter = open(filename, 'w')
                    print('new log file is {}'.format(filename))
                except Exception as e:
                    newWriter = None
                    self.fileOpenError = e
            oldWriter = self.writer
            self.writer = newWriter
            if oldWriter:
                oldWriter.close()
                print('close old log file, {}'.format(self.filename))
        self.filename = filename
        self.doWrite = doWrite
        self.close()

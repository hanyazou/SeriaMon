import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5 import QtCore

from .component import SeriaMonComponent

class Logger(QDialog, SeriaMonComponent):
    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)

        self.writer = None
        self.filename = os.path.join(os.path.expanduser('~'), 'Documents', 'seriamon.log')
        self.doWrite = False

        self.setWindowTitle('Log settings')

        self.saveCheckBox = QCheckBox('Save log as')
        self.saveCheckBox.stateChanged.connect(self._onSaveStateChanged)
        self.saveCheckBox.setChecked(False)

        self.filenameTextEdit = QLineEdit()
        width = self.filenameTextEdit.fontMetrics().boundingRect(self.filename+'____').width()
        self.filenameTextEdit.setMinimumWidth(width)

        self.selectFileButton = QPushButton('...')
        self.selectFileButton.clicked.connect(self._selectFile)

        self.setObjectName('Logger')
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._onOK)
        self.buttons.rejected.connect(self._onCancel)

        grid = QGridLayout()
        grid.addWidget(self.saveCheckBox, 0, 0)
        grid.addWidget(self.filenameTextEdit, 1, 0, 1, 6)
        grid.addWidget(self.selectFileButton, 1, 6)
        grid.addWidget(self.buttons, 2, 0, 1, 7, alignment=QtCore.Qt.AlignRight)
        grid.setColumnStretch(0, 1)
        self.setLayout(grid)

        self.initPreferences('seriamon.logger.{}.'.format(instanceId),
                             [[ str,    'filename', self.filename, self.filenameTextEdit ]])

    def putLog(self, value, compId=None, types=None, timestamp=None):
        if not types:
            types = '-'
        if self.writer:
            self.writer.write('{} {} {} {}\n'.format(timestamp, compId, types, value))
            self.writer.flush()

    def setupDialog(self):
        return self

    def _onSaveStateChanged(self):
        doWrite = self.saveCheckBox.isChecked()
        self.filenameTextEdit.setEnabled(doWrite)
        self.selectFileButton.setEnabled(doWrite)
        
    def _selectFile(self):
        filename = self.filenameTextEdit.text()
        filename,_ = QFileDialog.getSaveFileName(self, 'Open file', filename,
                                                 "Log files (*.log *.txt)")
        if filename:
            self.filenameTextEdit.setText(filename)

    def _onOK(self):
        filename = self.filenameTextEdit.text()
        self.reflectFromUi()
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
                    QMessageBox.critical(self, "Error", '{}'.format(e))
            oldWriter = self.writer
            self.writer = newWriter
            if oldWriter:
                oldWriter.close()
                print('close old log file, {}'.format(self.filename))
        self.filename = filename
        self.doWrite = doWrite
        self.close()

    def _onCancel(self):
        self.reflectToUi()
        self.close()


class LogImporter(QDialog, SeriaMonComponent):
    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)

        self.setObjectName('LogImporter')

        self.sink = sink

        self.filename = os.path.join(os.path.expanduser('~'), 'Documents', 'seriamon.log')
        self.setWindowTitle('Import log')

        self.filenameTextEdit = QLineEdit()
        width = self.filenameTextEdit.fontMetrics().boundingRect(self.filename+'____').width()
        self.filenameTextEdit.setMinimumWidth(width)

        self.selectFileButton = QPushButton('...')
        self.selectFileButton.clicked.connect(self._selectFile)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._onOK)
        self.buttons.rejected.connect(self._onCancel)

        grid = QGridLayout()
        grid.addWidget(self.filenameTextEdit, 0, 0, 1, 6)
        grid.addWidget(self.selectFileButton, 0, 6)
        grid.addWidget(self.buttons, 1, 0, 1, 7, alignment=QtCore.Qt.AlignRight)
        grid.setColumnStretch(0, 1)
        self.setLayout(grid)

        self.initPreferences('seriamon.logger.{}.'.format(instanceId),
                             [[ str,    'filename', self.filename, self.filenameTextEdit ]])

    def setupDialog(self):
        return self

    def _selectFile(self):
        filename = self.filenameTextEdit.text()
        filename,_ = QFileDialog.getSaveFileName(self, 'Open file', filename,
                                                 "Log files (*.log *.txt)")
        if filename:
            self.filenameTextEdit.setText(filename)

    def _onOK(self):
        self.reflectFromUi()
        self.sink.stopLog()
        self.sink.clearLog()
        try:
            reader = open(self.filename, 'r')
            print('read log from file {}'.format(self.filename))
            line = None
            lineCount = 0
            while True:
                line = reader.readline().strip('\n\r')
                if line == '':
                    break
                try:
                    terms = []
                    curPos = 0
                    for i in range(4):
                        nextPos = line.find(' ', curPos)
                        if nextPos < -1:
                            continue
                        terms.append(line[curPos:nextPos])
                        curPos = nextPos + 1
                    terms.append(line[curPos:])
                    lineCount += 1
                    timestamp = datetime.strptime('{} {}'.format(terms[0], terms[1]),
                                                  '%Y-%m-%d %H:%M:%S.%f')
                    self.sink.putLog(value=terms[4], compId = int(terms[2]), types=terms[3],
                                     timestamp=timestamp)
                except Exception as e:
                    print(e)
        except Exception as e:
            reader = None
            QMessageBox.critical(self, "Error", '{}'.format(e))
        finally:
            self.close()

    def _onCancel(self):
        self.reflectToUi()
        self.close()

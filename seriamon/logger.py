import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5 import QtCore

from .component import SeriaMonComponent

class Logger(QDialog, SeriaMonComponent):
    def __init__(self, sink, instanceId=0):
        super().__init__(sink=sink, instanceId=instanceId)

        self.writer = None

        self.setWindowTitle('Log settings')

        self.saveCheckBox = QCheckBox('Save log as')
        self.saveCheckBox.stateChanged.connect(self._onSaveStateChanged)
        self.saveCheckBox.setChecked(False)

        self.foldernameTextEdit = QLineEdit()
        width = self.foldernameTextEdit.fontMetrics().boundingRect('_' * 60).width()
        self.foldernameTextEdit.setMinimumWidth(width)

        self.selectFolderButton = QPushButton('...')
        self.selectFolderButton.clicked.connect(self._selectFolder)

        self.filenameTextEdit = QLineEdit()
        self.filenameTextEdit.setMinimumWidth(width)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._onOK)
        self.buttons.rejected.connect(self._onCancel)

        grid = QGridLayout()
        grid.addWidget(self.saveCheckBox, 0, 0)
        grid.addWidget(self.foldernameTextEdit, 1, 0, 1, 6)
        grid.addWidget(self.selectFolderButton, 1, 6)
        grid.addWidget(self.filenameTextEdit, 2, 0, 1, 7)
        grid.addWidget(self.buttons, 3, 0, 1, 7, alignment=QtCore.Qt.AlignRight)
        grid.setColumnStretch(0, 1)
        self.setLayout(grid)

        foldername = os.path.join(os.path.expanduser('~'), 'Documents')
        filename = 'seriamon-%Y%m%d-%H%M%S.log'
        self.initPreferences('seriamon.logger.{}.'.format(instanceId),
                             [[ str,    'foldername', foldername, self.foldernameTextEdit ],
                              [ str,    'filename',   filename,   self.filenameTextEdit ],
                              [ bool,   'doWrite',    False,      self.saveCheckBox ]])

    def putLog(self, value, compId=None, types=None, timestamp=None):
        if not types:
            types = '_'
        if self.writer:
            if isinstance(value, str):
                value = value.rstrip('\n\r')
            if isinstance(compId, int):
                self.writer.write('{} {:02} {} {}\n'.format(timestamp, compId, types, value))
            else:
                self.writer.write('{} {:2} {} {}\n'.format(timestamp, compId, types, value))
            self.writer.flush()

    def setupDialog(self):
        return self

    def updatePreferences(self):
        super().updatePreferences()
        self._onSaveStateChanged()
        self._reopen()

    def _onSaveStateChanged(self):
        doWrite = self.saveCheckBox.isChecked()
        self.filenameTextEdit.setEnabled(not doWrite)
        self.foldernameTextEdit.setEnabled(not doWrite)
        self.selectFolderButton.setEnabled(not doWrite)
        
    def _selectFolder(self):
        foldername = self.foldernameTextEdit.text()
        foldername_ = QFileDialog.getExistingDirectory(self, 'Open Directory', foldername, QFileDialog.ShowDirsOnly)
        if foldername_:
            self.foldernameTextEdit.setText(foldername_)

    def _onOK(self):
        filename = self.filename
        foldername = self.foldername
        doWrite = self.doWrite
        self.reflectFromUi()
        updated = self.filename != filename or self.foldername != foldername or self.doWrite != doWrite
        if updated:
            self._reopen()
        self.close()

    def _onCancel(self):
        self.reflectToUi()
        self.close()

    def _reopen(self):
        newWriter = None
        if self.doWrite:
            try:
                filename = os.path.join(self.foldername, datetime.now().strftime(self.filename))
                self.log(self.LOG_INFO, 'new log file is {}'.format(filename))
                newWriter = open(filename, 'w', encoding="utf-8")
                self.writer_filename = filename
            except Exception as e:
                newWriter = None
                QMessageBox.critical(self, "Error", '{}'.format(e))
        oldWriter = self.writer
        self.writer = newWriter
        if oldWriter:
            oldWriter.close()
            self.log(self.LOG_INFO, 'close old log file, {}'.format(self.writer_filename))


class LogImporter(QDialog, SeriaMonComponent):
    def __init__(self, sink, instanceId=0):
        super().__init__(sink=sink, instanceId=instanceId)

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

        self.initPreferences('seriamon.logimporter.{}.'.format(instanceId),
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
            self.log(self.LOG_INFO, 'read log from file {}'.format(self.filename))
            line = None
            lineCount = 0
            log = []
            while line != '':
                line = reader.readline().strip('\n\r')
                if line != '':
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
                        log.append([terms[4], int(terms[2]), terms[3], timestamp])
                    except Exception as e:
                        self.log(self.LOG_ERROR, e)
                        self.log(self.LOG_ERROR, 'ignore line; {}'.format(line))
                if 100 <= len(log) or line == '':
                    self.sink.importLog(log)
                    log = []
                
        except Exception as e:
            reader = None
            QMessageBox.critical(self, "Error", '{}'.format(e))
        finally:
            self.close()

    def _onCancel(self):
        self.reflectToUi()
        self.close()

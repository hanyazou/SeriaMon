import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QTextCursor

class TextViewer(QWidget):
    def __init__(self, compId, sink, instanceId=0):
        super().__init__()

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

        self.compIdCheckBox = QCheckBox('port id')
        self.compIdCheckBox.setChecked(False)

        grid = QGridLayout()
        grid.addWidget(self.textEdit, 0, 0, 1, 7)
        grid.addWidget(self.autoScrollCheckBox, 1, 4)
        grid.addWidget(self.timestampCheckBox, 1, 5)
        grid.addWidget(self.compIdCheckBox, 1, 6)
        grid.setRowStretch(0, 1)
        grid.setColumnStretch(0, 1)

        self.setLayout(grid)

    def putLog(self, value, compId, types, timestamp):
        cursor = QTextCursor(self.textEdit.document())
        cursor.movePosition(QTextCursor.End)
        if self.timestampCheckBox.isChecked():
            cursor.insertText("{} ".format(timestamp.isoformat(sep=' ', timespec='milliseconds')))
        if self.compIdCheckBox.isChecked():
            cursor.insertText('{} '.format(compId))
        cursor.insertText('{}\n'.format(value))
        if self.autoScrollCheckBox.isChecked():
            scrollbar = self.textEdit.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum() - 1)

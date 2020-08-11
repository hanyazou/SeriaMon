import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QTextCursor

class Viewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

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

        self.sourceIdCheckBox = QCheckBox('port id')
        self.sourceIdCheckBox.setChecked(False)

        grid = QGridLayout()
        grid.addWidget(self.textEdit, 0, 0, 1, 7)
        grid.addWidget(self.autoScrollCheckBox, 1, 4)
        grid.addWidget(self.timestampCheckBox, 1, 5)
        grid.addWidget(self.sourceIdCheckBox, 1, 6)
        grid.setRowStretch(0, 1)
        grid.setColumnStretch(0, 1)

        self.setLayout(grid)

    def putLog(self, value, sourceId, op, timestamp):
        cursor = QTextCursor(self.textEdit.document())
        cursor.movePosition(QTextCursor.End)
        if self.timestampCheckBox.isChecked():
            cursor.insertText("{} ".format(timestamp.isoformat(sep=' ', timespec='milliseconds')))
        if self.sourceIdCheckBox.isChecked():
            cursor.insertText('{} '.format(sourceId))
        cursor.insertText('{}\n'.format(value))
        if self.autoScrollCheckBox.isChecked():
            scrollbar = self.textEdit.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum() - 1)

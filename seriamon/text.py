from PyQt5.QtWidgets import *
from PyQt5.QtGui import QTextCursor

from seriamon.component import SeriaMonComponent
from seriamon.preferences import Preferences

class TextViewer(QWidget, SeriaMonComponent):
    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)

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

        self.internalMsgCheckBox = QCheckBox('internal message')
        self.internalMsgCheckBox.setChecked(False)

        self.initPreferences('seriamon.textviewer.{}.'.format(instanceId),
                             [[ bool,   'autoScroll', True,   self.autoScrollCheckBox ],
                              [ bool,   'timestamp',  True,   self.timestampCheckBox ],
                              [ bool,   'compId',     False,  self.compIdCheckBox ],
                              [ bool,   'internalMsg',False,  self.internalMsgCheckBox ]])

        grid = QGridLayout()
        grid.addWidget(self.textEdit, 0, 0, 1, 8)
        grid.addWidget(self.autoScrollCheckBox, 1, 4)
        grid.addWidget(self.timestampCheckBox, 1, 5)
        grid.addWidget(self.compIdCheckBox, 1, 6)
        grid.addWidget(self.internalMsgCheckBox, 1, 7)
        grid.setRowStretch(0, 1)
        grid.setColumnStretch(0, 1)

        self.setLayout(grid)

    def putLog(self, value, compId=None, types=None, timestamp=None):
        if not self.internalMsgCheckBox.isChecked() and 'i' in types:
            return
        cursor = QTextCursor(self.textEdit.document())
        cursor.movePosition(QTextCursor.End)
        if self.timestampCheckBox.isChecked():
            cursor.insertText("{} ".format(timestamp.isoformat(sep=' ', timespec='milliseconds')))
        if self.compIdCheckBox.isChecked():
            cursor.insertText('{:02} '.format(compId))
        cursor.insertText('{}\n'.format(str(value).rstrip('\n\r')))
        while Preferences.getInstance().scroll_buffer < self.textEdit.document().blockCount() - 1:
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        if self.autoScrollCheckBox.isChecked():
            scrollbar = self.textEdit.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum() - 1)

    def clearLog(self):
        self.textEdit.clear()

from PyQt5 import QtCore
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
                             [[ bool,   'autoScroll',    True,   self.autoScrollCheckBox ],
                              [ bool,   'timestamp',     True,   self.timestampCheckBox ],
                              [ bool,   'compId',        False,  self.compIdCheckBox ],
                              [ bool,   'internalMsg',   False,  self.internalMsgCheckBox ],
                              [ str,    'splitterState', None    ]])

        self.splitter = QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(self.textEdit)

        layout = QVBoxLayout()
        layout.addWidget(self.autoScrollCheckBox)
        layout.addWidget(self.timestampCheckBox)
        layout.addWidget(self.compIdCheckBox)
        layout.addWidget(self.internalMsgCheckBox)
        panel = QWidget()
        panel.setLayout(layout)
        scrollarea = QScrollArea()
        scrollarea.setWidget(panel)
        self.splitter.addWidget(scrollarea)

        layout = QVBoxLayout()
        layout.addWidget(self.splitter)
        self.setLayout(layout)

    def reflectToUi(self, items=None):
        super().reflectToUi(items)
        if self.splitterState:
            self.splitter.restoreState(bytearray.fromhex(self.splitterState))

    def reflectFromUi(self, items=None):
        super().reflectFromUi(items)
        self.splitterState = ''.join(['{:02x}'.format(data[0]) for data in self.splitter.saveState()])

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
        scrollbar = self.textEdit.verticalScrollBar()
        scrollpos = scrollbar.maximum() - scrollbar.value()
        while Preferences.getInstance().scroll_buffer < self.textEdit.document().blockCount() - 1:
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        if self.autoScrollCheckBox.isChecked():
            scrollpos = -1
        scrollbar.setValue(scrollbar.maximum() - scrollpos)

    def clearLog(self):
        self.textEdit.clear()

from PyQt5 import QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QTextCursor

from .component import *
from .preferences import Preferences

class TextViewer(QWidget, SeriaMonComponent):
    def __init__(self, sink, instanceId=0):
        super().__init__(sink=sink, instanceId=instanceId)

        self.buffer = []
        self.last_pos = 0
        self.ignore_ui_changes = False
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
        self.timestampCheckBox.stateChanged.connect(self.display_settings_changed)

        self.compIdCheckBox = QCheckBox('port id')
        self.compIdCheckBox.setChecked(False)
        self.compIdCheckBox.stateChanged.connect(self.display_settings_changed)

        self.internalMsgCheckBox = QCheckBox('internal message')
        self.internalMsgCheckBox.setChecked(False)
        self.internalMsgCheckBox.stateChanged.connect(self.display_settings_changed)

        self.initPreferences('seriamon.textviewer.{}.'.format(instanceId),
                             [[ bool,   'auto_scroll',      True,   self.autoScrollCheckBox ],
                              [ bool,   'show_timestamp',   True,   self.timestampCheckBox ],
                              [ bool,   'show_compid',      False,  self.compIdCheckBox ],
                              [ bool,   'show_internalmsg', False,  self.internalMsgCheckBox ],
                              [ str,    'splitterState',    None    ]])

        self.splitter = QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(self.textEdit)

        layout = QVBoxLayout()
        layout.addWidget(self.autoScrollCheckBox)
        layout.addWidget(self.timestampCheckBox)
        layout.addWidget(self.compIdCheckBox)
        layout.addWidget(self.internalMsgCheckBox)
        self.compid_checkboxes = []
        self.visible_compids = [ 0 ]
        for comp in ComponentManager.get_instance().getComponents():
            if not isinstance(comp, SeriaMonPort):
                continue
            compid = comp.getComponentId()
            cb = QCheckBox(f"{compid:2d} {comp.getComponentName()}")
            cb.setChecked(True)
            cb.stateChanged.connect(self.display_settings_changed)
            layout.addWidget(cb)
            self.compid_checkboxes.append((compid, cb))
            self.visible_compids.append(compid)
        panel = QWidget()
        panel.setLayout(layout)
        scrollarea = QScrollArea()
        scrollarea.setWidget(panel)
        self.splitter.addWidget(scrollarea)

        layout = QVBoxLayout()
        layout.addWidget(self.splitter)
        self.setLayout(layout)

    def reflectToUi(self, items=None):
        self.ignore_ui_changes = True
        super().reflectToUi(items)
        if self.splitterState:
            self.splitter.restoreState(bytearray.fromhex(self.splitterState))
        self.ignore_ui_changes = False
        self.redraw()

    def reflectFromUi(self, items=None):
        super().reflectFromUi(items)
        self.splitterState = ''.join(['{:02x}'.format(data[0]) for data in self.splitter.saveState()])
        self.visible_compids = [ 0 ]
        for (compid, cb) in self.compid_checkboxes:
            if cb.isChecked():
                self.visible_compids.append(compid)

    def putLog(self, value, compid=None, types=None, timestamp=None):
        value = str(value).rstrip('\n\r')
        if Preferences.getInstance().scroll_buffer <= len(self.buffer):
            self.buffer = self.buffer[len(self.buffer) - Preferences.getInstance().scroll_buffer + 1 : ]
        pos = self.append_to_textedit(timestamp, value, compid, types)
        self.buffer.append([pos, timestamp, value, compid, types])

    def clearLog(self):
        self.buffer = []
        self.redraw()

    def append_to_textedit(self, timestamp, value, compid, types) -> int:
        if not self.show_internalmsg and 'i' in types:
            return self.last_pos
        if not compid in self.visible_compids:
            return self.last_pos
        cursor = QTextCursor(self.textEdit.document())
        cursor.movePosition(QTextCursor.End)
        line = ''
        if self.show_timestamp:
            line += "{} ".format(timestamp.isoformat(sep=' ', timespec='milliseconds'))
        if self.show_compid:
            if isinstance(compid, int):
                line += '{:02} '.format(compid)
            else:
                line += '{:2} '.format(compid)
        line += value
        line += '\n'
        cursor.insertText(line)
        scrollbar = self.textEdit.verticalScrollBar()
        scrollpos = scrollbar.maximum() - scrollbar.value()
        while Preferences.getInstance().scroll_buffer < self.textEdit.document().blockCount() - 1:
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        if self.autoScrollCheckBox.isChecked():
            scrollpos = 1
        scrollbar.setValue(scrollbar.maximum() - scrollpos)
        self.last_pos = scrollbar.maximum() - 1
        return self.last_pos

    def get_index_from_pos(self, pos: int) -> int:
        for index in range(len(self.buffer)-1, -1, -1):
            if self.buffer[index][0] <= pos:
                return index
        return 0

    def get_pos_from_index(self, index: int) -> int:
        if len(self.buffer) == 0:
            return 0
        if len(self.buffer) <= index:
            return self.buffer[-1][0]
        if 0 <= index:
            return self.buffer[index][0]
        return 0

    def redraw(self):
        index = self.get_index_from_pos(self.textEdit.verticalScrollBar().value())
        self.textEdit.clear()
        self.last_pos = 0
        for line in self.buffer:
            line[0] = self.append_to_textedit(line[1], line[2], line[3], line[4])
        self.textEdit.verticalScrollBar().setValue(self.get_pos_from_index(index))

    def display_settings_changed(self):
        if self.ignore_ui_changes:
            return
        self.reflectFromUi()
        self.redraw()
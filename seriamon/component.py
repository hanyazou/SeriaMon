from PyQt5.QtWidgets import *
from PyQt5 import QtCore

class SeriaMonComponent:

    STATUS_NONE = 0
    STATUS_ACTIVE = 1
    STATUS_DEACTIVE = 2
    STATUS_WAITING = 3
    STATUS_ERROR = 4

    updated = QtCore.pyqtSignal(object)

    def __init__(self, compId, sink, instanceId=0):
        self.compId = compId
        self.sink = sink
        self._seriamoncomponent_status = self.STATUS_NONE

    def setStatus(self, status):
        self._seriamoncomponent_status = status
        self.updated.emit(self)

    def getStatus(self):
        return self._seriamoncomponent_status

    def savePreferences(self, prefs):
        self.reflectFromUi()
        for prop in self.preferencePoperties:
            typ = prop[0]
            name = prop[1]
            value = getattr(self, name)
            if typ == bool:
                value = int(value)
            prefs[self.preferenceKeyPrefix + name] = str(value)

    def loadPreferences(self, prefs):
        for prop in self.preferencePoperties:
            typ = prop[0]
            name = prop[1]
            key = self.preferenceKeyPrefix + name
            if not key in prefs:
                continue
            value = str(prefs[key])
            if not value:
                continue
            if typ == bool:
                value = int(value)
            setattr(self, name, typ(value))
        self.reflectToUi()

    def initPreferences(self, prefix, prefprops):
        self.preferenceKeyPrefix = prefix
        self.preferencePoperties = prefprops
        for prop in prefprops:
            typ = prop[0]
            name = prop[1]
            value = prop[2]
            if value is None:
                setattr(self, name, None)
            else:
                setattr(self, name, typ(value))
        self.reflectToUi()

    def reflectToUi(self):
        for prop in self.preferencePoperties:
            typ = prop[0]
            name = prop[1]
            value = getattr(self, name)
            if 4 <= len(prop):
                widget = prop[3]
            else:
                widget = None
            if value is not None and typ in (str, int, float) and isinstance(widget, QComboBox):
                index = widget.findData(typ(value))
                if 0 <= index:
                    widget.setCurrentIndex(index)
                else:
                    widget.addItem(str(value), typ(value))
                    widget.setCurrentText(str(value))
            elif value is not None and typ is bool and isinstance(widget, QCheckBox):
                widget.setChecked(typ(value))
            elif value is not None and typ in (str, int, float) and isinstance(widget, QLineEdit):
                widget.setText(typ(value))
            elif widget is not None and value is not None:
                print('WARNING: failed to reflect {} {} to UI'.format(name, value))

    def reflectFromUi(self):
        for prop in self.preferencePoperties:
            typ = prop[0]
            name = prop[1]
            if 4 <= len(prop):
                widget = prop[3]
            else:
                widget = None
            if isinstance(widget, QComboBox):
                setattr(self, name, typ(widget.currentData()))
            elif typ is bool and isinstance(widget, QCheckBox):
                setattr(self, name, typ(widget.isChecked()))
            elif typ in (str, int, float) and isinstance(widget, QLineEdit):
                setattr(self, name, typ(widget.text()))
            elif not widget is None:
                print('WARNING: failed to reflect {} from UI'.format(name))

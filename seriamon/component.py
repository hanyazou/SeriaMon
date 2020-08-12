from PyQt5.QtWidgets import *

class SeriaMonComponent:

    def __init__(self, compId, sink, instanceId=0):
        self.compId = compId
        self.sink = sink

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
            setattr(self, name, typ(value))

    def reflectToUi(self):
        for prop in self.preferencePoperties:
            typ = prop[0]
            name = prop[1]
            if 4 <= len(prop):
                widget = prop[3]
            else:
                widget = None
            if typ in (str, int, float) and isinstance(widget, QComboBox):
                index = widget.findData(typ(getattr(self, name)))
                if 0 <= index:
                    widget.setCurrentIndex(index)
                else:
                    print('WARNING: failed to reflect {} to UI'.format(name))
            elif typ is bool and isinstance(widget, QCheckBox):
                widget.setChecked(typ(getattr(self, name)))
            elif not widget is None:
                print('WARNING: failed to reflect {} to UI'.format(name))

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
            elif not widget is None:
                print('WARNING: failed to reflect {} from UI'.format(name))

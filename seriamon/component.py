import threading
import traceback
from PyQt5.QtWidgets import *
from PyQt5 import QtCore

from .preferences import Preferences

class SeriaMonComponent:

    STATUS_NONE = 0
    STATUS_ACTIVE = 1
    STATUS_DEACTIVE = 2
    STATUS_WAITING = 3
    STATUS_ERROR = 4

    LOG_DEBUG = 1
    LOG_INFO = 2
    LOG_WARNING = 3
    LOG_ERROR = 4
    LOG_NONE = 99

    _manager = None
    _compId = 0

    component_default_name = None
    component_default_num_of_instances = 1

    updated = QtCore.pyqtSignal(object)

    @staticmethod
    def setManager(manager):
        SeriaMonComponent._manager = manager

    def __init__(self, sink=None, instanceId=0):
        self.compId = SeriaMonComponent._compId
        SeriaMonComponent._compId += 1
        self.instanceId = instanceId
        self.log_level = Preferences.getInstance().default_log_level
        self.sink = sink
        self.loadingPreferences = False
        self.preferencePoperties = []
        self._seriamoncomponent_status = self.STATUS_NONE
        self._initialized = None
        if self.component_default_name:
            name = self.component_default_name
        else:
            name = type(self).__name__
        if 0 < instanceId:
            self.setComponentName('{} {}'.format(name, instanceId))
        else:
            self.setComponentName(name)
        if SeriaMonComponent._manager:
            SeriaMonComponent._manager.register(self)

    def initialized(self):
        self.initialized = True

    def setStatus(self, status):
        self._seriamoncomponent_status = status
        if isinstance(self, QtCore.QObject):
            self.updated.emit(self)

    def getStatus(self):
        return self._seriamoncomponent_status

    def setComponentName(self, name, instanceId=None):
        if instanceId is None:
            self._component_name = name
        else:
            self._component_name = ('{} {}'.format(name, instanceId))
        if isinstance(self, QWidget):
            self.setObjectName(self._component_name)

    def getComponentName(self):
        return self._component_name

    def setSink(self, sink):
        self.sink = sink

    def importLog(self, log):
        for value, compId, types, timestamp in log:
            self.putLog(value, compId=compId, types=types, timestamp=timestamp)

    def savePreferences(self, prefs):
        self.log(self.LOG_DEBUG, 'savePreferences: {}'.format(self))
        self.reflectFromUi()
        for prop in self.preferencePoperties:
            typ = prop[0]
            name = prop[1]
            value = getattr(self, name)
            if typ == bool:
                value = int(value)
            else:
                value = typ(value)
            prefs[self.preferenceKeyPrefix + name] = str(value)
            self.log(self.LOG_DEBUG, 'savePreferences: {}={}'.format(name, str(value)))

    def loadPreferences(self, prefs):
        self.log(self.LOG_DEBUG, 'loadPreferences: {}'.format(self))
        self.loadingPreferences = True
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
            self.log(self.LOG_DEBUG, 'loadPreferences: {}={}'.format(name, typ(value)))
        self.updatePreferences()
        self.loadingPreferences = False

    def initPreferences(self, prefix, prefprops):
        self.log(self.LOG_DEBUG, 'initPreferences: {}'.format(self))
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

    def updatePreferences(self):
        self.log(self.LOG_DEBUG, 'updatePreferences: {}'.format(self))
        self.log_level = Preferences.getInstance().default_log_level
        self.reflectToUi()

    def reflectToUi(self, items=None):
        self.log(self.LOG_DEBUG, 'reflectToUi')
        if items is not None and type(items) is not list:
            items = [ items ]
        for prop in self.preferencePoperties:
            typ = prop[0]
            name = prop[1]
            if items is not None and not name in items:
                continue
            value = getattr(self, name)
            if 4 <= len(prop):
                widget = prop[3]
            else:
                widget = None
            if value is not None and typ in (str, int, float) and isinstance(widget, QComboBox):
                if widget.isEditable():
                    widget.setCurrentText(str(value))
                    continue
                index = widget.findData(typ(value))
                if 0 <= index:
                    widget.setCurrentIndex(index)
                else:
                    widget.addItem(str(value), typ(value))
                    widget.setCurrentText(str(value))
            elif value is not None and typ is bool and isinstance(widget, QCheckBox):
                widget.setChecked(typ(value))
            elif value is not None and typ in (str, int, float) and isinstance(widget, QLineEdit):
                widget.setText(str(value))
            elif widget is not None and value is not None:
                self.log(self.LOG_WARNING, self.LOG_WARNING, 'failed to reflect {} {} to UI'.format(name, value))

    def reflectFromUi(self, items=None):
        if self.loadingPreferences:
            self.log(self.LOG_DEBUG, 'skip reflectFromUi()')
            return
        if items is not None and type(items) is not list:
            items = [ items ]
        for prop in self.preferencePoperties:
            typ = prop[0]
            name = prop[1]
            if items is not None and not name in items:
                continue
            if 4 <= len(prop):
                widget = prop[3]
            else:
                widget = None
            if isinstance(widget, QComboBox):
                if widget.isEditable():
                    setattr(self, name, typ(widget.currentText()))
                else:
                    setattr(self, name, typ(widget.currentData()))
            elif typ is bool and isinstance(widget, QCheckBox):
                setattr(self, name, typ(widget.isChecked()))
            elif typ in (str, int, float) and isinstance(widget, QLineEdit):
                setattr(self, name, typ(widget.text()))
            elif not widget is None:
                self.log(self.LOG_WARNING, 'failed to reflect {} from UI'.format(name))

    def log(self, level, message=None):
        level_str = ('?', 'D', 'I', 'W', 'E', '?')
        if message is None:
            message = level
            level = self.LOG_INFO
        if self.getComponentName():
            message = '{} {:>16}: {}'.format(level_str[level], self.getComponentName(), message)
        else:
            message = '{} {}'.format(level_str[level], message)
        message = message.replace('\n', '\\n')
        message = message.replace('\r', '\\r')
        if self.log_level <= level:
            print(message)
            if self.sink:
                self.sink.putLog('SeriaMon: {}\n'.format(message), compId = 0, types='i')


class SeriaMonPort(SeriaMonComponent):

    def __init__(self, sink, instanceId=0):
        super().__init__(sink=sink, instanceId=instanceId)


class ComponentManager(SeriaMonComponent):

    def __init__(self, sink=None, instanceId=0):
        self._lock = threading.Lock()
        self._components = []
        super().__init__(sink, instanceId)

    def register(self, comp: SeriaMonComponent, name: str = None):
        if not name:
            name = comp.getComponentName()
        self.log(self.LOG_DEBUG, f'Register component {comp.compId} {name}')
        with self._lock:
            self._components.append(comp)

    def getComponents(self):
        return self._components

    def callAllComponentsMethod(self, method_name: str, excludes = None):
        if not isinstance(excludes, SeriaMonComponent):
            excludes = [ excludes ]
        for comp in self._components:
            if comp is self or comp in excludes:
                continue
            method = getattr(comp, method_name, None)
            if method:
                method()

    def savePreferences(self, filename: str):
        preferences = {}
        for comp in self._components:
            if comp is self:
                continue
            try:
                if isinstance(comp, SeriaMonComponent):
                    comp.savePreferences(preferences)
            except Exception as e:
                for line in traceback.format_exc().splitlines():
                    self.log(self.LOG_ERROR, line)
        with open(filename, 'w') as writer:
            for key, value in preferences.items():
                writer.write('{}: {}\n'.format(key, value))
            writer.close()

    def loadPreferences(self, filename: str):
        preferences = {}
        try:
            reader = open(filename, 'r')
            for line in reader:
                line = line.rstrip('\n\r')
                try:
                    pos = line.index(':')
                    preferences[line[0:pos]] = line[pos+2:]
                except Exception as e:
                    for line in traceback.format_exc().splitlines():
                        self.log(self.LOG_ERROR, line)
                    self.log(self.LOG_ERROR, line)
            reader.close()
        except Exception as e:
            for line in traceback.format_exc().splitlines():
                self.log(self.LOG_ERROR, line)
        for comp in self._components:
            if comp is self:
                continue
            try:
                if isinstance(comp, SeriaMonComponent):
                    comp.loadPreferences(preferences)
            except Exception as e:
                for line in traceback.format_exc().splitlines():
                    self.log(self.LOG_ERROR, line)

    def updatePreferences(self):
        for comp in self._components:
            if comp is self:
                continue
            try:
                if isinstance(comp, SeriaMonComponent):
                    comp.updatePreferences()
            except Exception as e:
                for line in traceback.format_exc().splitlines():
                    self.log(self.LOG_ERROR, line)

import os
import importlib
import inspect
import traceback

from PyQt5.QtWidgets import *

from seriamon.component import *
from seriamon.utils import *
from seriamon.filter import FilterManager
from seriamon.runtime import ScriptRuntime, FilterWrapper

class Component(QWidget, SeriaMonComponent):

    component_default_name = 'Run'
    component_default_num_of_instances = 1
    MAXARGS = 4

    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)

        self.generation = 0
        self.module = None
        self.args = [None] * self.MAXARGS
        self.annotations = [None] * self.MAXARGS
        self.error = None

        self.scriptComboBox = ComboBox()
        self.scriptComboBox.aboutToBeShown.connect(self._updateScripts)
        self.scriptComboBox.currentIndexChanged.connect(self._scriptChanged)
        
        self.runButton = QPushButton()
        self.runButton.clicked.connect(self._buttonClicked)

        layout = QHBoxLayout()
        self.argLabels = []
        self.argComboBoxies = []
        for i in range(self.MAXARGS):
            self.argLabels.append(QLabel('arg{} ='.format(i)))
            self.argComboBoxies.append(ComboBox())
            layout.addWidget(self.argLabels[i])
            layout.addWidget(self.argComboBoxies[i])

        self.initPreferences('{}.{}.{}.'.format(type(self).__module__, type(self).__name__, self.instanceId),
                             [[ str,    'script',   '',     self.scriptComboBox ],
                              [ str,    'arg0',     '',     self.argComboBoxies[0] ],
                              [ str,    'arg1',     '',     self.argComboBoxies[1] ],
                              [ str,    'arg2',     '',     self.argComboBoxies[2] ],
                              [ str,    'arg3',     '',     self.argComboBoxies[3] ],
                              [ bool,   'run',      False,  None ]])

        grid = QGridLayout()
        grid.addWidget(self.scriptComboBox, 0, 0, 1, 3)
        grid.addLayout(layout, 1, 0, 1, 1)
        grid.addWidget(self.runButton, 2, 2)

        self.setLayout(grid)
        self.thread = _Thread(self)
        self.thread.start()

    def setupWidget(self):
        return self

    def stopLog(self):
        self.run = False
        self.updatePreferences()

    def shutdown(self):
        if self.thread:
            self.log(self.LOG_DEBUG, 'Stop internal thread...')
            self.thread.stayAlive = False
            self.thread.wait()

    def updatePreferences(self):
        super().updatePreferences()
        self.scriptComboBox.setEnabled(not self.run)
        for i in range(len(self.argComboBoxies)):
            self.argComboBoxies[i].setEnabled(not self.run)
        self.runButton.setText('Stop' if self.run else 'Run')
        if self.run:
            self.error = False
        self.generation += 1

    def _updateComboBox(self, combobox, choice, choices):
        current = combobox.currentText()
        names = choices.copy()
        combobox.clear()
        if current is not None and current != '' and not current in names:
            names.append(current)
        if choice is not None and choice != '' and not choice in names:
            names.append(choice)
        itr = sorted(names)
        for name in itr:
            combobox.addItem(name, name)
        if current is not None and current != '':
            combobox.setCurrentText(current)
        if choice is not None and choice != '':
            combobox.setCurrentText(choice)

    def _updateScripts(self):
        folder = os.path.join(os.path.dirname(__file__), '..', 'scripts')
        self.log(self.LOG_DEBUG, 'List scripts in {}'.format(folder))
        scripts = [name for name in [x[:-3] for x in os.listdir(folder) if x.endswith('.py')]]
        self.log(self.LOG_DEBUG, '    {}'.format(scripts))
        self._updateComboBox(self.scriptComboBox, self.script, scripts)

    def _buttonClicked(self):
        self.reflectFromUi()
        self.run = not self.run
        self.updatePreferences()

    def _scriptChanged(self):
        current = self.scriptComboBox.currentText()
        runnable = False
        try:
            self.module = importlib.import_module('seriamon.scripts.' + current)
            argspec = inspect.getfullargspec(self.module.run)
            self.argspec = argspec
            self.log(self.LOG_INFO, 'script: {}.run{}'.format(current, argspec))
            if argspec.defaults:
                offs = len(argspec.args) - len(argspec.defaults)
            else:
                offs = len(argspec.args)
            for i in range(len(self.argLabels)):
                if len(argspec.args) <= i:
                    self.argLabels[i].setVisible(False)
                    self.argComboBoxies[i].setVisible(False)
                    self.annotations[i] = None
                    continue

                argname = argspec.args[i]
                self.argLabels[i].setVisible(True)
                self.argLabels[i].setText('{} ='.format(argname))
                self.argComboBoxies[i].setVisible(True)

                self.annotations[i] = None
                if argname in argspec.annotations.keys():
                    self.annotations[i] = argspec.annotations[argname]
                    self.log(self.LOG_INFO, 'arg {} is annotated with {}'.format(argname, self.annotations[i]))
                if self.annotations[i] == ScriptRuntime.Port:
                    ports = [ filter for filter in FilterManager.getFilters().keys() ]
                    self.argComboBoxies[i].setEditable(False)
                    self._updateComboBox(self.argComboBoxies[i], self.args[i], ports)
                else:
                    self.argComboBoxies[i].setEditable(True)
                    self.argComboBoxies[i].clear()

                if offs <= i:
                    if self.argComboBoxies[i] is not None and self.argComboBoxies[i] != '':
                        continue
                    value = argspec.defaults[i - offs]
                    self.log(self.LOG_INFO, 'defaults[{}] = {}'.format(i - offs, value))
                    if not isinstance(value, str):
                        value = str(value)
                    self.argComboBoxies[i].setCurrentText(value)
            runnable = True
        except Exception as e:
            if current is not None and current != '':
                traceback.print_exc()
                self.log(self.LOG_ERROR, e)
        if not runnable:
            for i in range(len(self.argLabels)):
                self.argLabels[i].setVisible(False)
                self.argComboBoxies[i].setVisible(False)
        self.runButton.setEnabled(runnable)

    def __updateArgs(self):
        self.args[0] = self.arg0
        self.args[1] = self.arg1
        self.args[2] = self.arg2
        self.args[3] = self.arg3

    def reflectToUi(self, items=None):
        super().reflectToUi(items)
        self.__updateArgs()

    def reflectFromUi(self, items=None):
        super().reflectFromUi(items)
        self.__updateArgs()


class _Thread(QtCore.QThread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.stayAlive = True

    def run(self):
        parent = self.parent
        prevStatus = parent.STATUS_NONE
        self.generation = parent.generation

        while self.stayAlive:
            """
                update status indicator
            """
            if parent.run:
                if parent.error:
                    status = parent.STATUS_ERROR
                else:
                    status = parent.STATUS_ACTIVE
            else:
                status = parent.STATUS_DEACTIVE
            if prevStatus != status:
                parent.setStatus(status)
                prevStatus = status

            """
                run the script
            """
            if parent.loadingPreferences or self.generation == parent.generation:
                self.msleep(1000)
                continue
            self.generation = parent.generation
            if not parent.run:
                self.msleep(1000)
                continue
            try:
                parent.log(parent.LOG_INFO, "start script {}".format(parent.script))
                for attr in parent.module.__dict__.keys():
                    if isinstance(getattr(parent.module, attr), ScriptRuntime) or getattr(parent.module, attr) is ScriptRuntime:
                        rt = ScriptRuntime()
                        rt.set_logger(parent)
                        setattr(parent.module, attr, rt)
                args = []
                for i in range(len(parent.argspec.args)):
                    arg = None
                    if parent.annotations[i] == ScriptRuntime.Port:
                        if parent.args[i] in FilterManager.getFilters().keys():
                            arg = FilterWrapper(FilterManager.getFilter(parent.args[i]))
                        else:
                            arg = parent.args[i]
                    elif parent.annotations[i]:
                        arg = parent.annotations[i](parent.args[i])
                    else:
                        arg = parent.args[i]
                    args.append(arg)
                parent.module.run(*args)
                parent.log(parent.LOG_INFO, "end script {}".format(parent.script))
            except Exception as e:
                traceback.print_exc()
                parent.log(parent.LOG_ERROR, e)
                parent.error = True
                self.msleep(1000)

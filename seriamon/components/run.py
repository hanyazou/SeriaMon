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

        self.run = False
        self.running = False

        self.module = None
        self.args = [None] * self.MAXARGS
        self.annotations = [None] * self.MAXARGS

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
        self.thread = None

    def setupWidget(self):
        return self

    def start(self):
        if self.running:
            self.log(self.LOG_DEBUG, 'Script is already running.')
            return
        self.log(self.LOG_DEBUG, 'Start script...')
        self.thread = _Thread(self)
        self.running = True
        self.thread.start()

    def stop(self):
        if not self.running:
            self.log(self.LOG_DEBUG, 'Script is not running.')
            return
        if self.thread:
            self.log(self.LOG_DEBUG, 'Stop script...')
            self.thread.stop()
            self.thread.wait()
            self.log(self.LOG_DEBUG, 'Stop script...done')
        self._thead = None
        self.running = False

    def shutdown(self):
        self.stop()

    def updatePreferences(self):
        super().updatePreferences()
        self.scriptComboBox.setEnabled(not self.run)
        for i in range(len(self.argComboBoxies)):
            self.argComboBoxies[i].setEnabled(not self.run)
        if self.run:
            self.start()
        else:
            self.stop()
        self.runButton.setText('Stop' if self.run else 'Run')

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
            self.log(self.LOG_DEBUG, 'script: {}.run{}'.format(current, argspec))
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
                    self.log(self.LOG_DEBUG, 'arg {} is annotated with {}'.format(argname, self.annotations[i]))
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
                    self.log(self.LOG_DEBUG, 'defaults[{}] = {}'.format(i - offs, value))
                    if not isinstance(value, str):
                        value = str(value)
                    self.argComboBoxies[i].setCurrentText(value)
            runnable = True
        except Exception as e:
            if current is not None and current != '':
                for line in traceback.format_exc().splitlines():
                    self.log(self.LOG_ERROR, line)
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
        self.thread_context = None

    def stop(self):
        self.stayAlive = False
        Util.thread_kill(self.thread_context)

    def run(self):
        self.thread_context = Util.thread_context(f'{self.parent.getComponentName()}')
        parent = self.parent

        while self.stayAlive:
            if not parent._initialized:
                break
            self.msleep(100)
        self.msleep(100)

        parent.setStatus(parent.STATUS_ACTIVE)

        """
            run the script
        """
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
        except Util.ThreadKilledException as e:
            parent.setStatus(parent.STATUS_DEACTIVE)
        except Exception as e:
            for line in traceback.format_exc().splitlines():
                parent.log(parent.LOG_ERROR, line)
            parent.setStatus(parent.STATUS_ERROR)
        else:
            parent.setStatus(parent.STATUS_DEACTIVE)

        parent.run = False
        parent.running = False
        parent.updatePreferences()

import os
import importlib
import inspect

from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtCore import QVariant

from seriamon.component import *
from seriamon.utils import *

class Component(QWidget, SeriaMonPort):

    component_default_name = 'Run'
    component_default_num_of_instances = 1

    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)

        self.generation = 0

        self.scriptComboBox = ComboBox()
        self.scriptComboBox.aboutToBeShown.connect(self._updateScripts)
        self.scriptComboBox.currentIndexChanged.connect(self._scriptChanged)
        
        self.runButton = QPushButton()
        self.runButton.clicked.connect(self._buttonClicked)

        layout = QHBoxLayout()
        self.argLabels = []
        self.argComboBoxies = []
        for i in range(4):
            self.argLabels.append(QLabel('arg{} ='.format(i)))
            self.argComboBoxies.append(ComboBox())
            layout.addWidget(self.argLabels[i])
            layout.addWidget(self.argComboBoxies[i])

        self.initPreferences('{}.{}.{}.'.format(type(self).__module__, type(self).__name__, self.instanceId),
                             [[ str,    'script',   '',     self.scriptComboBox ],
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

    def updatePreferences(self):
        super().updatePreferences()
        self.scriptComboBox.setEnabled(not self.run)
        self.runButton.setText('Stop' if self.run else 'Run')
        if self.run:
            self.error = False
        self.generation += 1

    def _updateScripts(self):
        current = self.scriptComboBox.currentText()
        folder = os.path.join(os.path.dirname(__file__), '..', 'scripts')
        self.log(self.LOG_DEBUG, 'List scripts in {}'.format(folder))
        names = [name for name in [x[:-3] for x in os.listdir(folder) if x.endswith('.py')]]
        self.scriptComboBox.clear()
        if current is not None and current != '' and not current in names:
            names.append(current)
        if self.script is not None and self.script != '' in names:
            names.append(self.script)
        itr = sorted(names)
        for name in itr:
            self.scriptComboBox.addItem(name, name)
        self.scriptComboBox.setCurrentText(current)

    def _buttonClicked(self):
        self.reflectFromUi()
        self.run = not self.run
        self.updatePreferences()

    def _scriptChanged(self):
        current = self.scriptComboBox.currentText()
        try:
            module = importlib.import_module('seriamon.scripts.' + current)
            argspec = inspect.getargspec(module.run)
            for i in range(len(self.argLabels)):
                if i < len(argspec.args):
                    self.argLabels.setEnabled(True)
                    self.argLabels.setText(argspec.args[i])
                else:
                    self.argLabels.setEnabled(False)
        except Exception as e:
            pass


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
            if self.generation != parent.generation:
                self.generation = parent.generation
                if parent.run:
                    try:
                        parent.log(parent.LOG_INFO, "start script {}".format(parent.script))
                        module = importlib.import_module('seriamon.scripts.' + parent.script)
                        module.log = parent.log
                        module.run()
                        parent.log(parent.LOG_INFO, "end script {}".format(parent.script))
                    except Exception as e:
                        parent.log(parent.LOG_ERROR, e)
                        parent.error = True
                        self.msleep(1000)
                        continue
            self.msleep(1000)

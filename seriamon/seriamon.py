import sys
import os
import queue
import importlib
import inspect
from datetime import datetime

from PyQt5.QtWidgets import *
from PyQt5 import QtCore

from .component import *
from .plotter import Plotter
from .text import TextViewer
from .logger import Logger, LogImporter
from .filter import PortFilter
from .preferences_dialog import PreferencesDialog
from .utils import Util
from .gpio import *

class mainWindow(QMainWindow, SeriaMonComponent):

    serialPortSignal = QtCore.pyqtSignal(str)

    def __init__(self):
        self.compmgr = ComponentManager()
        SeriaMonComponent.setManager(self.compmgr)
        super().__init__(sink=self)
        self.compmgr.setSink(self)

        self.setComponentName(None)
        Util.set_logger(self)

        """
           initialize properties
        """
        self.prefFilename = os.path.join(os.path.expanduser('~'), '.seriamon.cfg')
        self.NUMPORTS = 4
        self.MAXQUEUESIZE = 10000
        self.queue = queue.Queue(self.MAXQUEUESIZE)
        self.stopped = False

        """
           create components
        """
        # load global preferences at first and load all preferences later again
        self.prefencesDialog = PreferencesDialog(sink=self,
                                                 updateAllComponentPreferences = lambda: self.compmgr.updatePreferences())
        self.compmgr.loadPreferences(self.prefFilename)
        self.log_level = Preferences.getInstance().default_log_level

        self.plotter = Plotter(sink=self)
        self.textViewer = TextViewer(sink=self)
        self.logger = Logger(sink=self)
        self.logImporter = LogImporter(sink=self)

        self.splitter = QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.plotter)
        self.splitter.addWidget(self.textViewer)

        component_folder = os.path.join(os.path.dirname(__file__), 'components')
        """
        Load plugin classes first so that components can use them
        """
        self.log(self.LOG_DEBUG, 'Load plugin classes from {}'.format(component_folder))
        for module_name in [x[:-3] for x in os.listdir(component_folder) if x.endswith('.py')]:
            module = importlib.import_module('.components.' + module_name, 'seriamon')
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, SeriaMonGpioInterface) and obj is not SeriaMonGpioInterface:
                    self.log(self.LOG_DEBUG, f'    add gpio {obj} from {os.path.join(component_folder, module_name)}')
                    GpioManager.register(name, obj)

        self.log(self.LOG_DEBUG, 'Load components from {}'.format(component_folder))
        for module_name in [x[:-3] for x in os.listdir(component_folder) if x.endswith('.py')]:
            module = importlib.import_module('.components.' + module_name, 'seriamon')
            if not 'Component' in [ name for name, obj in inspect.getmembers(module, inspect.isclass) ]:
                continue
            filter = PortFilter(sink=self)
            component = module.Component(sink=filter)
            isport = isinstance(component, SeriaMonPort)
            self.log(self.LOG_DEBUG, '    add compoment {}{} from {}'.format(component.getComponentName(), ' (port)' if isport else '', module_name))
            if isport:
                filter.setSource(component)
            if 1 < component.component_default_num_of_instances:
                component.setComponentName(component.getComponentName() + ' 0')
            for i in range(1, component.component_default_num_of_instances):
                if isport:
                    sink = PortFilter(sink=self)
                else:
                    sink = self
                self.log(self.LOG_DEBUG, '    add compoment {}{} from {}'.format(component.getComponentName(), ' (port)' if isport else '', module_name))
                component = module.Component(sink=sink, instanceId=i)
                if sink is not self:
                    sink.setSource(component)

        self.initPreferences('seriamon.app.',
                             [[ int,    'left',         None    ],
                              [ int,    'top',          None    ],
                              [ int,    'width',        None    ],
                              [ int,    'height',       None    ],
                              [ str,    'splitterState',None    ]])

        self.compmgr.loadPreferences(self.prefFilename)

        # ensure global preferences will be reflected to each components
        self.compmgr.updatePreferences()

        """
           tabbed setup widgets
        """
        self.tabs = QTabWidget()
        for comp in self.compmgr.getComponents():
            method = getattr(comp, 'setupWidget', None)
            if not method:
                continue
            widget = method()
            comp._seriamon_data = {}
            compData = comp._seriamon_data
            compData['name'] = comp.objectName()
            compData['tabs'] = self.tabs
            tabIndex = self.tabs.addTab(widget, compData['name'])
            compData['tabIndex'] = tabIndex
            comp.updated.connect(self._onUpdatedComponent)

        grid = QGridLayout()
        grid.addWidget(self.splitter, 0, 0, 2, 7)
        grid.addWidget(self.tabs, 2, 0, 1, 7, alignment=QtCore.Qt.AlignRight)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        widget = QWidget()
        widget.setLayout(grid)
        self.setCentralWidget(widget)

        """
           menu
        """
        menubar = self.menuBar()
        filemenu = menubar.addMenu('&File')

        menu = QAction('&Preferences', self)
        menu.triggered.connect(self.prefencesDialog.setupDialog().exec)
        filemenu.addAction(menu)
        menu = QAction('&Log...', self)
        menu.triggered.connect(self.logger.setupDialog().exec)
        filemenu.addAction(menu)
        menu = QAction('&Import...', self)
        menu.triggered.connect(self.logImporter.setupDialog().exec)
        filemenu.addAction(menu)

        """
           now we are ready
        """
        self.serialPortSignal.connect(self._handler)
        self.show()
        self.compmgr.callAllComponentsMethod('initialized')

    def reflectToUi(self, items=None):
        super().reflectToUi(items)
        rect = self.geometry()
        if self.left is None:
            self.left = rect.width() / 2
        if self.top is None:
            self.top = rect.height() / 2
        if self.width is None:
            self.width = rect.width()
        if self.height is None:
            self.height = rect.height()
        self.setGeometry(self.left, self.top, self.width, self.height)
        if self.splitterState:
            self.splitter.restoreState(bytearray.fromhex(self.splitterState))

    def reflectFromUi(self, items=None):
        super().reflectFromUi(items)
        rect = self.geometry()
        self.left = rect.left()
        self.top = rect.top()
        self.width = rect.width()
        self.height = rect.height()
        self.splitterState = ''.join(['{:02x}'.format(data[0]) for data in self.splitter.saveState()])

    def putLog(self, value, compId=None, types=None, timestamp=None):
        if self.stopped:
            return
        if compId is None:
            compId = '?'
        if types is None:
            types = ''
        if timestamp is None:
            timestamp = datetime.now()
        self.queue.put([value, compId, types, timestamp ])
        self.serialPortSignal.emit('s')

    def importLog(self, log):
        self.queue.put(log)
        self.serialPortSignal.emit('s')

    def stopLog(self):
        self.compmgr.callAllComponentsMethod('stopLog', excludes=self)

    def clearLog(self):
        self.compmgr.callAllComponentsMethod('clearLog', excludes=self)

    def closeEvent(self, event):
        self.compmgr.savePreferences(self.prefFilename)
        self.compmgr.callAllComponentsMethod('shutdown')
        QMainWindow.closeEvent(self, event)

    def _handler(self, msg):
        while not self.queue.empty():
            item = self.queue.get()
            if type(item[0]) == list:
                self.textViewer.importLog(item)
                self.plotter.importLog(item)
                self.logger.importLog(item)
            else:
                value = item[0]
                compId = item[1]
                types = item[2]
                timestamp = item[3]
                self.textViewer.putLog(value, compId, types, timestamp)
                self.plotter.putLog(value, compId, types, timestamp)
                self.logger.putLog(value, compId, types, timestamp)

    def _onUpdatedComponent(self, component):
        statusMap = { SeriaMonComponent.STATUS_NONE:     '',
                      SeriaMonComponent.STATUS_ACTIVE:   '\U0001F7E2 ', # Green
                      SeriaMonComponent.STATUS_DEACTIVE: '',
                      SeriaMonComponent.STATUS_WAITING:  '\U0001F7E1 ', # Yellow
                      SeriaMonComponent.STATUS_ERROR:    '\U0001F534 '} # Red
        compData = component._seriamon_data
        status = component.getStatus()
        if status in statusMap:
            status = statusMap[status]
        else:
            status = ''
        compData['tabs'].setTabText(compData['tabIndex'], '{} {}'.format(status, compData['name']))

class SeriaMon:
    def __init__(self):
        pass

    def run(self):
        app = QApplication([])
        window = mainWindow()
        window.setWindowTitle('Serial Monitor')
        sys.exit(app.exec_())


if __name__ == '__main__':
    SeriaMon().run()

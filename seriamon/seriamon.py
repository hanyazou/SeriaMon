import sys
import os
import queue
import importlib
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

class mainWindow(QMainWindow, SeriaMonComponent):

    serialPortSignal = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__(compId=0, sink=self)

        self.setComponentName(None)
        Util.set_logger(self)

        """
           initialize properties
        """
        self.prefFilename = os.path.join(os.path.expanduser('~'), '.seriamon.cfg')
        self.NUMPORTS = 4
        self.MAXQUEUESIZE = 10
        self.queue = queue.Queue(self.MAXQUEUESIZE)
        self._initialized = False

        """
           create components
        """
        self.components = [ self ]
        id = 1
        self.prefencesDialog = PreferencesDialog(compId=id, sink=self)
        self.components.append(self.prefencesDialog)
        id += 1

        # load global preferences at first and load all preferences later again
        self._loadPreferences()

        self.plotter = Plotter(compId=id, sink=self)
        self.components.append(self.plotter)
        id += 1
        self.textViewer = TextViewer(compId=id, sink=self)
        self.components.append(self.textViewer)
        id += 1
        self.logger = Logger(compId=id, sink=self)
        self.components.append(self.logger)
        id += 1
        self.logImporter = LogImporter(compId=id, sink=self)
        self.components.append(self.logImporter)
        id += 1

        component_folder = os.path.join(os.path.dirname(__file__), 'components')
        self.log(self.LOG_DEBUG, 'Load components from {}'.format(component_folder))
        for module_name in [x[:-3] for x in os.listdir(component_folder) if x.endswith('.py')]:
            module = importlib.import_module('.components.' + module_name, 'seriamon')
            filter = PortFilter(compId=id, sink=self)
            id += 1
            component = module.Component(compId=id, sink=filter)
            id += 1
            isport = isinstance(component, SeriaMonPort)
            self.log(self.LOG_DEBUG, '    add compoment {}{} from {}'.format(component.getComponentName(), ' (port)' if isport else '', module_name))
            self.components.append(component)
            if isport:
                filter.setSource(component)
            if 1 < component.component_default_num_of_instances:
                component.setComponentName(component.getComponentName() + ' 0')
            for i in range(1, component.component_default_num_of_instances):
                if isport:
                    sink = PortFilter(compId=id, sink=self)
                    id += 1
                else:
                    sink = self
                self.log(self.LOG_DEBUG, '    add compoment {}{} from {}'.format(component.getComponentName(), ' (port)' if isport else '', module_name))
                component = module.Component(compId=id, sink=sink, instanceId=i)
                id += 1
                self.components.append(component)
                if sink is not self:
                    sink.setSource(component)

        self.initPreferences('seriamon.app.',
                             [[ int,    'left',         None    ],
                              [ int,    'top',          None    ],
                              [ int,    'width',        None    ],
                              [ int,    'height',       None    ]])

        self._loadPreferences()

        """
           tabbed setup widgets
        """
        self.tabs = QTabWidget()
        for comp in self.components:
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
        grid.addWidget(self.plotter, 0, 0, 1, 7)
        grid.addWidget(self.textViewer, 1, 0, 1, 7)
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
        self._initialized = True

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

    def reflectFromUi(self, items=None):
        super().reflectFromUi(items)
        rect = self.geometry()
        self.left = rect.left()
        self.top = rect.top()
        self.width = rect.width()
        self.height = rect.height()

    def putLog(self, value, compId=None, types=None, timestamp=None):
        if not self._initialized:
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
        for comp in self.components:
            if comp is self:
                continue
            method = getattr(comp, 'stopLog', None)
            if method:
                method()

    def clearLog(self):
        for comp in self.components:
            if comp is self:
                continue
            method = getattr(comp, 'clearLog', None)
            if method:
                method()

    def closeEvent(self, event):
        self._savePreferences()
        QMainWindow.closeEvent(self, event)

    def _savePreferences(self):
        preferences = {}
        for comp in self.components:
            try:
                if isinstance(comp, SeriaMonComponent):
                    comp.savePreferences(preferences)
            except Exception as e:
                self.log(self.LOG_ERROR, e)
        with open(self.prefFilename, 'w') as writer:
            for key, value in preferences.items():
                writer.write('{}: {}\n'.format(key, value))
            writer.close()

    def _loadPreferences(self):
        preferences = {}
        try:
            reader = open(self.prefFilename, 'r')
            for line in reader:
                line = line.rstrip('\n\r')
                try:
                    pos = line.index(':')
                    preferences[line[0:pos]] = line[pos+2:]
                except Exception as e:
                    self.log(self.LOG_ERROR, e)
                    self.log(self.LOG_ERROR, line)
            reader.close()
        except Exception as e:
            self.log(self.LOG_ERROR, e)
        for comp in self.components:
            try:
                if isinstance(comp, SeriaMonComponent):
                    comp.loadPreferences(preferences)
            except Exception as e:
                self.log(self.LOG_ERROR, e)

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

import sys
import math
from datetime import datetime
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import *
from guiqwt.plot import CurveDialog
from guiqwt.builder import make
from guiqwt.curve import CurvePlot, CurveItem
from guiqwt.styles import CurveParam, LineStyleParam

from .component import SeriaMonComponent

class Plotter(QDialog, SeriaMonComponent):
    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)

        self.setObjectName('Plotter')

        self.MAXSAMPLES = 10000
        self.width = 600.0
        self.penColors = [
            '#0000FF', # Blue
            '#FF0000', # Red
            '#009900', # Green
            '#FF9900', # Orange
            '#CC00CC', # Magenta
            '#666666', # Gray
            '#00CCFF', # Cyan
            '#000000'  # Black
        ]

        self.starttime = None
        self.x = []
        self.y = []
        self.curves = []

        self.plot_window = CurveDialog(edit=False, toolbar=True)
        self.plot = self.plot_window.get_plot()
        self.plot.del_all_items(except_grid=False)
        self.plot_legend = make.legend("TR")
        self.plot.add_item(self.plot_legend)
        self.plot_grid = make.grid()
        self.plot.add_item(self.plot_grid)

        layout = QVBoxLayout()
        layout.addWidget(self.plot_window)
        self.setLayout(layout)

        """
           tabbed setup widget
        """
        self.showGridCheckBox = QCheckBox('show grid')
        self.showGridCheckBox.stateChanged.connect(self._update)
        self.showLegendCheckBox = QCheckBox('show legend')
        self.showLegendCheckBox.stateChanged.connect(self._update)
        self.showToolsCheckBox = QCheckBox('show tools')
        self.showToolsCheckBox.stateChanged.connect(self._update)

        gridlayout = QGridLayout()
        gridlayout.addWidget(self.showGridCheckBox, 0, 0)
        gridlayout.addWidget(self.showLegendCheckBox, 1, 0)
        gridlayout.addWidget(self.showToolsCheckBox, 2, 0)
        gridlayout.setRowStretch(0, 1)
        gridlayout.setColumnStretch(0, 1)

        self._setupTabWidget = QWidget()
        self._setupTabWidget.setLayout(gridlayout)

        self.initPreferences('seriamon.plotter.{}.'.format(instanceId),
                             [[ bool,   'showGrid',    False,  self.showGridCheckBox ],
                              [ bool,   'showLegend',  False,  self.showLegendCheckBox ],
                              [ bool,   'showTools',   False,  self.showToolsCheckBox ]])

        self._update()

    def setupWidget(self):
        return self._setupTabWidget

    def putLog(self, value, compId, types, timestamp):
        try:
            values = [float(v.split(':')[-1]) for v in value.split()]
            self._insert(timestamp.timestamp(), values)
            self._update()
        except Exception as e:
            pass

    def clearLog(self):
        self.x = []
        self.y = []
        self.plot.del_items(self.curves)
        self.curves = []
        self.starttime = None
        self._update()

    def _addCurve(self):
        param = CurveParam()
        # param.label = 'My curve'
        param.line = LineStyleParam()
        param.line.color = self.penColors[len(self.curves)]
        curve = CurveItem(param)
        self.plot.add_item(curve)
        self.curves.append(curve)

    def _insert(self, x, y):
        if not self.starttime:
            self.starttime = x

        if self.MAXSAMPLES <= len(self.x):
            self.x.pop(0)

        self.x.append(x - self.starttime)

        for i in range(len(self.y), len(y)):
            self.y.append([])
            for j in range(0, len(self.x)-1):
                self.y[i].append(y[i])
            self._addCurve()
        for i in range(0, len(y)):
            if self.MAXSAMPLES <= len(self.y[i]):
                self.y[i].pop(0)
            self.y[i].append(y[i])

    def _update(self):
        self.reflectFromUi()

        self.plot_grid.setVisible(self.showGrid)
        self.plot_legend.setVisible(self.showLegend)
        self.plot_window.get_toolbar().setVisible(self.showTools)

        for i in range(0, len(self.curves)):
            self.curves[i].set_data(self.x, self.y[i])

        self.plot.replot()

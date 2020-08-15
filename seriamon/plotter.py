import sys
import math
from datetime import datetime
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import *
from guiqwt.baseplot import BasePlot
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

        self._initLog()

        self.plot_window = CurveDialog(edit=False, toolbar=True)
        self.plot = self.plot_window.get_plot()
        self.plot.del_all_items(except_grid=False)
        self.plot_legend = make.legend("TR")
        self.plot.add_item(self.plot_legend)
        self.plot_grid = make.grid()
        self.plot.add_item(self.plot_grid)
        self.plot_cursor = make.xcursor(0, 0, label='x = %.2f<br>y = %.2f')
        self.plot.add_item(self.plot_cursor)

        self.panScrollBar = QScrollBar(QtCore.Qt.Horizontal)
        self.panScrollBar.valueChanged.connect(self._update_panzoom)

        self.zoomSpinBox = QDoubleSpinBox()
        self.zoomSpinBox.setRange(1.0, 10.0)
        self.zoomSpinBox.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
        self.zoomSpinBox.valueChanged.connect(self._update_panzoom)

        self.zoomSlider = QSlider(QtCore.Qt.Horizontal)
        self.zoomSlider.setRange(1.0, 10.0)
        self.zoomSlider.setSingleStep(0.01)
        self.zoomSlider.valueChanged.connect(lambda x:
                                             self.zoomSpinBox.setValue(self.zoomSlider.value()))

        layout = QGridLayout()
        layout.addWidget(self.plot_window, 0, 0, 1, 8)
        layout.addWidget(self.panScrollBar, 1, 0, 1, 6)
        layout.addWidget(self.zoomSlider, 1, 6)
        layout.addWidget(self.zoomSpinBox, 1, 7)
        layout.setRowStretch(0, 1)
        layout.setColumnStretch(0, 1)
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
        self.showCursorCheckBox = QCheckBox('show cursor')
        self.showCursorCheckBox.stateChanged.connect(self._update)

        gridlayout = QGridLayout()
        gridlayout.addWidget(self.showGridCheckBox, 0, 0)
        gridlayout.addWidget(self.showLegendCheckBox, 1, 0)
        gridlayout.addWidget(self.showToolsCheckBox, 2, 0)
        gridlayout.addWidget(self.showCursorCheckBox, 3, 0)
        gridlayout.setRowStretch(0, 1)
        gridlayout.setColumnStretch(0, 1)

        self._setupTabWidget = QWidget()
        self._setupTabWidget.setLayout(gridlayout)

        self.initPreferences('seriamon.plotter.{}.'.format(instanceId),
                             [[ bool,   'showGrid',    False,  self.showGridCheckBox ],
                              [ bool,   'showLegend',  False,  self.showLegendCheckBox ],
                              [ bool,   'showTools',   False,  self.showToolsCheckBox ],
                              [ bool,   'showCursor', False,  self.showCursorCheckBox ]])

        self._update()

    def setupWidget(self):
        return self._setupTabWidget

    def putLog(self, value, compId, types, timestamp):
        self._putLog(value, compId, types, timestamp)
        self._update()

    def importLog(self, log):
        for value, compId, types, timestamp in log:
            self._putLog(value, compId=compId, types=types, timestamp=timestamp)

        # reset pan and zoom
        self.zoomSpinBox.setValue(1.0)
        # reset cursor position
        self.plot_cursor.setVisible(False)

        self._update()

    def _putLog(self, value, compId, types, timestamp):
        if 'p' not in types:
            return
        try:
            names = []
            values = []
            for term in value.split():
                if ':' in term:
                    name, v = term.split(':')
                else:
                    name = None
                    v = term
                v = float(v)
                names.append(name)
                values.append(v)
            self._insert(compId, names, timestamp.timestamp(), values)
        except Exception as e:
            self.log(self.LOG_WARNING, '{}'.format(e))
            self.log(self.LOG_WARNING, 'ignore log line: {}'.format(value))

    def clearLog(self):
        for curveList in self.curves:
            if curveList is not None:
                self.plot.del_items(curveList)
        self._initLog()
        self._update()

    def _initLog(self):
        self.starttime = None
        self.curves = []
        self.numberOfCurves = 0
        self.xmin = None
        self.xmax = None

    def _curve(self, compId, columum):
        for i in range(len(self.curves), compId + 1):
            self.curves.append([])
        for i in range(len(self.curves[compId]), columum + 1):
            self.curves[compId].append(None)
        if self.curves[compId][columum] is None:
            param = CurveParam()
            param.line = LineStyleParam()
            param.line.color = self.penColors[self.numberOfCurves % len(self.penColors)]
            curve = CurveItem(param)
            curve._seriamon_plotter_data = {}
            curve._seriamon_plotter_data['name'] = None
            curve._seriamon_plotter_data['x'] = []
            curve._seriamon_plotter_data['y'] = []
            self.plot.add_item(curve)
            self.curves[compId][columum] = curve
            self.numberOfCurves += 1
        return self.curves[compId][columum]

    def _insert(self, compId, names, x, y):
        # update epoc and x
        if not self.starttime:
            self.starttime = x
        x -= self.starttime

        # update x range, min anx max 
        if self.xmin is None or x < self.xmin:
            self.xmin = x
        if self.xmax is None or self.xmax < x:
            self.xmax = x

        # store values
        for columum in range(0, len(y)):
            curve = self._curve(compId, columum)
            cd = curve._seriamon_plotter_data
            if names[columum] is not None and cd['name'] != names[columum]:
                self.log(self.LOG_DEBUG, 'columum={}, name={}'.format(columum, names[columum]))
                cd['name'] = names[columum]
                curve.setTitle(names[columum])
                curve.itemChanged()
            if self.MAXSAMPLES <= len(cd['x']):
                cd['x'].pop(0)
                cd['y'].pop(0)
            cd['x'].append(x)
            cd['y'].append(y[columum])

    def _update(self):
        self.reflectFromUi()

        # update curves
        for compId in range(0, len(self.curves)):
            if self.curves[compId] is None:
                continue
            for columum in range(0, len(self.curves[compId])):
                curve = self.curves[compId][columum]
                cd = curve._seriamon_plotter_data
                curve.set_data(cd['x'], cd['y'])

        # update other itesm
        self.plot_grid.setVisible(self.showGrid)
        self.plot_legend.setVisible(self.showLegend)
        self.plot_window.get_toolbar().setVisible(self.showTools)

        self._update_scroll_range()
        if self.showCursor and not self.plot_cursor.isVisible():
            xmin, xmax = self.plot.get_axis_limits(BasePlot.X_BOTTOM)
            ymin, ymax = self.plot.get_axis_limits(BasePlot.Y_LEFT)
            self.plot_cursor.set_pos((xmin + xmax) / 2, (ymin + ymax) / 2)
            self.log(self.LOG_DEBUG, 'relocate cursor at {}, {}'.
                     format((xmin + xmax) / 2, (ymin + ymax) / 2))
        self.plot_cursor.setVisible(self.showCursor)

        # draw plot
        self.plot.replot()

    def _update_panzoom(self):
        zoom = self.zoomSpinBox.value()
        self.zoomSlider.setValue(zoom)

        if self.xmin is not None and self.xmax is not None:
            center = self.panScrollBar.value()
            width = (self.xmax - self.xmin) / zoom / 2
            self.log(self.LOG_DEBUG, 'zoom={}, center={}, width={}'.format(zoom, center, width))
            self.plot.set_axis_limits(BasePlot.X_BOTTOM, center - width, center + width)

        self._update_scroll_range()
        self.plot.replot()

    def _update_scroll_range(self):
        if self.xmin is None or self.xmax is None:
            return
        zoom = self.zoomSpinBox.value()
        pagestep = (self.xmax - self.xmin) / zoom

        self.panScrollBar.setPageStep(pagestep)
        self.panScrollBar.setMinimum(pagestep / 2)
        self.panScrollBar.setMaximum(self.xmax - self.xmin - pagestep / 2)
        self.log(self.LOG_DEBUG, 'scroll: {}-{} step={}'.format(
            self.panScrollBar.minimum(),
            self.panScrollBar.maximum(),
            self.panScrollBar.pageStep()))
            

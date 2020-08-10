import sys
import math
from datetime import datetime
from PyQt5 import QtGui
from PyQt5.QtWidgets import *
import qwt as Qwt

class Plotter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

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

        self.xmin = 0.0
        self.xmax = 0.0
        self.updateRangeX(self.width)
        self.ymin = 0.0
        self.ymax = 0.0
        self.updateRangeY(100.0)
        self.starttime = None
        self.x = []
        self.y = []
        self.curve = []
        self.plot = Qwt.QwtPlot(self)
        self.plot.setCanvasBackground(QtGui.QColor('#FFFfFF'))
        self.plot.setAxisTitle(Qwt.QwtPlot.xBottom, 'time')

        grid = QGridLayout()
        grid.addWidget(self.plot, 0, 0, 1, 1)
        grid.setRowStretch(0, 1)
        grid.setColumnStretch(0, 1)

        self.setLayout(grid)
        self.update()

    def roundup(self, num):
        l = math.ceil(math.log10(num))
        num = num / (10 ** l)
        if num < 0.1:
            num = 0.1
        elif num < 0.2:
            num = 0.2
        elif num < -0.5:
            num = 0.5
        else:
            num = 1.0
        return num * (10 ** l)


    def updateRangeX(self, x):
        if x < self.xmin:
            self.xmin = x
            self.xstep = self.roundup(self.xmax - self.xmin) / 10
        if self.xmax < x:
            self.xmax = x
            self.xstep = self.roundup(self.xmax - self.xmin) / 10

    def reduceRangeX(self):
        self.xmin = self.x[0]

    def updateRangeY(self, y):
        if y < self.ymin:
            self.ymin = y
            self.ystep = self.roundup(self.ymax - self.ymin) / 10
            self.ymin = (self.ymin / self.ystep - 1) * self.ystep
        if self.ymax < y:
            self.ymax = y
            self.ystep = self.roundup(self.ymax - self.ymin) / 10
            self.ymax = int((self.ymax + self.ystep - 1) / self.ystep) * self.ystep

    def addCurve(self):
        curve = Qwt.QwtPlotCurve('');
        curve.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
        pen = QtGui.QPen(QtGui.QColor(self.penColors[len(self.curve) % len(self.penColors)]))
        pen.setWidth(1)
        curve.setPen(pen)
        curve.attach(self.plot)
        self.curve.append(curve)

    def insert(self, x, y):
        if not self.starttime:
            self.starttime = math.floor(datetime.now().timestamp())
            print('start time = {}'.format(self.starttime))

        if self.MAXSAMPLES <= len(self.x):
            self.x.pop(0)
            self.reduceRangeX()
        self.x.append(x - self.starttime)
        self.updateRangeX(x - self.starttime)

        for i in range(len(self.y), len(y)):
            self.y.append([])
            for j in range(0, len(self.x)-1):
                self.y[i].append(y[i])
            self.addCurve()
        for i in range(0, len(y)):
            if self.MAXSAMPLES <= len(self.y[i]):
                self.y[i].pop(0)
            self.y[i].append(y[i])
            self.updateRangeY(y[i])

    def update(self):
        for i in range(0, len(self.curve)):
            self.curve[i].setData(self.x, self.y[i])
        self.plot.setAxisScale(Qwt.QwtPlot.xBottom, max(self.xmin, self.xmax - self.width), self.xmax, self.xstep)
        self.plot.setAxisScale(Qwt.QwtPlot.yLeft, self.ymin, self.ymax, self.ystep * 2)
        self.plot.replot()

import sys
import os
import serial
import serial.tools.list_ports
import errno
import queue
import time
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QTextCursor

from ..component import *
from ..utils import *

class Component(QWidget, SeriaMonPort):

    component_default_name = 'Uart'
    component_default_num_of_instances = 2

    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)

        self.setObjectName(self.getComponentName())

        self.generation = 0

        self.setLayout(self._setupUart())
        self.thread = _ReaderThread(self)
        self.thread.start()
        self.queue = queue.Queue(1)

    def setupWidget(self):
        return self

    def _resetPort(self, port):
        return

    def write(self, data, block=True, timeout=None):
        if isinstance(data, str):
            data = data.encode()
        deadline = Util.deadline(timeout)
        try:
            self.queue.put(data, block=block, timeout=Util.remaining_seconds(deadline))
        except queue.Full as e:
            return False
        self.queue.all_tasks_done.acquire()
        try:
            while self.queue.unfinished_tasks:
                self.queue.all_tasks_done.wait(Util.remaining_seconds(deadline))
                if deadline <= Util.now():
                    if not self.queue.empty():
                        self.queue.get_nowait()
                    return False
        finally:
            self.queue.all_tasks_done.release()
        return True

    def _portHandler(self, port, types):
        if not self.queue.empty():
            try:
                port.write(self.queue.get_nowait())
                self.queue.task_done()
            except queue.Empty as e:
                pass
        value = port.read(size=1000)
        if len(value) == 0:
            # timeout
            return
        if not self.connect:
            # connection was closed
            return
        self.sink.putLog(value, self.compId, types)

    def _setupUart(self):
        self.portnameComboBox = ComboBox()
        self.portnameComboBox.aboutToBeShown.connect(self._updatePortnames)
        
        self.plotCheckBox = QCheckBox('plot')

        self.baudrateComboBox = QComboBox()
        self.baudrateComboBox.addItem('50', 50);
        self.baudrateComboBox.addItem('75', 75);
        self.baudrateComboBox.addItem('110', 110);
        self.baudrateComboBox.addItem('134', 134);
        self.baudrateComboBox.addItem('150', 150);
        self.baudrateComboBox.addItem('200', 200);
        self.baudrateComboBox.addItem('300', 300);
        self.baudrateComboBox.addItem('600', 600);
        self.baudrateComboBox.addItem('1200', 1200);
        self.baudrateComboBox.addItem('1800', 1800);
        self.baudrateComboBox.addItem('2400', 2400);
        self.baudrateComboBox.addItem('4800', 4800);
        self.baudrateComboBox.addItem('9600', 9600);
        self.baudrateComboBox.addItem('19200', 19200);
        self.baudrateComboBox.addItem('38400', 38400);
        self.baudrateComboBox.addItem('57600', 57600);
        self.baudrateComboBox.addItem('115200', 115200);
        self.baudrateComboBox.addItem('230400', 230400);
        self.baudrateComboBox.addItem('460800', 460800);
        self.baudrateComboBox.addItem('500000', 500000);
        self.baudrateComboBox.addItem('576000', 576000);
        self.baudrateComboBox.addItem('921600', 921600);
        self.baudrateComboBox.addItem('1000000', 1000000);
        self.baudrateComboBox.addItem('1152000', 1152000);
        self.baudrateComboBox.addItem('1500000', 1500000);
        self.baudrateComboBox.addItem('2000000', 2000000);
        self.baudrateComboBox.addItem('2500000', 2500000);
        self.baudrateComboBox.addItem('3000000', 3000000);
        self.baudrateComboBox.addItem('3500000', 3500000);
        self.baudrateComboBox.addItem('4000000', 4000000);

        self.bytesizeComboBox = QComboBox()
        self.bytesizeComboBox.addItem('7', QVariant(serial.SEVENBITS))
        self.bytesizeComboBox.addItem('8', QVariant(serial.EIGHTBITS))

        self.parityComboBox = QComboBox()
        self.parityComboBox.addItem('none', QVariant(serial.PARITY_NONE))
        self.parityComboBox.addItem('odd', QVariant(serial.PARITY_ODD))
        self.parityComboBox.addItem('even', QVariant(serial.PARITY_EVEN))

        self.stopbitsComboBox = QComboBox()
        self.stopbitsComboBox.addItem('1', QVariant(serial.STOPBITS_ONE))
        self.stopbitsComboBox.addItem('1.5', QVariant(serial.STOPBITS_ONE_POINT_FIVE))
        self.stopbitsComboBox.addItem('2', QVariant(serial.STOPBITS_TWO))

        self.rtsctsCheckBox = QCheckBox('rtscts')
        self.dsrdtrCheckBox = QCheckBox('dsrdtr')

        self.initPreferences('seriamon.{}.{}.'.format(type(self).__name__, self.instanceId),
                             [[ str,    'portname', None,   self.portnameComboBox ],
                              [ bool,   'plot',     False,  self.plotCheckBox ],
                              [ int,    'baudrate', 9600,   self.baudrateComboBox ],
                              [ int,    'bytesize', 8,      self.bytesizeComboBox ],
                              [ str,    'parity',   'N',    self.parityComboBox ],
                              [ float,  'stopbits', 1,      self.stopbitsComboBox ],
                              [ bool,   'rtscts',   False,  self.rtsctsCheckBox ],
                              [ bool,   'dsrdtr',   False,  self.dsrdtrCheckBox ],
                              [ bool,   'connect',  False,  None ]])

        self.connectButton = QPushButton()
        self.connectButton.clicked.connect(self._buttonClicked)

        layout = QHBoxLayout()
        layout.addWidget(QLabel('baud rate:'))
        layout.addWidget(self.baudrateComboBox)
        layout.addWidget(QLabel('byte size:'))
        layout.addWidget(self.bytesizeComboBox)
        layout.addWidget(QLabel('parity bit:'))
        layout.addWidget(self.parityComboBox)
        layout.addWidget(QLabel('stop bit:'))
        layout.addWidget(self.stopbitsComboBox)
        layout.addWidget(self.rtsctsCheckBox)
        layout.addWidget(self.dsrdtrCheckBox)

        grid = QGridLayout()
        grid.addWidget(self.portnameComboBox, 0, 1, 1, 2)
        grid.addWidget(self.plotCheckBox, 0, 3)
        grid.addLayout(layout, 1, 1, 1, 4)
        grid.addWidget(self.connectButton, 2, 4)
        return grid

    def stopLog(self):
        self.connect = False
        self.updatePreferences()

    def updatePreferences(self):
        super().updatePreferences()
        self.portnameComboBox.setEnabled(not self.connect)
        self.plotCheckBox.setEnabled(not self.connect)
        self.baudrateComboBox.setEnabled(not self.connect)
        self.bytesizeComboBox.setEnabled(not self.connect)
        self.parityComboBox.setEnabled(not self.connect)
        self.stopbitsComboBox.setEnabled(not self.connect)
        self.rtsctsCheckBox.setEnabled(not self.connect)
        self.dsrdtrCheckBox.setEnabled(not self.connect)
        self.connectButton.setText('Disconnect' if self.connect else 'Connect')
        self.generation += 1

    def _updatePortnames(self):
        currentText = self.portnameComboBox.currentText()
        portnames = [v[0] for v in serial.tools.list_ports.comports(include_links=True)]
        self.portnameComboBox.clear()
        if currentText is not None and currentText != '' and not currentText in portnames:
            portnames.append(currentText)
        if self.portname is not None and not self.portname in portnames:
            portnames.append(self.portname)
        itr = sorted(portnames)
        for port in itr:
            self.portnameComboBox.addItem(port, port)
        self.portnameComboBox.setCurrentText(currentText)

    def _buttonClicked(self):
        self.reflectFromUi()
        self.connect = not self.connect
        self.updatePreferences()

class _ReaderThread(QtCore.QThread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.stayAlive = True
        self.generation = parent.generation
        self.port = serial.Serial(timeout=0.5)  # timeout is 500ms

    def run(self):
        parent = self.parent
        error = False
        prevStatus = parent.STATUS_NONE

        while self.stayAlive:
            """
                update status indicator
            """
            if parent.connect:
                if self.port.is_open and not error:
                    status = parent.STATUS_ACTIVE
                else:
                    status = parent.STATUS_WAITING
            else:
                status = parent.STATUS_DEACTIVE
            if prevStatus != status:
                parent.setStatus(status)
                prevStatus = status

            """try to (re)open the port if
                 port settings has been changed
                 connect / disconnect button was clicked
                errors were reported on serial port
            """
            if self.generation != parent.generation or error:
                if self.port.is_open:
                    self.port.close()
                    parent.sink.putLog('---- close port {} -----'.
                                       format(self.port.port), parent.compId)
                if self.parent.connect:
                    self.port.port = parent.portname
                    self.port.baudrate = parent.baudrate
                    self.port.bytesize = parent.bytesize
                    self.port.parity = parent.parity
                    self.port.stopbits = parent.stopbits
                    self.port.rtscts = parent.rtscts
                    self.port.dsrdtr = parent.dsrdtr
                    try:
                        self.port.open()
                        error = False
                    except Exception as e:
                        parent.sink.putLog('----  fail to open {} -----'.
                                           format(self.port.port), parent.compId)
                        print(e)
                        error = True
                        self.msleep(1000)
                        continue
                    parent.sink.putLog('----  open port {} -----'.
                                       format(self.port.port), parent.compId)
                    parent._resetPort(self.port)
                    
                if self.parent.plot:
                    types = 'p'
                else:
                    types = None
                self.generation = parent.generation

            """
               read serial port if it is open
            """
            if self.port.is_open:
                error = False
                try:
                    self.parent._portHandler(self.port, types)
                except Exception as e:
                    print(e)
                    error = True
                    self.msleep(1000)
                    continue
            else:
                self.msleep(1000)

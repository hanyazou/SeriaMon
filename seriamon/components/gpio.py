'''

The MIT License (MIT)

Copyright (c) 2021 @hanyazou

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''

import time
from PyQt5.QtWidgets import *

from seriamon.component import *
from seriamon.utils import *
from seriamon.gpio import *

class Component(QWidget, SeriaMonPort):

    component_default_name = 'Gpio'
    component_default_num_of_instances = 1

    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)
        self._reset_parser()

        self.setLayout(self._setup())

    def setupWidget(self):
        return self

    def write(self, data, block=True, timeout=None):
        if not isinstance(data, str):
            data = data.decode()
        self._parse(data)
        return True

    def putLog(self, value, compId=None, types=None, timestamp=None):
        if not compId:
            compId = self.compId
        self.sink.putLog(value, compId=compId, types=types, timestamp=timestamp)

    def _setup(self):
        self.portnameComboBox = ComboBox()
        self.portnameComboBox.aboutToBeShown.connect(self._updatePortnames)
        
        self.initPreferences('{}.{}.{}.'.format(type(self).__module__, type(self).__name__, self.instanceId),
                             [[ str,    'portname', None,   self.portnameComboBox ],
                              [ bool,   'connect',  False,  None ]])

        self.connectButton = QPushButton()
        self.connectButton.clicked.connect(self._buttonClicked)

        grid = QGridLayout()
        grid.addWidget(self.portnameComboBox, 0, 1, 1, 2)
        # grid.addWidget(self.connectButton, 2, 4)
        return grid

    def updatePreferences(self):
        super().updatePreferences()
        self.portnameComboBox.setEnabled(not self.connect)
        self.connectButton.setText('Disconnect' if self.connect else 'Connect')

    def _updatePortnames(self):
        currentText = self.portnameComboBox.currentText()
        portnames = [str(device) for device in GpioManager.get_list()]
        self.portnameComboBox.clear()
        if currentText is not None and currentText != '' and not currentText in portnames:
            portnames.append(currentText)
        if self.portname is not None and not self.portname in portnames:
            portnames.append(self.portname)
        itr = sorted(portnames)
        for port in itr:
            self.portnameComboBox.addItem(port, port)
        self.portnameComboBox.setCurrentText(currentText)

    def _get_device(self) -> SeriaMonGpioInterface:
        self.reflectFromUi()
        for device in GpioManager.get_list():
            if str(device) == self.portname:
                device.configure()
                return device
        return None

    def _buttonClicked(self):
        self.reflectFromUi()
        self.connect = not self.connect
        self.updatePreferences()

    def _reset_parser(self):
        self.parse_error = False
        self.args = []
        self.buf = ''

    def _parse_buf(self):
        self.log(self.LOG_DEBUG, f'args={self.args}, buf={self.buf}')
        if self.buf == '':
            return
        if not self.args:
            self.args.append(self.buf)
            self.buf = ''
            return
        try:
            self.args.append(int(self.buf, 0))
        except ValueError as e:
            self.log(self.LOG_ERROR, e)
            self.parse_error = True
        self.buf = ''

    def _execute(self):
        if not self.args:
            return
        if self.args[0].lower() == 'on' or self.args[0].lower() == 'off':
            if len(self.args) < 2:
                self.putLog('invalid argument\n')
                self.parse_error = True
                return

            value = self.args[0].lower() == 'on'
            self.putLog(f'set port {self.args[1]} to {value}\n')
            if device := self._get_device():
                device.port_power(self.args[1], value)
            return

        if self.args[0].lower() == 'delay':
            if len(self.args) < 2:
                self.putLog('invalid argument\n')
                self.parse_error = True
                return
            self.log(self.LOG_DEBUG, f'delay {self.args[1]} ms')
            time.sleep(self.args[1] / 1000.0)
            return

        if self.args[0].lower() == 'n?':
            if device := self._get_device():
                self.putLog(f'{4}\n')
            return

        self.putLog(f'unknown comand {self.args[0]}\n')
        self.parse_error = True

    def _parse(self, s):
        if 1 < len(s):
            for c in s:
                self._parse(c)
            return
        c = s
        newline = '\n'
        # self.log(self.LOG_DEBUG, f"input='{c.rstrip(newline)}' (0x{ord(c[0]):02x})")
        if c == '\n' or c == ';' or c == '':
            self._parse_buf()
            if self.parse_error:
                self.putLog(f'parse error {self.args}\n')
            else:
                self._execute()
            self._reset_parser()
            if c == '\n':
                self.putLog('ok\n')
            return

        if self.parse_error or (self.args and c == ' ') or c == '\r':
            # just ignore
            return

        if c == ',' or c == ' ':
            self._parse_buf()
            return

        self.buf += c

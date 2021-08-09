import sys
import os
import asyncio
import errno

from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QTextCursor

from bleak import BleakScanner
from bleak import BleakClient

from ..component import SeriaMonPort
from ..utils import *

__devices__ = {}
__instances__ = [ None, None, None, None ]
__handlers__ = [ None, None, None, None ]

def detection_handler(device, advertisement_data):
    global __devices__
    if device.name == "BDM" and str(device) not in __devices__.keys():
        print("new decice: ", device.address, device.name)
        __devices__[str(device)] = device

def notification_handler(self, sender, data):
    funcs = [ "DC", "AC", "DC", "AC", "Ohm", "Cap", "Hz", "Duty" , "Temp", "Temp", "Diode", "Cont", "hFE", "", "", "" ]
    units = [ "V",  "V",  "A",  "A",  "Ohm", "F",   "Hz", "%" ,    "℃",     "℉",     "V",     "Ohm",        "hFE", "", "", "" ]
    scales = [ "", "n", "u", "m", "", "k", "M" "" ]
    readtypes = [ "Hold", "Delta", "Auto", "Low Battery", "Min", "Max" ]

    d0 = (data[1] << 8| data[0])
    d1 = (data[3] << 8| data[2])
    d2 = (data[5] << 8| data[4])

    func = (d0 >> 6) & 0xf
    scale = (d0 >> 3) & 0x7
    decimal = (d0 >> 0) & 0x3
    if d2 & 0x8000:
        value = -(d2 & 0x7fff)
    else:
        value = d2
    value /= (10 ** decimal)
    # print("{0:04x} {1:04x} {2:04x} ".format(d0, d1, d2), end='')
    log = "{0:>5} {1:10.4f} {2}{3}".format(funcs[func], value, scales[scale], units[func])
    for i in range(len(readtypes)):
        if d1 & (1 << i):
            log += " {}".format(readtypes[i])
    self.sink.putLog(log)
    self.sink.putLog(value, self.compId, self.types)

class Component(QWidget, SeriaMonPort):

    component_default_name = 'BLE'

    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)

        # for DEBUG
        self.log_level = self.LOG_DEBUG

        self.instances[instanceId] = self
        self.setObjectName(self.getComponentName())

        self.generation = 0
        self.thread = _ReaderThread(self)

        self.deviceComboBox = ComboBox()
        self.deviceComboBox.aboutToBeShown.connect(self._updateDevices)
        
        self.plotCheckBox = QCheckBox('plot')

        self.initPreferences('seriamon.blereader.{}.'.format(instanceId),
                             [[ str,    'device',   None,   self.deviceComboBox ],
                              [ bool,   'plot',     False,  self.plotCheckBox ],
                              [ bool,   'connect',  False,  None ]])

        self.connectButton = QPushButton()
        self.connectButton.clicked.connect(self._buttonClicked)

        layout = QHBoxLayout()

        grid = QGridLayout()
        grid.addWidget(self.deviceComboBox, 0, 1, 1, 2)
        grid.addWidget(self.plotCheckBox, 0, 3)
        grid.addLayout(layout, 1, 1, 1, 4)
        grid.addWidget(self.connectButton, 2, 4)
        self.setLayout(grid)

        self.thread.start()

    @property
    def devices(self):
        global __devices__
        return __devices__

    @property
    def handlers(self):
        global __handlers__
        return __handlers__

    @property
    def instances(self):
        global __instances__
        return __instances__

    def setupWidget(self):
        return self

    def stopLog(self):
        self.connect = False
        self.updatePreferences()

    def updatePreferences(self):
        super().updatePreferences()
        self.deviceComboBox.setEnabled(not self.connect)
        self.plotCheckBox.setEnabled(not self.connect)
        self.connectButton.setText('Disconnect' if self.connect else 'Connect')
        self.generation += 1

    def _updateDevices(self):
        currentText = self.deviceComboBox.currentText()
        self.deviceComboBox.clear()
        if currentText is not None and currentText != '' and not currentText in self.devices.keys():
            self.devices[currentText] = None
        if self.device is not None and not self.device in self.devices.keys():
            self.devices[self.device] = None
        itr = sorted(self.devices.keys())
        for device in itr:
            self.deviceComboBox.addItem(device, self.devices[device])
        self.deviceComboBox.setCurrentText(currentText)

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
        # self.port = serial.Serial(timeout=0.5)  # timeout is 500ms

    async def asyncRun(self, loop):
        parent = self.parent
        error = False
        prevStatus = parent.STATUS_NONE
        scanncer = None
        client = None

        if parent.instanceId == 0:
            scanner = BleakScanner()
            scanner.register_detection_callback(detection_handler)
            await scanner.start()

        while self.stayAlive:
            """try to (re)connect the device if
                 device sellection has been changed
                 connect / disconnect button was clicked
                 errors were reported on the connection
            """
            if parent.connect and (self.generation != parent.generation or error):
                if client is not None and (not parent.connect or error) :
                    await client.disconnect()
                    client = None
                    error = False
                if parent.connect:
                    if parent.devices[parent.device] is None:
                        parent.log(parent.LOG_DEBUG, 'waiting for {}...'.format(parent.device))
                    else:
                        parent.log(parent.LOG_DEBUG, "connecting to {}...".format(parent.devices[parent.device]))
                        client = BleakClient(parent.devices[parent.device].address, loop=loop)
                        await client.connect()
                        if parent.plot:
                            parent.types = 'p'
                        else:
                            parent.types = None
                        self.generation = parent.generation

                    services = await client.get_services()
                    value_uuid = None
                    for s in services:
                        print("  ", s.uuid, s.description)
                        for c in s.characteristics:
                            print("    ", c.uuid, c.description)
                            if s.uuid.startswith("0000fff0") and c.uuid.startswith("0000fff4"):
                                value_uuid = c.uuid
                            if s.uuid.startswith("0000180a"):
                                value = await client.read_gatt_char(c.uuid)
                                print("      ", value, ''.join('{:02x}'.format(x) for x in value))

                    if value_uuid:
                        await client.start_notify(value_uuid, parent.handlers[parent.instanceId])

            """
                update status indicator
            """
            if parent.connect and client is not None:
                if await client.is_connected() and not error:
                    status = parent.STATUS_ACTIVE
                else:
                    status = parent.STATUS_WAITING
            else:
                status = parent.STATUS_DEACTIVE
            if prevStatus != status:
                parent.setStatus(status)
                prevStatus = status

            await asyncio.sleep(1.0)

        if scanner:
            await scanner.stop()

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.asyncRun(loop))

"""

"""
def cb0(sender, data):
    global __instances__
    notification_handler(__instances__[0], sender, data)
__handlers__[0] = cb0

def cb1(sender, data):
    global __instances__
    notification_handler(__instances__[1], sender, data)
__handlers__[1] = cb1

def cb2(sender, data):
    global __instances__
    notification_handler(__instances__[2], sender, data)
__handlers__[2] = cb1

def cb3(sender, data):
    global __instances__
    notification_handler(__instances__[3], sender, data)
__handlers__[3] = cb1

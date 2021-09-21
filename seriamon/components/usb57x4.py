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

import sys
import usb
import argparse
from seriamon.gpio import SeriaMonGpioInterface
from seriamon.usbutils import USBUtil

class USB57x4(SeriaMonGpioInterface):
    '''
    AN1903 Configuration Options for USB5734, USB5744, and USB5742
    CONFIGURATION REGISTERS
    '''
    REG_GPIO_PD = 0x082c
    REG_GPIO_DIR = 0x0830
    REG_GPIO_OUT = 0x0834
    REG_GPIO_IN = 0x08348
    REG_GPIO_PU = 0x0834c
    REG_USB2_OCS_STAT = 0x0900
    REG_USB3_OCS_STAT = 0x0902
    REG_USB2_VID = 0x3000
    REG_USB2_PID = 0x3002
    REG_USB2_DID = 0x3004
    REG_CFG1 = 0x3006
    REG_CFG2 = 0x3007
    REG_CFG3 = 0x3008
    REG_USB2_NRD = 0x3009
    REG_USB3_PRT_CFG_SEL1 = 0x3c00
    REG_USB3_PRT_CFG_SEL2 = 0x3c04
    REG_USB3_PRT_CFG_SEL3 = 0x3c08
    REG_USB3_PRT_CFG_SEL4 = 0x3c0c
    REG_USB3_PRT_CFG_SEL_GANG_PIN = 0x40
    REG_USB3_PRT_CFG_SEL_DISABLED = 0x20
    REG_USB3_PRT_CFG_SEL_PREMANENT = 0x10
    REG_USB3_PRT_CFG_SEL_PORT_POWER_SEL_MASK = 0x0f
    REG_OCS_SEL1 = 0x3c20
    REG_OCS_SEL2 = 0x3c24
    REG_OCS_SEL3 = 0x3c28
    REG_OCS_SEL4 = 0x3c2c
    REG_OCS_SEL_PRT_SEL_MASK = 0x0f

    REQ_WRITE = 0x03
    REQ_READ = 0x04

    supported_ids = {
        ( 0x0424, 0x2740 )
    }
    portmap = { 1: 17, 2: 18, 3: 19, 4: 20 }

    def __init__(self, dev: usb.core.Device):
        self.dev = dev

    def __str__(self):
        return USBUtil.device_name(self.dev)

    def _read_register(self, addr, len):
        bmRequestType = usb.util.build_request_type(usb.util.CTRL_IN, usb.util.CTRL_TYPE_VENDOR,
                                                    usb.util.CTRL_RECIPIENT_INTERFACE)
        return self.dev.ctrl_transfer(bmRequestType, self.REQ_READ, addr, 0, len)

    def _read_register32(self, addr):
        buf = self._read_register(addr, 4)
        return (buf[0] << 24) + (buf[1] << 16) + (buf[2] << 8) + buf[3]

    def _read_register8(self, addr):
        buf = self._read_register(addr, 1)
        return buf[0]

    def _write_register(self, addr, value):
        bmRequestType = usb.util.build_request_type(usb.util.CTRL_OUT, usb.util.CTRL_TYPE_VENDOR,
                                                    usb.util.CTRL_RECIPIENT_INTERFACE)
        self.dev.ctrl_transfer(bmRequestType, self.REQ_WRITE, addr, 0, value)

    def _write_register32(self, addr, value):
        buf = [ (value >> 24) & 0xff, (value >> 16) & 0xff, (value >> 8) & 0xff,  value & 0xff ]
        self._write_register(addr, buf)

    def _write_register8(self, addr, value):
        buf = [ value & 0xff ]
        self._write_register(addr, buf)

    def show_registers(self):
        v = ( self._read_register8(self.REG_USB3_PRT_CFG_SEL1),
              self._read_register8(self.REG_USB3_PRT_CFG_SEL2),
              self._read_register8(self.REG_USB3_PRT_CFG_SEL3),
              self._read_register8(self.REG_USB3_PRT_CFG_SEL4))
        print(f'CFG: {v[0]:02x} {v[1]:02x} {v[2]:02x} {v[3]:02x}')
        v = ( self._read_register8(self.REG_OCS_SEL1),
              self._read_register8(self.REG_OCS_SEL2),
              self._read_register8(self.REG_OCS_SEL3),
              self._read_register8(self.REG_OCS_SEL4))
        print(f'OCS: {v[0]:02x} {v[1]:02x} {v[2]:02x} {v[3]:02x}')
        v = self._read_register(self.REG_GPIO_DIR, 4)
        print(f'DIR: {v[0]:02x} {v[1]:02x} {v[2]:02x} {v[3]:02x}')
        v = self._read_register(self.REG_GPIO_OUT, 4)
        print(f'OUT: {v[0]:02x} {v[1]:02x} {v[2]:02x} {v[3]:02x}')

    def show_status(self):
        print(self)
        for port in self.portmap:
            print(f'   Port {port}: {"on" if self.port_power(port) else "off"}')

    def configure(self) -> None:
        regs = {
            ( 1, self.REG_USB3_PRT_CFG_SEL1, self.REG_OCS_SEL1 ),
            ( 2, self.REG_USB3_PRT_CFG_SEL2, self.REG_OCS_SEL2 ),
            ( 3, self.REG_USB3_PRT_CFG_SEL3, self.REG_OCS_SEL3 ),
            ( 4, self.REG_USB3_PRT_CFG_SEL4, self.REG_OCS_SEL4 )
        }
        for port, cfg_sel, ocs_sel in regs:
            self._write_register8(cfg_sel, 0x00)
            self._write_register8(ocs_sel, 0x00)
        dir = self._read_register32(self.REG_GPIO_DIR)
        for port, gpio in self.portmap.items():
            if not (dir & (1 << gpio)):
                self.port_power(port, True)
                dir |= (1 << gpio)
        self._write_register32(self.REG_GPIO_DIR, dir)

    def port_power(self, port, onoff=None) -> bool:
        bit = (1 << self.portmap[port])
        out = self._read_register32(self.REG_GPIO_OUT)
        if onoff is None:
            return True if out & bit else False
        if onoff:
            out |= bit
        else:
            out &= ~bit
        self._write_register32(self.REG_GPIO_OUT, out)
        return onoff

    def get_list(verbose=False) -> list:
        hubs = []
        for dev in usb.core.find(find_all=True):
            if (dev.idVendor, dev.idProduct) in USB57x4.supported_ids:
                hubs.append(USB57x4(dev))
            if (verbose):
                print(USBUtil.device_name(dev))
        if (verbose):
            print(f'{len(hubs)} smart{"s" if len(hubs) else ""} hub found')
        return hubs


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description='usb57x4')
    argparser.add_argument("actions", type=str, nargs='*',
                           help="Specify action {on|off}")
    argparser.add_argument("-p", "--port", dest="port", type=int,
                           help="Specify usb port number")
    argparser.add_argument("-d", "--dump", dest="dump", action="store_true",
                           help="Specify this to dump registers")
    argparser.add_argument("-v", "--verbose", dest="verbose", action="store_true",
                           help="increase output verbosity")
    args = argparser.parse_args()

    hubs = USB57x4.get_list(verbose=args.verbose)

    if not hubs:
        print()
        sys.exit(1)
    if args.dump:
        hubs[0].show_registers()
        sys.exit(0)
    hubs[0].configure()
    for action in args.actions:
        hubs[0].port_power(args.port, True if action == 'on' else False)
    hubs[0].show_status()
    sys.exit(0)

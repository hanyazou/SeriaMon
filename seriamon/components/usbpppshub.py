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

class USBPPPSHub(SeriaMonGpioInterface):

    exclude_ids = {
        ( 0x0424, 0x2744 ),
        ( 0x0424, 0x5744 ),
    }

    def __init__(self, dev: usb.core.Device):
        self.dev = dev

    def __str__(self):
        return USBUtil.device_name(self.dev)

    def show_status(self):
        dev = self.dev
        print(self)
        for port in range(4):
            bmRequestType = usb.util.build_request_type(usb.util.CTRL_IN, usb.util.CTRL_TYPE_CLASS,
                                                        usb.util.CTRL_RECIPIENT_OTHER)
            status = dev.ctrl_transfer(bmRequestType, usb.REQ_GET_STATUS, 0, wIndex=port+1, data_or_wLength=4)
            wPortStatus = (status[1] << 8) | status[0]
            status_string = ""
            if wPortStatus & USBUtil.PORT_STAT_INDICATION:
                status_string += " indication"
            if wPortStatus & USBUtil.PORT_STAT_TEST:
                status_string += " test"
            if wPortStatus & USBUtil.PORT_STAT_HIGH_SPEED:
                status_string += " high-speed"
            if wPortStatus & USBUtil.PORT_STAT_LOW_SPEED:
                status_string += " low-speed"
            if wPortStatus & USBUtil.PORT_STAT_POWER:
                status_string += " power"
            if wPortStatus & USBUtil.PORT_STAT_RESET:
                status_string += " reset"
            if wPortStatus & USBUtil.PORT_STAT_OVER_CURRENT:
                status_string += " over-current"
            if wPortStatus & USBUtil.PORT_STAT_SUSPEND:
                status_string += " suspend"
            if wPortStatus & USBUtil.PORT_STAT_ENABLE:
                status_string += " enable"
            if wPortStatus & USBUtil.PORT_STAT_CONNECTION:
                status_string += " connect"
            if wPortStatus == 0:
                status_string += " off"
            print(f'   Port {port + 1}: {status[1]:02x}{status[0]:02x}{status_string}')

    def port_power(self, port, onoff):
        request = usb.REQ_SET_FEATURE if onoff else usb.REQ_CLEAR_FEATURE
        bmRequestType = usb.util.build_request_type(usb.util.CTRL_IN, usb.util.CTRL_TYPE_CLASS,
                                                    usb.util.CTRL_RECIPIENT_OTHER)
        self.dev.ctrl_transfer(bmRequestType, request, USBUtil.PORT_FEAT_POWER, wIndex=port)

    def configure() -> None:
        pass

    def get_list(verbose=False):
        hubs = []
        for dev in usb.core.find(find_all=True):
            if (dev.idVendor, dev.idProduct) in USBPPPSHub.exclude_ids:
                continue
            if dev.bDeviceClass != usb.CLASS_HUB:
                intf = None
                for cfg in dev:
                    if intf := usb.util.find_descriptor(cfg, bInterfaceClass=usb.CLASS_HUB):
                        break
                if not intf:
                    # this device is not a hub
                    continue
            is_smart_hub = False
            HubCharacteristics = None
            try:
                bmRequestType = usb.util.build_request_type(usb.util.CTRL_IN, usb.util.CTRL_TYPE_CLASS,
                                                            usb.util.CTRL_RECIPIENT_DEVICE)
                hubdesc = dev.ctrl_transfer(bmRequestType, usb.REQ_GET_DESCRIPTOR, usb.DT_HUB << 8, wIndex=0,
                                            data_or_wLength=1024)
                if hubdesc[0] < 5 or hubdesc[1] != 0x29:
                    print('HUB descriptor: invalid descriptor')
                    continue
                NbrPorts = hubdesc[2]
                HubCharacteristics = (hubdesc[4] << 8) | hubdesc[3]
                # print(f'NbrPorts={NbrPorts}, HubCharacteristics={HubCharacteristics:04x}')
                # Power Switching Mode
                if USBUtil.bitfield(HubCharacteristics, 1, 0) != 0x01:
                    # not Individual port power switching
                    continue
                # Over-current Protection Mode
                if USBUtil.bitfield(HubCharacteristics, 4, 3) != 0x01:
                    # not Individual port power switching
                    continue
                is_smart_hub = True
            except Exception as e:
                # print(e)
                pass
            if is_smart_hub:
                hubs.append(USBPPPSHub(dev))
            if (verbose):
                if HubCharacteristics:
                    characteristics_string = f'0x{HubCharacteristics:04x}'
                else:
                    characteristics_string = f' ???? '
                print(f'{dev.idVendor:04x} {dev.idProduct:04x} @ 0x{_usb_portid(dev):08x} '
                      f'{characteristics_string}: '
                      f'{USBUtil.get_string(dev, dev.iManufacturer)} '
                      f'{USBUtil.get_string(dev, dev.iProduct)} '
                      f'{USBUtil.get_string(dev, dev.iSerialNumber)} {"****" if is_smart_hub else ""}')
        if (verbose):
            print(f'{len(hubs)} smart{"s" if len(hubs) else ""} hub found')
        return hubs


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description='usbutils')
    argparser.add_argument("actions", type=str, nargs='*',
                           help="Specify action {on|off}")
    argparser.add_argument("-p", "--port", dest="port", type=int,
                           help="Specify usb port number")
    argparser.add_argument("-v", "--verbose", dest="verbose", action="store_true",
                           help="increase output verbosity")
    args = argparser.parse_args()

    hubs = USBPPPSHub.get_list(verbose=args.verbose)

    if not hubs:
        print()
        sys.exit(1)
    for action in args.actions:
        hubs[0].port_power(args.port, True if action == 'on' else False)
    for dev in hubs:
        dev.show_status()
    sys.exit(0)
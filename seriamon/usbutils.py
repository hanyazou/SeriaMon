import sys
import usb
import argparse

# Universal Serial Bus Specification Revision 2.0
''' 11.24.2.7.1 PortStatusBits
Table 11-21. Port Status Field, wPortStatus
'''
USB_PORT_STAT_CONNECTION   = (1 << 0)
USB_PORT_STAT_ENABLE       = (1 << 1)
USB_PORT_STAT_SUSPEND      = (1 << 2)
USB_PORT_STAT_OVER_CURRENT = (1 << 3)
USB_PORT_STAT_RESET        = (1 << 4)
USB_PORT_STAT_POWER        = (1 << 8)
USB_PORT_STAT_LOW_SPEED    = (1 << 9)
USB_PORT_STAT_HIGH_SPEED   = (1 << 10)
USB_PORT_STAT_TEST         = (1 << 11)
USB_PORT_STAT_INDICATION   = (1 << 12)

''' 11.24.2 Class-specific Requests
Table 11-17. Hub Class Feature Selectors
'''
USB_HUB_FEAT_C_LOCAL_POWER   = 0
USB_HUB_FEAT_C_OVER_CURRENT  = 1
USB_PORT_FEAT_CONNECTION     = 0
USB_PORT_FEAT_ENABLE         = 1
USB_PORT_FEAT_SUSPEND        = 2
USB_PORT_FEAT_OVER_CURRENT   = 3
USB_PORT_FEAT_RESET          = 4
USB_PORT_FEAT_POWER          = 8
USB_PORT_FEAT_LOW_SPEED      = 9
USB_PORT_FEAT_C_CONNECTION   = 16
USB_PORT_FEAT_C_ENABLE       = 17
USB_PORT_FEAT_C_SUSPEND      = 18
USB_PORT_FEAT_C_OVER_CURRENT = 19
USB_PORT_FEATC_RESET         = 20
USB_PORT_FEAT_TEST           = 21
USB_PORT_FEAT_INDICATOR      = 22

def _bitmask(msb, lsb):
    if msb < lsb:
        msb, lsb = lsb, msb
    mask = 0
    for i in range(lsb, msb + 1):
        mask = mask | 1 << i
    return mask

def _bitfield(value, msb, lsb):
    if msb < lsb:
        msb, lsb = lsb, msb
    return (value & _bitmask(msb, lsb)) >> lsb

def _usb_portid(dev: usb.Device):
    portid = dev.bus << 24
    for i, port in enumerate(dev.port_numbers):
        portid |= dev.port_numbers[i] << (20 - i * 4)
    return portid

def _usb_get_string(dev: usb.Device, index):
    if string := usb.util.get_string(dev, index):
        string = string.rstrip(' ')
    return string


class USBSmartHub():

    def __init__(self, dev: usb.core.Device):
        self.dev = dev

    def show_status(self):
        dev = self.dev
        print(f'{dev.idVendor:04x} {dev.idProduct:04x} @ 0x{_usb_portid(dev):08x}: '
              f'{_usb_get_string(dev, dev.iManufacturer)} '
              f'{_usb_get_string(dev, dev.iProduct)} {_usb_get_string(dev, dev.iSerialNumber)}')
        for port in range(4):
            bmRequestType = usb.util.build_request_type(usb.util.CTRL_IN, usb.util.CTRL_TYPE_CLASS,
                                                        usb.util.CTRL_RECIPIENT_OTHER)
            status = dev.ctrl_transfer(bmRequestType, usb.REQ_GET_STATUS, 0, wIndex=port+1, data_or_wLength=4)
            wPortStatus = (status[1] << 8) | status[0]
            status_string = ""
            if wPortStatus & USB_PORT_STAT_INDICATION:
                status_string += " indication"
            if wPortStatus & USB_PORT_STAT_TEST:
                status_string += " test"
            if wPortStatus & USB_PORT_STAT_HIGH_SPEED:
                status_string += " high-speed"
            if wPortStatus & USB_PORT_STAT_LOW_SPEED:
                status_string += " low-speed"
            if wPortStatus & USB_PORT_STAT_POWER:
                status_string += " power"
            if wPortStatus & USB_PORT_STAT_RESET:
                status_string += " reset"
            if wPortStatus & USB_PORT_STAT_OVER_CURRENT:
                status_string += " over-current"
            if wPortStatus & USB_PORT_STAT_SUSPEND:
                status_string += " suspend"
            if wPortStatus & USB_PORT_STAT_ENABLE:
                status_string += " enable"
            if wPortStatus & USB_PORT_STAT_CONNECTION:
                status_string += " connect"
            if wPortStatus == 0:
                status_string += " off"
            print(f'   Port {port + 1}: {status[1]:02x}{status[0]:02x}{status_string}')

    def port_power(self, port, onoff):
        request = usb.REQ_SET_FEATURE if onoff else usb.REQ_CLEAR_FEATURE
        bmRequestType = usb.util.build_request_type(usb.util.CTRL_IN, usb.util.CTRL_TYPE_CLASS,
                                                    usb.util.CTRL_RECIPIENT_OTHER)
        self.dev.ctrl_transfer(bmRequestType, request, USB_PORT_FEAT_POWER, wIndex=port)

    def get_hubs(verbose=False):
        hubs = []
        for dev in usb.core.find(find_all=True):
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
                if _bitfield(HubCharacteristics, 1, 0) != 0x01:
                    # not Individual port power switching
                    continue
                # Over-current Protection Mode
                if _bitfield(HubCharacteristics, 4, 3) != 0x01:
                    # not Individual port power switching
                    continue
                is_smart_hub = True
            except Exception as e:
                # print(e)
                pass
            if is_smart_hub:
                hubs.append(USBSmartHub(dev))
            if (verbose):
                if HubCharacteristics:
                    characteristics_string = f'0x{HubCharacteristics:04x}'
                else:
                    characteristics_string = f' ???? '
                print(f'{dev.idVendor:04x} {dev.idProduct:04x} @ 0x{_usb_portid(dev):08x} '
                      f'{characteristics_string}: '
                      f'{_usb_get_string(dev, dev.iManufacturer)} '
                      f'{_usb_get_string(dev, dev.iProduct)} '
                      f'{_usb_get_string(dev, dev.iSerialNumber)} {"****" if is_smart_hub else ""}')
        if (verbose):
            print(f'{len(hubs)} smart{"s" if len(hubs) else ""} hub found')
        return hubs


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description='usbutils')
    argparser.add_argument("actions", type=str, nargs='*',
                           help="Specify action {on|off}")
    argparser.add_argument("-p", "--port", dest="port", type=int,
                           help="Aggregate other threads into anonymous one")
    argparser.add_argument("-v", "--verbose", dest="verbose", action="store_true",
                           help="increase output verbosity")
    args = argparser.parse_args()

    hubs = USBSmartHub.get_hubs(verbose=args.verbose)

    if not hubs:
        print()
        sys.exit(1)
    for action in args.actions:
        hubs[0].port_power(args.port, True if action == 'on' else False)
    for dev in hubs:
        hubs[0].show_status()
    sys.exit(0)
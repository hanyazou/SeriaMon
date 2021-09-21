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

import usb

class USBUtil:
    # Universal Serial Bus Specification Revision 2.0
    ''' 11.24.2.7.1 PortStatusBits
    Table 11-21. Port Status Field, wPortStatus
    '''
    PORT_STAT_CONNECTION   = (1 << 0)
    PORT_STAT_ENABLE       = (1 << 1)
    PORT_STAT_SUSPEND      = (1 << 2)
    PORT_STAT_OVER_CURRENT = (1 << 3)
    PORT_STAT_RESET        = (1 << 4)
    PORT_STAT_POWER        = (1 << 8)
    PORT_STAT_LOW_SPEED    = (1 << 9)
    PORT_STAT_HIGH_SPEED   = (1 << 10)
    PORT_STAT_TEST         = (1 << 11)
    PORT_STAT_INDICATION   = (1 << 12)

    ''' 11.24.2 Class-specific Requests
    Table 11-17. Hub Class Feature Selectors
    '''
    HUB_FEAT_C_LOCAL_POWER   = 0
    HUB_FEAT_C_OVER_CURRENT  = 1
    PORT_FEAT_CONNECTION     = 0
    PORT_FEAT_ENABLE         = 1
    PORT_FEAT_SUSPEND        = 2
    PORT_FEAT_OVER_CURRENT   = 3
    PORT_FEAT_RESET          = 4
    PORT_FEAT_POWER          = 8
    PORT_FEAT_LOW_SPEED      = 9
    PORT_FEAT_C_CONNECTION   = 16
    PORT_FEAT_C_ENABLE       = 17
    PORT_FEAT_C_SUSPEND      = 18
    PORT_FEAT_C_OVER_CURRENT = 19
    PORT_FEATC_RESET         = 20
    PORT_FEAT_TEST           = 21
    PORT_FEAT_INDICATOR      = 22

    def bitmask(msb, lsb):
        if msb < lsb:
            msb, lsb = lsb, msb
        mask = 0
        for i in range(lsb, msb + 1):
            mask = mask | 1 << i
        return mask

    def bitfield(value, msb, lsb):
        if msb < lsb:
            msb, lsb = lsb, msb
        return (value & USBUtil.bitmask(msb, lsb)) >> lsb

    def portid(dev: usb.Device):
        portid = dev.bus << 24
        for i, port in enumerate(dev.port_numbers):
            portid |= dev.port_numbers[i] << (20 - i * 4)
        return portid

    def get_string(dev: usb.Device, index):
        if string := usb.util.get_string(dev, index):
            string = string.rstrip(' ')
        return string

    def device_name(dev: usb.core.Device):
        s = (f'{dev.idVendor:04x} {dev.idProduct:04x} @ 0x{USBUtil.portid(dev):08x}: '
                f'{USBUtil.get_string(dev, dev.iManufacturer)} '
                f'{USBUtil.get_string(dev, dev.iProduct)}'
                f'{" " + USBUtil.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else ""}')
        return s

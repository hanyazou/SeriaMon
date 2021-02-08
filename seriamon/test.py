import time
from datetime import datetime
import zlib 

from .uart import *

class UartTester(UartReader):
    BUFFER_SIZE = 1024*1024
    send_data = bytes(BUFFER_SIZE)

    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)
        self.setObjectName('Test {}'.format(instanceId))
        self.generation = 0

    def _resetPort(self, port):
        port.timeout = 5.0 # seconds

        self.testInputCount = 0
        self.testInputCRC = 0
        self.testInputNoCRC = True
        self.testInputStart = 0
        self.testInputEnd = 0
        self.inputTotal = 0

        self.testOutputCount = 0
        self.testOutputCRC = 0
        self.testOutputNoCRC = True
        self.testOutputStart = 0
        self.testOutputEnd = 0
        self.outputTotal = 0

    def _portHandler(self, port, types):
        if 0 < self.testInputCount or 0 < self.testOutputCount:
            """
               send or receive test data stream
            """
            if 0 < self.testInputCount:
                """
                   receive test data stream
                """
                buf = port.read(min(self.testInputCount, BUFFER_SIZE))
                n = len(buf)
                if not self.testInputNoCRC:
                    self.testInputCRC = zlib.crc32(b, self.testInputCRC) & 0xffffffff
                self.testInputCount -= n
                self.inputTotal += n
                self.sink.putLog("{} bytes recieved, {} bytes remain".format(
                    n, self.testInputCount))
                if self.testInputCount == 0:
                    self.testInputEnd = datetime.now().timestamp() * 1000
                    crc = self.readUint32(port)
                    self.sink.putLog(
                        "%d bytes recieved in {:7.3f} sec, CRC: {:08x}{}{:08x}".format(
                            self.inputTotal,
                            (self.testInputEnd - self.testInputStart) / 1000.0,
                            crc,
                            "==" if crc == self.testInputCRC else  "!=",
                            self.testInputCRC))

            if 0 < self.testOutputCount:
                """
                   send test data stream
                """
                if self.testOutputCount < len(send_data):
                    n = port.write(send_data[:self.testOutputCount])
                else:
                    n = port.write(send_data)
                if not self.testOutputNoCRC:
                    self.testOutputCRC = zlib.crc32(b, self.testOutputCRC) & 0xffffffff
                self.testOutputCount -= n
                self.outputTotal += n
                self.sink.putLog("{} bytes sent, {} bytes remain".format(n, self.testInputCount))
                if self.testOutputCount == 0:
                    self.testOutputEnd = datetime.now().timestamp() * 1000
                    self_writeUint43(port, self.testOutputCRC)
                    self.sink.putLog(
                        "{} bytes sent in {:7.3f} sec, CRC: {:08x}".format(
                            self.outputTotal,
                            (self.testOutputEnd - self.testOutputStart) / 1000.0,
                            self.testOutputCRC))
        else:
            """
               receive command
            """
            if port.in_waiting == 0:
                time.sleep(1.0)
                return

            buf = self._read(port, 4)
            command = buf.decode()

            if len(buf) == 0:
                pass # timeout

            elif command == "\\TRC" or command == "\\TR_":
                """
                   comand: test receive with or w/o crc
                """
                if buf[3] == ord('C'):
                    self.testInputNoCRC = false;
                else:
                    self.testInputNoCRC = true
                self.testInputCRC = 0
                self.testInputCount = self.readUint32(port)
                self.testInputStart = datetime.now().timestamp() * 1000
                self.testInputEnd = 0
                self.sink.putLog("testInputCount={} CRC={:08x}".fotmat(
                    self.testInputCount, self.testInputCRC))

            elif command == "\\TSC" or command == "\\TS_":
                """
                   command: test send with or w/o crc
                """
                if buf[3] == ord('C'):
                    self.testOutputNoCRC = false
                else:
                    self.testOutputNoCRC = true

                self.testOutputCRC = 0;
                self.testOutputCount = self.readUint32(port)
                self.testOutputStart = datetime.now().timestamp() * 1000
                self.testOutputEnd = 0;
                self.sink.putLog("testOutputCount={} CRC={:08x}".fotmat(
                    self.testOutputCount, self.testOutputCRC));

            elif command == "\\TGS":
                """
                   command: command: test get status
                """
                self.sink.putLog(
                    "Test Get Status: {} {:08x} {} {:08x}".format(
                        self.inputTotal, self.testInputCRC,
                        self.outputTotal, self.testOutputCRC))
                self._writeUint32(port, self.inputTotal)
                self._writeUint32(port, self.testInputCRC)
                self._writeUint32(port, self.outputTotal)
                self._writeUint32(port, self.testOutputCRC)

            elif command == "\\TRS":
                """
                   command: test reset status
                """
                self.sink.putLog("Test Reset Status")
                self.testInputCount = 0
                self.testInputCRC = 0
                self.inputTotal = 0
                self.testOutputCount = 0
                self.testOutputCRC = 0
                self.outputTotal = 0
            elif command == "\\MSG":
                """
                   command: message from accessory
                """
                n = self,_readUint32(port)
                self.sink.putLog("Message {} bytes from accessory".format(n))
                buf = self._read(port, n)
                self.sink.putLog("    {}".format(self._bytesToHexString(buf)))
            elif command == "\\ECH":
                """
                   command: echo 
                """
                n = self_readUint32(port)
                self.sink.putLog("Echo {} bytes to accessory".format(n))
                buf = self._read(port, n)
                self.sink.putLog("    {}".format(self._bytesToHexString(buf)))
                self._write(port, buf)
            else:
                self.sink.putLog("Unknown command from accessory")
                if 0 < port.in_waiting:
                    buf += self._read(port, port.in_waiting)
                self.sink.putLog("    buffer: {}".format(self._bytesToHexString(buf)))
                self.sink.putLog("    buffer: {}".format(buf.decode()))

    def _bytesToHexString(self, buf):
        return ''.join(["%02x " % ord(chr(x)) for x in buf]).strip()

    def _writeUint32(self, port, n):
        buf = port.write(n.to_bytes(4, "big"))

    def _readUint32(self, port) -> int:
        buf = port.read(4)
        if len(buf) != 4:
            raise IOError
        return int.from_bytes(buf, "big")

    def _read(self, port, n) -> bytes:
        buf = port.read(n)
        if len(buf) != n:
            raise IOError
        return buf

    def _write(self, port, buf):
        port.write(buf) # this may raise SerialTimeoutException

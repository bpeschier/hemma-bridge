import asyncio
import logging
import struct
from asyncio.futures import CancelledError

import serial
import serial.tools.list_ports

import flynn
import flynn.decoder

logger = logging.getLogger(__name__)


class Serial:
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()

    serial = None
    loop = None

    def __init__(self, serial_device, loop):
        self.serial = serial_device
        self.loop = loop

        loop.add_reader(serial_device, self.serial_reader)
        loop.create_task(self.serial_writer())
        logger.debug("Started reader and writer tasks")

    def serial_reader(self):
        try:
            data = flynn.load(self.serial)
            logger.debug("< {}".format(data))

            self.loop.create_task(self.incoming.put([data, self.outgoing]))
        except flynn.decoder.InvalidCborError:
            logger.error("Invalid CBOR received")
        except serial.SerialException:
            logger.error("Error on serial device, shutting down")
            self.close()
            self.loop.stop()

    async def serial_writer(self):
        try:
            while True:
                cmd = await self.outgoing.get()
                data = flynn.dumps(cmd)
                header = struct.pack('<H', len(data))
                self.loop.call_soon(self.serial.write, header + data)

                logger.debug("> {}".format(cmd))
        except CancelledError:
            pass

    def close(self):
        self.serial.close()
        logger.debug("Closing serial")


def get_default_port():
    return serial.tools.list_ports.comports()[-1][0]

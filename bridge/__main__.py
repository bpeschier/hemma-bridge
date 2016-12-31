import argparse
import asyncio
import socket
import logging

import serial
import sys

import zeroconf

from . import Bridge
from .serial import Serial, get_default_port
from .websockets import Websockets, LoggingHandler
from .zeroconf import HemmaService

parser = argparse.ArgumentParser(
    description='Create bridge between websockets and serial port(s)'
)

parser.add_argument(
    '--announce',
    '-z',
    dest='announce',
    action='store_true',
    default=True,
)

parser.add_argument(
    '--debug',
    '-d',
    dest='debug',
    action='store_true',
    default=False,
)

parser.add_argument(
    '--websocket-debug',
    '-w',
    dest='websocket_debug',
    action='store_true',
    default=False,
)

parser.add_argument(
    '-p',
    '--port',
    dest='port',
    type=int,
    action='store',
    default=8765,
)

parser.add_argument(
    '--serial-device',
    '-s',
    dest='serial',
    type=str,
    action='store',
    default=get_default_port(),
)

parser.add_argument(
    '--name',
    '-n',
    dest='name',
    type=str,
    action='store',
    default=socket.gethostname().split('.local')[0],
)

parser.add_argument(
    '--domain',
    dest='domain',
    type=str,
    action='store',
    default='local.',
)

args = parser.parse_args()

loop = asyncio.get_event_loop()

log_level = logging.DEBUG if args.debug else logging.INFO
logger = logging.getLogger()
logger.setLevel(log_level)

# create logging handler and set level to debug argument
if args.websocket_debug:
    ch = LoggingHandler('0.0.0.0', args.port + 1, loop)
    # but we cannot allow websockets to debug, because that would endlessly loop
    from .websockets import logger as websocket_logger
    websocket_logger.setLevel(logging.ERROR)
else:
    ch = logging.StreamHandler(sys.stdout)

ch.setLevel(log_level)

# create formatter
formatter = logging.Formatter('{name: <25} {levelname: <8} | {message}', style='{')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

loop.set_debug(args.debug)

ws = Websockets('0.0.0.0', args.port, loop)
se = Serial(serial.Serial(args.serial, 115200, timeout=5), loop)

bridge = Bridge(loop, ws, se)

if args.announce:
    zc = zeroconf.Zeroconf()
    service = HemmaService(args.name, args.port, args.domain)
    zc.register_service(service)
else:
    zc = None
    service = None

try:
    logger.info('Starting service {} on {}'.format(args.name, args.serial))
    loop.run_forever()
finally:

    # We need to clean up a bit
    pending = asyncio.Task.all_tasks()
    for t in pending:
        t.cancel()

    loop.run_until_complete(asyncio.gather(*pending))

    se.close()
    ws.close()

    if args.announce:
        zc.unregister_service(service)
        zc.close()

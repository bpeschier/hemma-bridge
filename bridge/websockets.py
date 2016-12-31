import asyncio
import flynn
import logging
from asyncio.futures import CancelledError

import websockets

logger = logging.getLogger(__name__)


class Websockets:
    connections = set()
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    loop = None

    def __init__(self, address, port, loop):
        self.address = address
        self.port = port
        self.loop = loop

        loop.create_task(self.monitor_outgoing())
        logger.debug("Started outgoing queue")

        start_server = self.serve()
        loop.run_until_complete(start_server)
        logger.debug("Started Websocket server")

    def serve(self):
        return websockets.serve(self.handler, self.address, self.port)

    async def monitor_outgoing(self):
        try:
            while True:
                data = await self.outgoing.get()
                for outgoing in self.connections:
                    await outgoing.put(data)
        except CancelledError:
            pass

    async def handler(self, socket, path):
        write_queue = asyncio.Queue()
        self.connections.add(write_queue)

        producer_task = None
        listener_task = None
        try:
            while True:

                listener_task = self.loop.create_task(socket.recv())
                producer_task = self.loop.create_task(write_queue.get())
                done, pending = await asyncio.wait(
                    [listener_task, producer_task],
                    return_when=asyncio.FIRST_COMPLETED)

                if listener_task in done:
                    message = listener_task.result()
                    logger.debug("< {}".format(message))
                    await self.incoming.put([flynn.loads(message), write_queue])
                else:
                    listener_task.cancel()

                if producer_task in done:
                    message = producer_task.result()
                    logger.debug("> {}".format(message))
                    await socket.send(flynn.dumps(message))
                else:
                    producer_task.cancel()

        except websockets.ConnectionClosed:
            pass
        finally:
            if producer_task:
                producer_task.cancel()
            if listener_task:
                listener_task.cancel()
            self.connections.remove(write_queue)

    def close(self):
        pass


class LoggingHandler(logging.Handler):
    connections = set()

    def __init__(self, address, port, loop):
        super().__init__()
        self.address = address
        self.port = port
        self.loop = loop

        start_server = self.serve()
        loop.run_until_complete(start_server)
        logger.debug("Started Websocket debug logger")

    def serve(self):
        return websockets.serve(self.handler, self.address, self.port)

    async def handler(self, socket, path):
        self.connections.add(socket)

        try:
            while True:
                await socket.recv()
        except websockets.ConnectionClosed:
            pass
        finally:
            self.connections.remove(socket)

    def emit(self, record):
        try:
            if not record.name.startswith('websockets'):
                msg = self.format(record)

                for socket in self.connections:
                    self.loop.create_task(socket.send(msg))

        except Exception:
            self.handleError(record)

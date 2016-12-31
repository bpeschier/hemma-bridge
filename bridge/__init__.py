import asyncio
import logging
from asyncio.futures import CancelledError

logger = logging.getLogger(__name__)


class Bridge:
    results = None
    events = None
    sources = None
    loop = None

    current_id = 0
    current_id_lock = asyncio.Lock()

    def __init__(self, event_loop, *sources):
        self.sources = sources
        self.events = {}
        self.results = {}
        self.loop = event_loop

        for source in sources:
            self.loop.create_task(self.monitor_source(
                source,
                [s for s in sources if s is not source]
            ))
        logger.debug("Started monitoring tasks for sources")

    async def monitor_source(self, source, sinks):
        try:
            while True:
                data, reply = await source.incoming.get()
                if 'name' in data:  # request
                    logger.info('Received request')
                    if 'id' not in data:
                        name = data.get('name')
                        logger.info('Missing id for request {name}'.format(name=name))
                        await reply.put({'error': 'Missing id', 'name': name})
                    else:
                        await self.send_command(data, reply, sinks)
                elif 'id' in data:  # reply
                    logger.info('Received reply')
                    self.set_result(data['id'], data)
                elif 'data' in data:  # broadcast
                    logger.info('Received broadcast')
                    broadcast_data = data.get('data')
                    if broadcast_data:
                        data['name'] = broadcast_data[0]
                        data['time'] = broadcast_data[1]
                        data['data'] = broadcast_data[2]
                    for s in sinks:
                        await s.outgoing.put(data)
        except CancelledError:
            pass

    async def get_response(self, cmd_id):
        event = self.events.setdefault(cmd_id, asyncio.Event())
        try:
            await asyncio.wait_for(event.wait(), 5.0)
        finally:
            event.clear()
            del self.events[cmd_id]
            return self.results.pop(cmd_id, None)

    async def get_command_id(self):
        async with self.current_id_lock:
            self.current_id = (self.current_id + 1) % (1024 * 1024)
            cmd_id = self.current_id
        return cmd_id

    async def send_command(self, data, reply, sinks):
        internal_cmd_id = await self.get_command_id()
        cmd_id = data['id']
        data['id'] = internal_cmd_id  # overwrite so we guarantee uniqueness (with 1 bridge...)
        data['args'] = data.get('args', {})

        async def send_request(sink):
            await sink.outgoing.put(data)
            response = await self.get_response(internal_cmd_id)
            if response:
                logger.info('Forwarded response for request {id}'.format(id=cmd_id))
                response['data']['id'] = cmd_id  # reset our original id
                await reply.put(response['data'])
            else:
                logger.info('Timeout for request {id}'.format(id=cmd_id))
                await reply.put({'error': 'Timeout'})

        logger.info(
            'Forwarding request {id} to {address}'.format(
                id=cmd_id, address=data['address']))
        await asyncio.wait([self.loop.create_task(send_request(s)) for s in sinks])

    def set_result(self, command_id, data):
        self.results[command_id] = {
            'id': command_id,
            'data': data,
        }
        event = self.events.setdefault(command_id, asyncio.Event())
        event.set()
        logger.info('Received response to request {id}'.format(id=command_id))

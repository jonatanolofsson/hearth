"""ZigBee server."""
import asyncio
import json
import logging
import websockets
import aiohttp
from asyncinit import asyncinit
from .device import Device as DeviceBase

LOGGER = logging.getLogger(__name__)
SERVER = None


class Device(DeviceBase):
    """Zigbee device."""
    async def __init__(self, id_, uniqueid):
        await super().__init__(id_)
        self.uniqueid = uniqueid
        self.server = await server()
        device = self.server.get_device(self.uniqueid)
        self.node_id = device['id']
        self.state = device['state']
        self.rest_endpoint = device['r']
        self.server.add_listener(self.uniqueid, self.ws_callback)

    async def ws_callback(self, message):
        """Message received from websocket."""
        self.update_state(message['state'])

    async def set_state(self, new_state):
        """Set new state."""
        await (await server()).put(
            f"{self.rest_endpoint}/{self.node_id}/state",
            new_state)
        new_state = {key: value for key, value in new_state.items()
                     if key in self.state}
        await super().set_state(new_state)


@asyncinit
class ServerConnection:
    """Deconz server."""

    async def __init__(self, url, api_key, rest_port=80):
        self.url = url
        self.api_key = api_key
        self.rest_uri = f"http://{url}:{rest_port}/api/{api_key}"
        self.session = None
        self.devices = {}
        self.listeners = {}
        self.session = await aiohttp.ClientSession().__aenter__()
        await self.load_config()
        self.ws_uri = f"ws://{self.url}:{self.config['websocketport']}"
        await self.load_devices()
        asyncio.ensure_future(self.ws_reader())

    async def get(self, endpoint):
        """HTTP GET."""
        async with self.session.get(f"{self.rest_uri}/{endpoint}",
                                    timeout=20) as response:
            return await response.json()

    async def post(self, endpoint, data):
        """HTTP POST."""
        async with self.session.post(f"{self.rest_uri}/{endpoint}",
                                     json=data, timeout=20) as response:
            return await response.json()

    async def put(self, endpoint, data):
        """HTTP PUT."""
        async with self.session.put(f"{self.rest_uri}/{endpoint}",
                                    json=data, timeout=20) as response:
            return await response.json()

    async def ws_reader(self):
        """Websocket reader."""
        while True:
            LOGGER.debug("Connecting to websocket: %s", self.ws_uri)
            async with websockets.connect(self.ws_uri) as socket:
                while True:
                    try:
                        msg = json.loads(await socket.recv())
                        LOGGER.debug("Got ws message: %s", msg)
                        rest_endpoint = msg['r']
                        node_id = msg['id']
                        callbacks = self.listeners \
                            .get(rest_endpoint, {}) \
                            .get(node_id, [])
                        for callback in callbacks:
                            asyncio.ensure_future(callback(msg))
                    except json.JSONDecodeError as error:
                        LOGGER.warning("Invalid json format: %s", error)
                    except AttributeError as error:
                        LOGGER.warning("Invalid message: %s", error)
            await asyncio.sleep(1)

    def add_listener(self, uniqueid, callback):
        """Add callback on message from device."""
        device = self.get_device(uniqueid)
        if device['r'] not in self.listeners:
            self.listeners[device['r']] = {}
        if device['id'] not in self.listeners[device['r']]:
            self.listeners[device['r']][device['id']] = []
        self.listeners[device['r']][device['id']].append(callback)

    async def load_config(self):
        """Load server configuration."""
        self.config = await self.get('config')

    async def load_devices(self):
        """Load all devices."""
        self.devices = {}
        for source in ['lights', 'sensors']:
            devices = await self.get(source)
            for node_id, device in devices.items():
                device.update({'id': node_id, 'r': source})
                self.devices[device['uniqueid']] = device

    def get_device(self, uniqueid):
        """Get device."""
        return self.devices[uniqueid]


async def server():
    """Get server object."""
    while SERVER is None:
        await asyncio.sleep(0.2)
    return SERVER


def connect(*args, **kwargs):
    """Start ZigBee server."""
    async def astart(*args, **kwargs):
        """Async start server."""
        global SERVER  # pylint: disable=global-statement
        SERVER = await ServerConnection(*args, **kwargs)
    asyncio.ensure_future(astart(*args, **kwargs))

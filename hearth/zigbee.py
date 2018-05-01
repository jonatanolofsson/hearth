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
        self.node_id = None
        self.rest_endpoint = None
        asyncio.ensure_future(self.init())

    async def init(self):
        """Init 2."""
        device = False
        sleeptime = 1
        while not device:
            device = self.server.get_device(self.uniqueid)
            if not device:
                await asyncio.sleep(sleeptime)
                if sleeptime < 30:
                    sleeptime += 1
        self.node_id = device['id']
        state = device['state'].copy()
        if 'config' in device:
            state.update(device['config'])
        await super().init_state(state)
        self.rest_endpoint = device['r']
        LOGGER.debug("Finished init: %s", self.id)
        self.server.add_listener(self.uniqueid, self.ws_callback)

    async def ws_callback(self, message):
        """Message received from websocket."""
        if 'state' in message:
            reachable = message['state']['reachable'] \
                if 'reachable' in message['state'] else False
            await self.update_state(message['state'], reachable)
        if 'config' in message:
            reachable = message['config']['reachable'] \
                if 'reachable' in message['config'] else False
            await self.update_state(message['config'], reachable)

    async def set_state(self, upd_state):
        """Set new state."""
        LOGGER.debug("Setting new state: %s", upd_state)
        if self.node_id is None:
            return
        self.expect_update(5)
        res = await (await server()).put(
            f"{self.rest_endpoint}/{self.node_id}/state",
            upd_state)
        successes = {name.rpartition('/')[2]: state
                     for line in res
                     for name, state in line.get("success", {}).items()}
        await super().update_state(successes)

    def alerts(self):
        """List of active alerts."""
        active_alerts = super().alerts()
        try:
            if self.state['battery'] < 10:
                active_alerts.append(
                    {"icon": "battery_alert",
                     "label": f"Low battery: {self.state['battery']} %",
                     "color": "#f44336"})
        except:
            pass
        return active_alerts


@asyncinit
class ServerConnection:
    """Deconz server."""

    async def __init__(self, url, api_key, rest_port=80):
        self.url = url
        self.api_key = api_key
        self.rest_uri = f"http://{url}:{rest_port}/api/{api_key}"
        self.devices = {}
        self._listeners = {}
        self.session = await aiohttp.ClientSession().__aenter__()
        await self.load_config()
        asyncio.ensure_future(self.load_devices())
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
        ws_uri = f"ws://{self.url}:{self.config['websocketport']}"
        while True:
            try:
                LOGGER.debug("Connecting to websocket: %s", ws_uri)
                async with websockets.connect(ws_uri) as socket:
                    while True:
                        try:
                            msg = json.loads(await socket.recv())
                            rest_endpoint = msg['r']
                            node_id = msg['id']
                            callbacks = self._listeners \
                                .get(rest_endpoint, {}) \
                                .get(node_id, [])
                            for callback in callbacks:
                                asyncio.ensure_future(callback(msg))
                        except json.JSONDecodeError as error:
                            LOGGER.warning("Invalid json format: %s", error)
                        except AttributeError as error:
                            LOGGER.warning("Invalid message: %s", error)
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except:
                pass

    def add_listener(self, uniqueid, callback):
        """Add callback on message from device."""
        device = self.get_device(uniqueid)
        if device['r'] not in self._listeners:
            self._listeners[device['r']] = {}
        if device['id'] not in self._listeners[device['r']]:
            self._listeners[device['r']][device['id']] = []
        self._listeners[device['r']][device['id']].append(callback)

    async def load_config(self):
        """Load server configuration."""
        self.config = await self.get('config')

    async def load_devices(self):
        """Load all devices."""
        self.devices = {}
        while True:
            for source in ['lights', 'sensors']:
                devices = await self.get(source)
                for node_id, device in devices.items():
                    if 'uniqueid' in device:
                        if device['uniqueid'] not in self.devices:
                            device.update({'id': node_id, 'r': source})
                            self.devices[device['uniqueid']] = device
            await asyncio.sleep(30)

    def get_device(self, uniqueid):
        """Get device."""
        if uniqueid not in self.devices:
            return False
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

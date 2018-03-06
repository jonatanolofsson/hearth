"""Device base class."""
import asyncio
import inspect
import json
import logging
from asyncinit import asyncinit
from . import hearth
from . import web

LOGGER = logging.getLogger(__name__)


@asyncinit
class Device:
    """Device base class."""

    async def __init__(self, id_):
        self.id = id_  # pylint: disable=invalid-name
        self._refresh_fut = None
        self.state = {}
        self._eventlisteners = {}

    def webmessage(self, data=None):
        """Create a websocket message."""
        data = data or {}
        data.update({"id": self.id})
        return json.dumps(data)

    async def update_state(self, new_state, new_value=None):
        """State."""
        if isinstance(new_state, str):
            new_state = {new_state: new_value}
        self.state.update(new_state)
        self.refresh()

    def listen(self, eventname, callback=None):
        """Register event listener."""
        if callback is None and isinstance(eventname, dict):
            for ename, ecb in eventname.items():
                self.listen(ename, ecb)
        elif callback is not None:
            if eventname not in self._eventlisteners:
                self._eventlisteners[eventname] = []
            self._eventlisteners[eventname].append(callback)

    def event(self, eventname, *args, **kwargs):
        """Announce event."""
        for callback in self._eventlisteners.get(eventname, []):
            asyncio.ensure_future(callback(*args, **kwargs))

    async def set_state(self, upd_state):
        """Set new state."""
        self.state.update(upd_state)

    async def set_single_state(self, state, value):
        """Set single state."""
        await self.set_state({state: value})

    def serialize(self):  # pylint: disable=no-self-use
        """React."""
        return {'id': self.id, 'state': self.state, 'ui': self.ui()}

    def ui(self):  # pylint: disable=no-self-use, invalid-name
        """UI."""
        return False

    async def webhandler(self, data, _):
        """Default webhandler."""
        if 'm' in data and not data['m'].startswith('_'):
            fun = getattr(self, data['m'], None)
            if callable(fun):
                args = data.get('args', [])
                LOGGER.info("Executing: %s, %s", data, fun)
                res = fun(*args)
                if inspect.isawaitable(res):
                    await res

    def expect_refresh(self, timeout):
        """Ensure refresh is called within a given timeout."""
        async def waiter():
            """Waiter."""
            try:
                await asyncio.sleep(timeout)
                self.refresh()
            except asyncio.CancelledError:
                pass

        if self._refresh_fut is not None:
            self._refresh_fut.cancel()
        self._refresh_fut = asyncio.ensure_future(waiter())

    def refresh(self):
        """Announce state changes."""
        if self._refresh_fut is not None:
            self._refresh_fut.cancel()
            self._refresh_fut = None

        web.broadcast(self.webmessage(self.serialize()))


class HearthDevice(Device):
    """Device to handle the base functionality of hearth"""

    async def __init__(self):
        await super().__init__(0)

    async def webhandler(self, data, socket):
        """Handle incoming message."""
        if data['m'] == 'sync_devices':
            await socket.send(self.webmessage(
                {"m": "devices",
                 "devices": [d.serialize()
                             for d in hearth.DEVICES.values()]}))


async def setup():
    """Setup."""
    hearth.add_devices(await HearthDevice())

asyncio.ensure_future(setup())

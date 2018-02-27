"""Device base class."""
import asyncio
import inspect
import json
import logging
from . import hearth
from . import web

LOGGER = logging.getLogger(__name__)

class Device:
    """Device base class."""

    def __init__(self, id_):
        self.id = id_  # pylint: disable=invalid-name
        self._refresh_fut = None
        self.state = {}

    def webmessage(self, data=None):
        """Create a websocket message."""
        data = data or {}
        data.update({"id": self.id})
        return json.dumps(data)

    def update_state(self, new_state, new_value=None):
        """State."""
        if isinstance(new_state, str):
            new_state = {new_state: new_value}
        self.state.update(new_state)
        self.refresh()

    async def state_set(self, new_state, old_state):
        """New state has been set."""
        pass

    async def set_state(self, new_state, new_value):
        """Set new state."""
        if isinstance(new_state, str):
            new_state = {new_state: new_value}
        old_state = self.state.copy()
        self.state.update(new_state)
        await self.state_set(self.state, old_state)

    def serialize(self):  # pylint: disable=no-self-use
        """React."""
        return {'id': self.id, 'state': self.state, 'ui': self.ui()}

    def ui(self):  # pylint: disable=no-self-use, invalid-name
        """UI."""
        return {}

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
            await asyncio.sleep(timeout)
            self.refresh()

        self._refresh_fut = asyncio.ensure_future(waiter())

    def refresh(self):
        """Announce state changes."""
        if self._refresh_fut is not None:
            self._refresh_fut.cancel()

        web.broadcast(self.webmessage(self.serialize()))


class HearthDevice(Device):
    """Device to handle the base functionality of hearth"""

    def __init__(self):
        Device.__init__(self, 0)

    async def webhandler(self, data, socket):
        """Handle incoming message."""
        if data['m'] == 'sync_devices':
            await socket.send(self.webmessage(
                {"m": "devices",
                 "devices": [d.serialize()
                             for d in hearth.DEVICES.values()]}))


hearth.add_devices(HearthDevice())

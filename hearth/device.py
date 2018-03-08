"""Device base class."""
import os
import asyncio
from datetime import datetime
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
        self.history = []
        await self.load_history()

    def history_filename(self):
        """Get path to device state history."""
        filename = "".join(x for x in str(self.id) if x.isalnum())
        return os.path.abspath(".cache/" + filename)

    async def load_history(self):
        """Load history from file."""
        self.history = []
        hfile = self.history_filename()
        if os.path.exists(hfile):
            with open(hfile, 'r') as ifile:
                self.history = json.load(ifile)

    async def save_history(self):
        """Save history to file."""
        hfile = self.history_filename()
        hdir = os.path.dirname(hfile)
        if not os.path.exists(hdir):
            os.makedirs(hdir)
        with open(hfile, 'w') as ofile:
            json.dump(self.history, ofile)

    async def shutdown(self):
        """Shutdown procedure."""
        await self.save_history()

    def webmessage(self, data=None):
        """Create a websocket message."""
        data = data or {}
        data.update({"id": self.id})
        return json.dumps(data)

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
        await self.update_state(upd_state)

    async def update_state(self, new_state, new_value=None):
        """State."""
        if isinstance(new_state, str):
            new_state = {new_state: new_value}
        updated_state = self.state.copy()
        updated_state.update(new_state)
        LOGGER.debug("%s: Updated state: %s", self.id, updated_state)
        if updated_state != self.state:
            self.state = updated_state
            self.history.append([str(datetime.now()), self.state])
            self.refresh()

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

"""Device base class."""
import os
import asyncio
from datetime import datetime
import inspect
import dateutil
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
        self._update_fut = None
        self.state = {'reachable': False,
                      'last_seen': ''}
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
        if len(self.history) > 0:
            self.state = self.history[-1][1]

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
            LOGGER.debug("Event: %s. Scheduling callback: %s", eventname, callback)
            nargs = len(inspect.signature(callback).parameters) - len(kwargs)
            res = callback(*args[:nargs], **kwargs)
            if inspect.isawaitable(res):
                asyncio.ensure_future(res)

    async def set_state(self, upd_state):
        """Set new state. This may be overridden to command device to set the
        state."""
        pass

    async def init_state(self, upd_state):
        """Set state initial value. Distinguised from set_state through
        overloading."""
        await self.update_state(upd_state, len(self.history) == 0)

    def expect_update(self, timeout):
        """Ensure update is called within a given timeout."""
        async def waiter(fut):
            """Waiter."""
            try:
                await asyncio.wait_for(fut, timeout)
            except asyncio.TimeoutError:
                LOGGER.debug("Did not update: %s", self.id)
                await self.update_state({"reachable": False}, False)
            finally:
                if self._update_fut is not None:
                    self._update_fut.cancel()
                    self._update_fut = None

        if self._update_fut is None:
            self._update_fut = asyncio.Future()
            asyncio.ensure_future(waiter(self._update_fut))
        LOGGER.debug("Expecting update: %s", self.id)

    async def update_state(self, upd_state, set_seen=True):
        """Update the state. This is mainly called when the device informs of a
        new state, i.e. it should not be commanded to set the state."""
        LOGGER.debug("Update: %s", self.id)
        if self._update_fut is not None:
            self._update_fut.set_result(True)
            self._update_fut = None

        if set_seen:
            upd_state.update({'reachable': True})
            upd_state.update({'last_seen': str(datetime.now())})
        self.state.update(upd_state)
        self.history.append([str(datetime.now()), self.state])
        self.refresh()
        self.event('statechange', self)
        for key in upd_state:
            self.event(f'statechange:{key}', self, key, self.state[key])
            self.event(f'statechange:{key}:{self.state[key]}',
                       self, key, self.state[key])
        LOGGER.debug("%s: Updated state: %s", self.id, upd_state)

    async def set_single_state(self, state, value):
        """Set single state."""
        await self.set_state({state: value})

    def alerts(self):
        """List of current alerts."""
        active_alerts = []
        if not self.state['reachable']:
            active_alerts.append({"icon": "error",
                                  "label": "Device unreachable",
                                  "color": "#f44336"})
            LOGGER.debug("Unreachable device: %s", self.id)
        return active_alerts

    def serialize(self):  # pylint: disable=no-self-use
        """React."""
        state = self.state.copy()
        ui_ = self.ui()
        if ui_ and 'state' in ui_:
            state.update(ui_['state'])
        state.update({'alerts': self.alerts()})
        return {'id': self.id, 'state': state, 'ui': ui_}

    def ui(self):  # pylint: disable=no-self-use, invalid-name
        """UI."""
        return False

    def events_ui(self):
        """Return UI for triggering events."""
        events = [event
                  for event, listeners in self._eventlisteners.items()
                  if len(listeners) > 0 and len(inspect.signature(listeners[0]).parameters) == 0]
        if not events:
            return []
        return [
            {"class": "SelectField",
             "props": {"floatingLabelText": "Event"},
             "action": "event",
             "items": events}]

    async def webhandler(self, data, _):
        """Default webhandler."""
        if 'm' in data and not data['m'].startswith('_'):
            LOGGER.info("Got webmessage: %s", data)
            fun = getattr(self, data['m'], None)
            if callable(fun):
                args = data.get('args', [])
                LOGGER.info("Executing: %s, %s", data, fun)
                res = fun(*args)
                if inspect.isawaitable(res):
                    await res

    def refresh(self):
        """Announce state changes."""
        web.broadcast(self.webmessage(self.serialize()))

    def __getitem__(self, key):
        """Map [] to state."""
        return self.state[key]


class HearthDevice(Device):
    """Device to handle the base functionality of hearth"""

    async def __init__(self):
        await super().__init__(0)
        await super().update_state({})

    async def webhandler(self, data, socket):
        """Handle incoming message."""
        if data['m'] == 'sync_devices':
            await socket.send(self.webmessage(
                {"m": "devices",
                 "devices": [d.serialize()
                             for d in hearth.DEVICES.values()]}))
        else:
            await super().webhandler(data, socket)

    def ui(self):
        """UI."""
        return {"ui": self.events_ui()}


async def setup():
    """Setup."""
    hearth.add_devices(await HearthDevice())

asyncio.ensure_future(setup())

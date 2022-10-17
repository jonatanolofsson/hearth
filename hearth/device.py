"""Device base class."""
import os
import asyncio
from copy import deepcopy
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
        try:
            if os.path.exists(hfile):
                with open(hfile, 'r') as ifile:
                    self.history = json.load(ifile)
            if self.history and isinstance(self.history, list):
                self.state = self.history[-1][1]
        except Exception as e:  # pylint: disable=broad-except, invalid-name
            LOGGER.warning("Could not load history: %s", self.id)
            LOGGER.error(e)

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
            nargs = len(inspect.signature(callback).parameters) - len(kwargs)
            res = callback(*args[:nargs], **kwargs)
            if inspect.isawaitable(res):
                asyncio.ensure_future(res)

    async def set_state(self, upd_state):
        """Set new state. This may be overridden to command device to set the
        state."""
        pass

    async def set_single_state(self, state, value):
        """Set single state."""
        await self.set_state({state: value})

    async def init_state(self, upd_state, set_seen=False):
        """Set state initial value. Distinguised from set_state through
        overloading."""
        if set_seen:
            upd_state.update({'reachable': True})
            upd_state.update({'last_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

        upd_state = {key: value for key, value in upd_state.items() if key not in self.state}

        if upd_state:
            self.state.update(upd_state)
            self.history.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), deepcopy(self.state)])

    async def update_state(self, upd_state, set_seen=True):
        """Update the state. This is mainly called when the device informs of a
        new state, i.e. it should not be commanded to set the state."""
        if self._update_fut is not None:
            self._update_fut.set_result(True)
            self._update_fut = None

        actually_updated = {
            state: value
            for state, value in upd_state.items()
            if state not in self.state or self.state[state] != value}

        if set_seen:
            upd_state.update({'reachable': True})
            upd_state.update({'last_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        old_state = deepcopy(self.state)
        self.state.update(upd_state)
        self.history.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), deepcopy(self.state)])
        self.refresh_ui()
        self.event('statechange', self)
        for key in actually_updated:
            self.event(f'statechange:{key}', self, key, self.state[key], old_state.get(key, None))
            self.event(f'statechange:{key}:{self.state[key]}',
                       self, key, self.state[key], old_state.get(key, None))
        for key in upd_state:
            self.event(f'stateupdate:{key}', self, key, self.state[key], old_state.get(key, None))
            self.event(f'stateupdate:{key}:{self.state[key]}',
                       self, key, self.state[key], old_state.get(key, None))

    def expect_update(self, timeout):
        """Ensure update is called within a given timeout."""
        async def waiter(fut):
            """Waiter."""
            try:
                await asyncio.wait_for(fut, timeout)
            except asyncio.TimeoutError:
                LOGGER.debug("Did not update: %s", self.id)
                self._update_fut = None
                await self.update_state({"reachable": False}, False)
            finally:
                if self._update_fut is not None:
                    self._update_fut.cancel()
                    self._update_fut = None

        if self._update_fut is None:
            self._update_fut = asyncio.Future()
            asyncio.ensure_future(waiter(self._update_fut))

    def alerts(self):
        """List of current alerts."""
        active_alerts = []
        if not self.state['reachable']:
            active_alerts.append({"icon": "error",
                                  "label": "Device unreachable",
                                  "color": "error"})
            LOGGER.debug("Unreachable device: %s", self.id)
        return active_alerts

    def serialize(self):  # pylint: disable=no-self-use
        """React."""
        state = self.state.copy()
        ui_ = self.ui()
        if ui_ and 'state' in ui_:  # pylint: disable=unsupported-membership-test
            state.update(ui_['state'])  # pylint: disable=unsubscriptable-object
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
            {"class": "Select",
             "props": {"label": "Event"},
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

    def refresh_ui(self):
        """Announce state changes."""
        LOGGER.info("Refreshing UI: %s", self.id)
        web.broadcast(self.webmessage(self.serialize()))
        self.event('refresh_ui')

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

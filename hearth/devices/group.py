"""Group."""
import asyncio
import functools
import logging
import hearth
from hearth import Device, D

__all__ = ['Group']

LOGGER = logging.getLogger(__name__)


class Group(Device):
    """Group of devices, with same properties as the first."""

    async def __init__(self, id_, *devices):
        await super().__init__(id_)
        devices[0]._refresh_ui_ = devices[0].refresh_ui
        devices[0].refresh_ui = self.refresh_ui
        self.devices = devices

        public_methods = set(method_name for d in devices for method_name in dir(d) if callable(getattr(d, method_name) and not method_name.startswith('_')))
        for method in public_methods:
            setattr(self, method, getattr(devices[0], method).__func__)

        hearth.add_devices(*devices)

    def refresh_ui(self):
        """Refresh overload."""
        self.devices[0]._refresh_ui_()
        super().refresh_ui()

    async def broadcast(self, fnname, *args, **kwargs):
        """Broadcast function to all members of group."""
        LOGGER.debug("Broadcasting function: %s", fnname)
        await asyncio.gather(*[
            getattr(obj, fnname)(*args, **kwargs)
            for obj in self.devices
        ])

    def __getattribute__(self, attr):
        if attr in ['state', 'ui']:
            return getattr(self.devices[0], attr)
        elif attr in ['set_state', 'set_single_state']:
            return functools.partial(self.broadcast, attr)
        return object.__getattribute__(self, attr)

    def __getattr__(self, attr):
        if not hasattr(self.devices[0], attr):
            raise AttributeError(f"No such attribute: {attr}")
        return functools.partial(self.broadcast, attr)

"""Group."""
import asyncio
import inspect
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
        devices[0].listen('refresh_ui', self.refresh_ui)
        self.devices = devices

        hearth.add_devices(*devices)

    async def broadcast(self, fnname, *args, **kwargs):
        """Broadcast function to all members of group."""
        LOGGER.debug("Broadcasting function: %s", fnname)
        await asyncio.gather(*(x for x in [
            getattr(obj, fnname)(*args, **kwargs)
            for obj in self.devices
            if hasattr(obj, fnname)
        ] if inspect.isawaitable(x)))

    def __getattribute__(self, attr):
        if attr in ['state', 'ui']:
            return getattr(self.devices[0], attr)
        elif attr in ['set_state', 'set_single_state']:
            return functools.partial(self.broadcast, attr)
        return object.__getattribute__(self, attr)

    def __getattr__(self, attr):
        return functools.partial(self.broadcast, attr)

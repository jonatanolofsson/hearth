"""Chromecast device class."""
import pychromecast
from hearth import Device

DEVICES = {}

__all__ = ['Chromecast']


class Chromecast(Device):
    """Chromecast device."""

    async def __init__(self, id_, ip):
        """Init."""
        await super().__init__(id_)
        await self.init_state({}, True)
        self.ip = ip
        self.device = pychromecast.Chromecast(self.ip, blocking=False)

    @property
    def is_idle(self):
        """Return true/false if the device is connected to an app."""
        return self.device.app_id in (None, 'E8C28D3C')

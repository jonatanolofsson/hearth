"""Chromecast device class."""
import asyncio
import pychromecast
from hearth import Device

DEVICES = {}

__all__ = ['Chromecast']


def load_devices():
    """Load all chromecasts in the network."""

    async def _load_devices():
        """Load all chromecasts in the network."""
        global DEVICES
        loop = asyncio.get_event_loop()
        devs = await loop.run_in_executor(None, pychromecast.get_chromecasts)

        DEVICES = {str(dev.uuid): dev for dev in devs}
        load_devices.active = False

    if load_devices.active:
        return
    load_devices.active = True
    asyncio.ensure_future(_load_devices())


load_devices.active = False
load_devices()


def get_device(uuid):
    """Get device, or None."""
    dev = DEVICES.get(uuid, None)
    if dev is None:
        load_devices()
    return dev


class Chromecast(Device):
    """Chromecast device."""

    async def __init__(self, id_, uuid):
        """Init."""
        await super().__init__(id_)
        self.uuid = uuid
        await super().init_state({"app_id": "", "display_name": ""})

    @property
    def is_idle(self):
        """Return true/false if the device is connected to an app."""
        device = get_device(self.uuid)
        if not device:
            return True
        return device.app_id in (None, 'E8C28D3C')

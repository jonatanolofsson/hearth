"""Room device classes."""
import asyncio
import logging
import hearth
from hearth import Device

__all__ = ['Room']

LOGGER = logging.getLogger(__name__)


class Room(Device):
    """Room."""

    async def __init__(self, id_, *devices):
        """Init."""
        await super().__init__(id_)
        self.devices = {device.id: device for device in devices}
        hearth.add_devices(*devices)
        await super().update_state({})

    async def off(self):
        """Shut everything down."""
        LOGGER.info("Shutting down %s", self.id)
        asyncio.gather(*[d.off() for d in self.devices.values()
                         if hasattr(d, 'off')])

    async def on(self):
        """Shut everything down."""
        LOGGER.info("Starting up %s", self.id)
        asyncio.gather(*[d.on() for d in self.devices.values()
                         if hasattr(d, 'on')])

    def ui(self):
        """UI."""
        return {"rightIcon": "all_out", "rightAction": "off",
                "ui": [
                    {"class": "FlatButton",
                     "props": {"label": "Off"},
                     "action": "off"},
                    {"class": "FlatButton",
                     "props": {"label": "On"},
                     "action": "on"}
                ]}

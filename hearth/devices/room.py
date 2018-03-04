"""Room device classes."""
import asyncio
import logging
import hearth
from hearth import Device

__all__ = ['Room']

LOGGER = logging.getLogger(__name__)


class Room(Device):
    """Room."""

    async def __init__(self, id_, *devices, sensors=None):
        """Init."""
        sensors = sensors or []
        await super().__init__(id_)
        self.devices = devices
        self.sensors = sensors
        hearth.add_devices(*devices)
        hearth.add_devices(*sensors)

    async def off(self):
        """Shut everything down."""
        LOGGER.info("Shutting down %s", self.id)
        asyncio.gather(*[d.off() for d in self.devices if hasattr(d, 'off')])

    def ui(self):
        """UI."""
        return {"rightIcon": "all_out", "rightAction": "off",
                "ui": [
                    {"class": "FlatButton",
                     "props": {"label": "Off"},
                     "action": "off"}
                ]}

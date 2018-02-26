"""Room device classes."""
import asyncio
import logging
import hearth
from hearth import Device

LOGGER = logging.getLogger(__name__)


class Room(Device):
    """Room."""

    def __init__(self, id_, *devices):
        """Init."""
        Device.__init__(self, id_)
        self.devices = devices
        hearth.add_devices(*devices)

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

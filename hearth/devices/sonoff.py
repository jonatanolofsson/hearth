"""SonOff device classes."""
import asyncio
import logging
from hearth import Device, mqtt

LOGGER = logging.getLogger(__name__)


class SonOff(Device):
    """SonOff switch."""

    def __init__(self, id_, name, mqttc=None):
        Device.__init__(self, id_)
        self.name = name
        self.mqtt = mqttc or mqtt.client
        self.state = {'on': False}
        asyncio.ensure_future(self.setup())

    async def setup(self):
        """Setup."""
        await self.mqtt.sub(f"stat/{self.name}/POWER", self.update_power_state)
        await self.mqtt.pub(f"cmnd/{self.name}/power", "")

    async def on(self):  # pylint: disable=invalid-name
        """Switch on."""
        self.expect_refresh(5)
        await self.mqtt.pub(f"cmnd/{self.name}/power", "on")

    async def off(self):
        """Switch off."""
        self.expect_refresh(5)
        await self.mqtt.pub(f"cmnd/{self.name}/power", "off")

    async def toggle(self):
        """Toggle."""
        await (self.off() if self.state['on'] else self.on())

    async def state_set(self, new_state, _):
        """Update state."""
        await (self.on() if new_state['on'] else self.off())

    async def update_power_state(self, _, payload):
        """Update power state."""
        LOGGER.info("%s: New power state: %s", self.name, payload)
        self.update_state({'on': (payload == "ON")})

    def ui(self):
        """Return jsx ui representation."""
        return {"rightIcon": "indeterminate_check_box", "rightAction": "toggle",
                "ui": [
                    {"class": "Toggle",
                     "props": {"label": "On"},
                     "state": "on"}
                ]}

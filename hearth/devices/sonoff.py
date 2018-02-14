"""SonOff device classes."""
import asyncio
import logging
from hearth import Device, mqtt

LOGGER = logging.getLogger(__name__)


class SonOff(Device):
    """SonOff switch."""

    def __init__(self, name, mqttc=None):
        self.mqtt = mqttc or mqtt.client
        self.name = name
        self.state = None
        asyncio.ensure_future(self.setup())

    async def setup(self):
        """Setup."""
        await self.mqtt.sub(f"stat/{self.name}/POWER", self.update_power_state)
        await self.mqtt.pub(f"cmnd/{self.name}/power", "")

    async def on(self):
        """Switch on."""
        await self.mqtt.pub(f"cmnd/{self.name}/power", "on")

    async def off(self):
        """Switch off."""
        await self.mqtt.pub(f"cmnd/{self.name}/power", "off")

    async def update_power_state(self, _, payload):
        """Update power state."""
        LOGGER.info("%s: New power state: %s", self.name, payload)
        self.state = payload
        self.refresh()

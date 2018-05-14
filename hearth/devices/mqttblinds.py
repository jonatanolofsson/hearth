"""MQTT blinds device class."""
import asyncio
import logging
from datetime import datetime, timedelta
import json
from hearth import Device, mqtt

__all__ = ['MqttBlinds']
WAIT_TIME = 10

LOGGER = logging.getLogger(__name__)


class MqttBlinds(Device):
    """MQTT blinds."""

    async def __init__(self, id_, name):
        await super().__init__(id_)
        self.name = name
        self.mqtt = await mqtt.server()
        await super().init_state({'level': False})
        await self.mqtt.sub(f"{self.name}/state", self.mqtt_update_state)
        asyncio.ensure_future(self.ping())

    async def mqtt_update_state(self, _, payload):
        """Update state from mqtt data."""
        await self.update_state(json.loads(payload))

    async def ping(self):
        """Periodically retrieve status to check connection is live."""
        while True:
            self.expect_update(WAIT_TIME)
            await self.mqtt.pub(f"{self.name}/send_state", "")
            await asyncio.sleep(600 if self.state['reachable'] else 30)

    async def up(self):  # pylint: disable=invalid-name
        """Blinds up."""
        self.expect_update(WAIT_TIME)
        await self.mqtt.pub(f"{self.name}/command", {"action": "u"})

    async def down(self):
        """Blinds down."""
        self.expect_update(WAIT_TIME)
        await self.mqtt.pub(f"{self.name}/command", {"action": "d"})

    async def stop(self):
        """Stop blinds."""
        self.expect_update(WAIT_TIME)
        await self.mqtt.pub(f"{self.name}/command", {"action": "s"})

    async def zero(self):
        """Set full up."""
        self.expect_update(WAIT_TIME)
        await self.mqtt.pub(f"{self.name}/command", {"action": "0"})

    async def one(self):
        """Set full down."""
        self.expect_update(WAIT_TIME)
        await self.mqtt.pub(f"{self.name}/command", {"action": "1"})

    async def level(self, level):
        """Move blinds."""
        self.expect_update(WAIT_TIME)
        await self.mqtt.pub(f"{self.name}/command", {"level": level})

    async def set_state(self, upd_state):
        """Update state."""
        if 'level' in upd_state:
            await self.level(upd_state['level'])
        else:
            await super().set_state(upd_state)

    def ui(self):
        """Return jsx ui representation."""
        return {"rightIcon": "indeterminate_check_box",
                "rightAction": "toggle",
                "ui": [
                    {"class": "Button",
                     "props": {"label": "Up"},
                     "action": "up"},
                    {"class": "Button",
                     "props": {"label": "Down"},
                     "action": "down"},
                    {"class": "Button",
                     "props": {"label": "Stop"},
                     "action": "stop"},
                    {"class": "Slider",
                     "props": {"label": "Level",
                               "min": 0,
                               "max": 1,
                               "step": 0.1},
                     "state": "level"}
                ],
               }

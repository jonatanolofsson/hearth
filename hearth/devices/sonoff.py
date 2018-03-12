"""SonOff device classes."""
import asyncio
import logging
from datetime import datetime, timedelta
from hearth import Device, mqtt

__all__ = ['SonOff']
WAIT_TIME = 10

LOGGER = logging.getLogger(__name__)


class SonOff(Device):
    """SonOff switch."""

    async def __init__(self, id_, name):
        await super().__init__(id_)
        self.name = name
        self.mqtt = await mqtt.server()
        await super().init_state({'on': False})
        await self.mqtt.sub(f"stat/{self.name}/POWER", self.update_power_state)
        asyncio.ensure_future(self.ping())

    async def ping(self):
        """Periodically retrieve status to check connection is live."""
        while True:
            self.expect_update(WAIT_TIME)
            await self.mqtt.pub(f"cmnd/{self.name}/power", "")
            await asyncio.sleep(60 if self.state['reachable'] else 30)

    async def on(self):  # pylint: disable=invalid-name
        """Switch on."""
        self.expect_update(WAIT_TIME)
        await self.mqtt.pub(f"cmnd/{self.name}/power", "on")

    async def off(self):
        """Switch off."""
        self.expect_update(WAIT_TIME)
        await self.mqtt.pub(f"cmnd/{self.name}/power", "off")

    async def toggle(self):
        """Toggle."""
        await (self.off() if self.state['on'] else self.on())

    async def set_state(self, new_state):
        """Update state."""
        if 'on' in new_state:
            await (self.on() if new_state['on'] else self.off())
        else:
            await super().set_state(new_state)

    async def update_power_state(self, _, payload):
        """Update power state."""
        LOGGER.info("%s: New power state: %s", self.name, payload)
        await self.update_state({'on': (payload == "ON")})

    def ui(self):
        """Return jsx ui representation."""
        onoffdata = []
        tprev = str(datetime.now()).split('.')[0]
        sprev = self.state['on']
        lasttime = str(datetime.now() - timedelta(hours=1)).split('.')[0]
        for t, s, in reversed(self.history):
            t = t.partition('.')[0]
            if t < lasttime:
                break
            onoffdata.append({'x': tprev, 'y': int(sprev)})
            onoffdata.append({'x': tprev, 'y': int(s['on'])})
            tprev = t
            sprev = s['on']
        onoffdata.append({'x': lasttime, 'y': int(sprev)})
        onoffdata.reverse()

        return {"rightIcon": "indeterminate_check_box",
                "rightAction": "toggle",
                "ui": [
                    {"class": "Toggle",
                     "props": {"label": "On"},
                     "state": "on"},
                    {"class": "C3Chart",
                     "state": "onoffdata",
                     "props": {
                         "data": {
                             "keys": {"x": "x", "value": ["y"]},
                             "types": {"x": "area"},
                             "xFormat": '%Y-%m-%d %H:%M:%S',
                         },
                         "size": {
                             "height": 150
                         },
                         "axis": {
                             "x": {
                                 "type": "timeseries",
                                 "tick": {"format": "%H:%M", "count": 4}
                             },
                             "y": {
                                 "max": 1,
                                 "min": 0,
                                 "tick": {"values": [0, 1]}
                             }
                         }
                     }
                    }
                ],
                "state": {"onoffdata": onoffdata}}

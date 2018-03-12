"""Sector Alarm Sensor."""
import asyncio
import logging
import hearth
import sectoralarm

__all__ = ['SectorAlarm']

LOGGER = logging.getLogger(__name__)


class SectorAlarm(hearth.Device):
    """Sector Alarm Sensor."""
    async def __init__(self, id_, username, password, panel):
        """Init."""
        await super().__init__(id_)
        self.username = username
        self.password = password
        self.panel = panel
        self.session = None
        self.sleeptime = 60
        await self.connect()
        asyncio.ensure_future(self.syncer())

    async def connect(self):
        """Connect."""
        self.session = await sectoralarm.Session(self.username,
                                                 self.password,
                                                 self.panel)

    async def sync(self):
        """Sync data."""
        try:
            new_state = {}
            new_state.update(await self.session.get_arm_state())
            # new_state.update(await self.session.get_temperature())
            LOGGER.debug("Got SA state: %s", new_state)
            await self.update_state(new_state)
        except:
            await self.update_state({"reachable": False}, False)

    async def syncer(self):
        """Stay in sync."""
        while True:
            await self.sync()
            await asyncio.sleep(self.sleeptime)

    def ui(self):
        """Return ui representation."""
        return {"ui": [
            {"class": "Text",
             "props": {"label": "Armed"},
             "state": "message"},
        ]}

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
        self.sleeptime = 600
        self.temperature_devices = {}
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
            armstate = await self.session.get_arm_state()
            new_state['armed'] = armstate['message']
            new_state['armed_time'] = armstate['timeex']
            new_state['armed_by'] = armstate['user']
            temps = (await self.session.get_temperature())['temperatureComponentList']
            new_state['temperatures'] = [
                {key: temp[key] for key in ['serialNo', 'label', 'temperature']}
                for temp in temps]
            if 'armed' in new_state and new_state['armed'] != self.state['armed']:
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
        uix = {"ui": [
            {"class": "Text",
             "props": {"label": "Armed"},
             "state": "armed"},
            {"class": "Text",
             "props": {"label": "Armed at"},
             "state": "armed_time"},
            {"class": "Text",
             "props": {"label": "Armed by"},
             "state": "armed_by"},
        ],
        "state": {}}
        for therm in self.state.get('temperatures', []):
            uix['ui'].append(
                {"class": "Text",
                 "props": {"label": therm['label'], "format": "{} °C"},
                 "state": 'temp' + therm['serialNo']},
            )
            uix['state'].update({'temp' + therm['serialNo']: therm['temperature']})
        return uix

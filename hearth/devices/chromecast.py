"""Chromecast device class."""
import asyncio
import re
import aiohttp
from hearth import Device

DEVICES = {}

__all__ = ['Chromecast']


class Chromecast(Device):
    """Chromecast device."""

    async def __init__(self, id_, ip):
        """Init."""
        await super().__init__(id_)
        await self.init_state({}, True)
        self.ip = ip
        self.session = await aiohttp.ClientSession().__aenter__()

    async def app_id(self):
        """Get app id."""
        try:
            async with self.session.get(f"http://{self.ip}:8008/apps", timeout=10) as res:
                res = await res.text()
                return re.search(r"\<name\>([^\<]*)\</name\>", res).group(1)
        except:
            pass
        return None

    async def is_idle(self):
        """Return true/false if the device is connected to an app."""
        app_id = await self.app_id()
        return app_id in (None, 'E8C28D3C')

    async def shutdown(self):
        """Shut down."""
        await self.session.__aexit__(None, None, None)

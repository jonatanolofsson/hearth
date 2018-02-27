"""ZigBee server."""
import asyncio
import logging
import bellows.ezsp
import bellows.zigbee.application
from bellows.zigbee.util import convert_ieee

LOGGER = logging.getLogger(__name__)
SERVER = None  # pylint: disable=invalid-name


async def server():
    """Get server when available."""
    while SERVER is None:
        await asyncio.sleep(0.2)
    return SERVER


def start(dbfile='zigbee.db', dev='/dev/zigbee', baudrate=57600):
    """Start ZigBee server."""
    async def astart():
        global SERVER  # pylint: disable=invalid-name, global-statement
        ezsp = bellows.ezsp.EZSP()
        await ezsp.connect(dev, baudrate)
        app = bellows.zigbee.application.ControllerApplication(ezsp, dbfile)
        await app.startup(auto_form=True)
        SERVER = app
        LOGGER.info("Started zigbee server: %s", dbfile)
    asyncio.get_event_loop().run_until_complete(astart())

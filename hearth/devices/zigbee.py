import json
import logging
import hearth
from hearth.device import Device as DeviceBase
from hearth import mqtt

LOGGER = logging.getLogger(__name__)


class ZigbeeController(DeviceBase):
    """Control the Zigbee backend."""
    async def __init__(self, id_='ZigBee'):
        """Init."""
        await super().__init__(id_)
        await super().init_state({'online': False, 'version': 0, 'commit': 0, 'coordinator': '', 'permit_join': False})
        self.mqtt = await mqtt.server()
        hearth.add_devices(self)
        await self.mqtt.sub(r"zigbee2mqtt/bridge/state", self.onoffline)
        await self.mqtt.sub(r"zigbee2mqtt/bridge/config", self.updatehandler)

    async def onoffline(self, _, payload):
        LOGGER.info("Getting zigbee update: %s :: %s", self.id, payload)
        self.state['online'] = (payload == 'online')

    async def updatehandler(self, _, payload):
        """Handle update message from MQTT."""
        LOGGER.info("Getting zigbee update: %s :: %s", self.id, payload)
        try:
            await self.update_state(json.loads(payload))
        except:
            LOGGER.warning("Failed to parse MQTT message: %s", payload)

    async def open_network(self):
        """Open network."""
        LOGGER.info("Opening ZigBee network")
        await self.mqtt.pub('zigbee2mqtt/bridge/config/permit_join', 'true')

    async def close_network(self):
        """Close network."""
        LOGGER.info("Closing ZigBee network")
        await self.mqtt.pub('zigbee2mqtt/bridge/config/permit_join', 'false')

    def ui(self):
        """UI."""
        return {"ui": [
                {"class": "Text", "props": {"label": "Online: "}, "state": "online"},
                {"class": "Text", "props": {"label": "Permit join: "}, "state": "permit_join"},
                {"class": "Button",
                 "props": {"label": "Open network"},
                 "action": "open_network"},
                {"class": "Button",
                 "props": {"label": "Close network"},
                 "action": "close_network"}] + self.events_ui()}



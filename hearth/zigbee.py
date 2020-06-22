"""Zigbee server."""
import asyncio
import json
import logging
from hearth import mqtt
from asyncinit import asyncinit
from .device import Device as DeviceBase
from . import hearth

LOGGER = logging.getLogger(__name__)


class ZigbeeController(DeviceBase):
    """Control the Zigbee backend."""
    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__(*args, **kwargs)
        await self.update_state({})

    async def open_network(self):
        """open network."""
        self.mqtt.publish('zigbee2mqtt/bridge/config/permit_join', 'true')

    async def close_network(self):
        """open network."""
        self.mqtt.publish('zigbee2mqtt/bridge/config/permit_join', 'false')

    def ui(self):
        """UI."""
        return {"ui": [
                    {"class": "Button",
                     "props": {"label": "Open network"},
                     "action": "open_network"},
                    {"class": "Button",
                     "props": {"label": "Close network"},
                     "action": "close_network"}
                ]
                + self.events_ui()}


class Device(DeviceBase):
    """Zigbee device."""
    async def __init__(self, id_, uid):
        await super().__init__(id_)
        self.uid = uid if uid.startswith('0x') else '0x' + uid.split('-')[0].replace(':', '')
        self.mqtt = await mqtt.server()
        self.zbstates = []
        await self.mqtt.sub(f"zigbee2mqtt/{self.uid}", self.updatehandler)
        await self.refresh()

    async def updatehandler(self, _, payload):
        """Handle updatemessage from MQTT."""
        LOGGER.info("Getting zigbee update: %s :: %s", self.uid, payload)
        try:
            await self.update_state(json.loads(payload))
        except:
            LOGGER.warning("Failed to parse MQTT message: %s", payload)

    async def set_state(self, upd_state):
        """Update state."""
        zbstates = {key: value for key, value in upd_state.items()
                    if key in self.zbstates}
        if zbstates:
            await self.mqtt.pub(f"zigbee2mqtt/{self.uid}/set", zbstates)
            LOGGER.info("Publish zbstates on %s: %s", f"zigbee2mqtt/{self.uid}/set", zbstates)
        await super().set_state(upd_state)

    async def refresh(self):
        await self.mqtt.pub(f"zigbee2mqtt/{self.uid}/get", '')

    def alerts(self):
        """List of active alerts."""
        active_alerts = super().alerts()
        try:
            if self.state['battery'] < 10:
                active_alerts.append(
                    {"icon": "battery_alert",
                     "label": f"Low battery: {self.state['battery']} %",
                     "color": "#f44336"})
        except:
            pass
        return active_alerts

"""Zigbee server."""
import json
import logging
from hearth import mqtt
from .device import Device as DeviceBase

LOGGER = logging.getLogger(__name__)


class Device(DeviceBase):
    """Zigbee device."""
    async def __init__(self, id_):
        await super().__init__(id_)
        self.mqtt = await mqtt.server()
        self.zbstates = []
        await self.mqtt.sub(f"zigbee2mqtt/{self.id}", self.updatehandler)
        await self.refresh()

    async def updatehandler(self, _, payload):
        """Handle updatemessage from MQTT."""
        LOGGER.info("Getting zigbee update: %s :: %s", self.id, payload)
        try:
            await self.update_state(json.loads(payload))
        except:
            LOGGER.warning("Failed to parse MQTT message: %s", payload)

    async def set_state(self, upd_state):
        """Update state."""
        zbstates = {key: value for key, value in upd_state.items()
                    if key in self.zbstates}
        if zbstates:
            await self.mqtt.pub(f"zigbee2mqtt/{self.id}/set", zbstates)
            LOGGER.info("Publish zbstates on %s: %s", f"zigbee2mqtt/{self.id}/set", zbstates)
        await super().set_state(upd_state)

    async def refresh(self):
        await self.mqtt.pub(f"zigbee2mqtt/{self.id}/get", '')

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

"""ZWave device classes."""
import json
import logging
from hearth import Device, mqtt

__all__ = ['ZWThermostat']
WAIT_TIME = 10

LOGGER = logging.getLogger(__name__)


class ZWDevice(Device):
    """SonOff switch."""

    async def __init__(self, id_, zwid):
        await super().__init__(id_)
        self.zwid = zwid
        self.mqtt = await mqtt.server()
        self.zwstates = []
        await self.mqtt.sub(f"zwave/updates/{self.zwid}", self.updatehandler)

    async def updatehandler(self, _, payload):
        """Handle updatemessage from MQTT."""
        try:
            await self.update_state(json.loads(payload))
        except:
            LOGGER.debug("Failed to parse MQTT message: %s", msg)

    async def set_state(self, upd_state):
        """Update state."""
        zwstates = {key: value for key, value in upd_state.items()
                    if key in self.zwstates}
        if zwstates:
            await self.mqtt.pub(f"zwave/set/{self.zwid}", zwstates)
        await super().set_state(upd_state)


class ZWThermostat(ZWDevice):
    """ZWave thermostat."""
    async def __init__(self, id_, zwid):
        await super().__init__(id_, zwid)
        await super().init_state({'Heating 1': 21.0, "Battery Level": 100})
        self.zwstates += ["Heating 1"]

    async def set_temperature(self, setpoint):
        """Set new temperature setpoint."""
        await self.set_state({"Heating 1": setpoint})

    def ui(self):
        """Return jsx ui representation."""

        return {"rightIcon": "indeterminate_check_box",
                "rightAction": "toggle",
                "ui": [
                    {"class": "Slider",
                     "props": {"label": "Temperature setpoint",
                               "min": 5,
                               "max": 28,
                               "step": 0.5},
                     "state": "Heating 1"},
                    {"class": "Text",
                     "props": {"label": "Battery", "format": "{} %"},
                     "state": "Battery Level"},
                ]}

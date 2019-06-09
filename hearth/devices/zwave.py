"""ZWave device classes."""
import json
import logging
from hearth import Device, mqtt

__all__ = ['ZWThermostat', 'ZWSwitch', 'ZWDimmer']
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
        LOGGER.info("Getting zwave update: %s :: %s", self.zwid, payload)
        try:
            await self.update_state(json.loads(payload))
        except:
            LOGGER.warning("Failed to parse MQTT message: %s", payload)

    async def set_state(self, upd_state):
        """Update state."""
        zwstates = {key: value for key, value in upd_state.items()
                    if key in self.zwstates}
        if zwstates:
            await self.mqtt.pub(f"zwave/set/{self.zwid}", zwstates)
            LOGGER.info("Publish zwstates on %s: %s", f"zwave/set/{self.zwid}", zwstates)
        await super().set_state(upd_state)

    async def refresh(self, states=None):
        await self.mqtt.pub(f"zwave/refresh/{self.zwid}",
                            states or self.zwstates)


class ZWThermostat(ZWDevice):
    """ZWave thermostat."""
    async def __init__(self, id_, zwid):
        await super().__init__(id_, zwid)
        await super().init_state({'Heating 1': 21.0, "Battery Level": 100})
        self.zwstates += ["Heating 1"]
        # FIXME: Set "Day", "Hour", "Minute"
        await self.refresh()

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
                               "step": 0.5,
                               "dots": True},
                     "state": "Heating 1"},
                    {"class": "Text",
                     "props": {"label": "Battery", "format": "{} %"},
                     "state": "Battery Level"},
                ]}


class ZWSwitch(ZWDevice):
    """ZWave Switch."""
    async def __init__(self, id_, zwid):
        await super().__init__(id_, zwid)
        await super().init_state({'Switch': False, "Energy": 0, "Power": 0})
        self.zwstates += ["Switch"]
        await self.refresh()

    async def on(self):  # pylint: disable=invalid-name
        """Switch on."""
        await self.set_state({'Switch': True})

    async def off(self):
        """Switch off."""
        await self.set_state({'Switch': False})

    async def toggle(self):
        """Toggle."""
        await (self.off() if self.state['Switch'] else self.on())

    def ui(self):
        """Return ui representation."""
        return {"rightIcon": "indeterminate_check_box",
                "rightAction": "toggle",
                "ui": [
                    {"class": "Switch",
                     "props": {"label": "On"},
                     "state": "Switch"},
                ]}


class ZWDimmer(ZWDevice):
    """ZWave dimmer."""
    async def __init__(self, id_, zwid):
        await super().__init__(id_, zwid)
        await super().init_state({"Switch": False, "Level": 0, "Energy": 0, "Power": 0, "ResumeLevel": 99})
        self.zwstates += ["Level", "Energy", "Power"]
        await self.refresh()

    async def set_state(self, upd_state):
        """Update state."""
        if "Switch" in upd_state:
            if upd_state["Switch"]:
                await self.on()
            else:
                await self.off()
            del upd_state["Switch"]

        await super().set_state(upd_state)
        self.state["Switch"] = (self.state["Level"] > 0.01)
        if self.state["Level"] > 0:
            self.state["ResumeLevel"] = self.state["Level"]

    async def update_state(self, upd_state, set_seen=True):
        if "Level" in upd_state:
            upd_state["Switch"] = (upd_state["Level"] > 0.01)
            if upd_state["Level"] > 0.01:
                upd_state["ResumeLevel"] = upd_state["Level"]
        await super().update_state(upd_state, set_seen)

    async def on(self):  # pylint: disable=invalid-name
        """Switch on."""
        level = self.state.get("ResumeLevel", 99)
        if level < 0.01:
            level = 99
        await self.set_state({'Level': level})

    async def off(self):
        """Switch off."""
        await self.set_state({'Level': 0})

    async def toggle(self):
        """Toggle."""
        await (self.off() if self.state['Switch'] else self.on())

    async def brightness(self, bri, transisiontime=0):
        """Set brightness."""
        await self.set_state({'Level': min(max(0, int(bri)), 99)})

    async def dim_up(self, percent=10, transisiontime=0):
        """Dim up."""
        await self.brightness(self.state['bri'] + percent, transisiontime)

    async def dim_down(self, percent=10, transisiontime=0):
        """Dim down."""
        await self.brightness(self.state['bri'] - percent, transisiontime)

    def ui(self):
        """Return ui representation."""
        return {"rightIcon": "indeterminate_check_box",
                "rightAction": "toggle",
                "ui": [
                    {"class": "Switch",
                     "props": {"label": "On"},
                     "state": "Switch"},
                    {"class": "Slider",
                     "props": {"label": "Brightness",
                               "min": 0,
                               "max": 99,
                               "step": 1},
                     "state": "Level"},
                    {"class": "Text",
                        "props": {"label": "Power", "format": "{:1} W"},
                     "state": "Power"},
                ]}

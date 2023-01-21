"""ZWave device classes."""
import asyncio
import json
import logging
import hearth
from hearth import Device, mqtt

__all__ = ['ZWThermostat', 'ZWSwitch', 'ZWDimmer']  #, 'ZWSwitchDimmer']
WAIT_TIME = 10

LOGGER = logging.getLogger(__name__)


class ZWDevice(Device):
    """ZWave device."""

    async def __init__(self, id_, zwid, endpoint=1, mqtt_prefix="zwave"):
        await super().__init__(id_)
        self.zwid = zwid
        self.endpoint = endpoint
        self.mqtt = await mqtt.server()
        self.zwstates = {}
        self.zwstates_inv = {}
        self.basetopic = f"{mqtt_prefix}/{self.zwid}"
        await self.mqtt.sub(f"{self.basetopic}/status", self.statushandler)

    async def subscribe(self):
        self.zwstates_inv = {y: x for x, y in self.zwstates.items()}
        await asyncio.gather(*[
            self.mqtt.sub(f"{self.basetopic}/{key}", self.updatehandler)
            for key in self.zwstates.values()])

    async def updatehandler(self, topic, payload):
        key = topic[len(self.basetopic) + 1:]
        if key in self.zwstates_inv:
            state = self.zwstates_inv[key]
        else:
            LOGGER.info("Invalid topic: %s: %s", topic, payload)
            return
        try:
            data = json.loads(payload)
            LOGGER.info("Updating from zwave: %s: %s", state, data)
            await self.update_state({state: data["value"] if "value" in data else None})
        except Exception as e:
            LOGGER.warning("Failed to parse MQTT update message: \"%s\" (%s / %s): %s :: %s", topic, key, state, payload, e)

    async def statushandler(self, _, payload):
        """Handle updatemessage from MQTT."""
        LOGGER.info("Getting zwave update: %s :: %s", self.zwid, payload)
        try:
            data = json.loads(payload)
            await self.update_state({"ready": data["value"], "status": data["status"]})
        except:
            LOGGER.warning("Failed to parse MQTT status message: %s", payload)

    async def set_state(self, upd_state):
        """Update state."""
        zwstates = {self.zwstates[key]: value for key, value in upd_state.items()
                    if key in self.zwstates}
        if zwstates:
            await asyncio.gather(*[self.mqtt.pub(f"{self.basetopic}/{key}/set", {"value": value}) for key, value in zwstates.items()])
            LOGGER.info("Publish zwstates to %s: %s", {self.basetopic}, zwstates)
        await super().set_state(upd_state)


class ZWThermostat(ZWDevice):
    """ZWave thermostat."""
    async def __init__(self, id_, zwid, endpoint=0, mqtt_prefix="zwave"):
        await super().__init__(id_, zwid, endpoint, mqtt_prefix)
        await super().init_state({'temperature_setpoint': 21.0, "battery": 100})
        self.zwstates["temperature_setpoint"] = "67/0/setpoint/1"
        self.zwstates["battery"] = "128/0/level"
        # FIXME: Set "Day", "Hour", "Minute"
        await self.subscribe()

    async def set_temperature(self, setpoint):
        """Set new temperature setpoint."""
        await self.set_state({"temperature_setpoint": setpoint})

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
                     "state": "temperature_setpoint"},
                    {"class": "Text",
                     "props": {"label": "Battery", "format": "{} %"},
                     "state": "battery"},
                ]}


class ZWSwitch(ZWDevice):
    """ZWave Switch."""
    async def __init__(self, id_, zwid, endpoint=1, mqtt_prefix="zwave"):
        await super().__init__(id_, zwid, mqtt_prefix)
        await super().init_state({'switch': False, "power": 0})
        self.zwstates["switch"] = f"37/{endpoint}/currentValue"
        self.zwstates["power"] = f"50/{endpoint}/value/66049"
        await self.subscribe()

    async def on(self):  # pylint: disable=invalid-name
        """Switch on."""
        await self.set_state({'switch': True})

    async def off(self):
        """Switch off."""
        await self.set_state({'switch': False})

    async def toggle(self):
        """Toggle."""
        await (self.off() if self.state['switch'] else self.on())

    def ui(self):
        """Return ui representation."""
        return {"rightIcon": "indeterminate_check_box",
                "rightAction": "toggle",
                "ui": [
                    {"class": "Switch",
                     "props": {"label": "On"},
                     "state": "switch"},
                    {"class": "Text",
                        "props": {"label": "Power", "format": "{:1} W"},
                     "state": "power"},
                ]}


class ZWDimmer(ZWDevice):
    """ZWave dimmer."""
    async def __init__(self, id_, zwid, mqtt_prefix="zwave"):
        await super().__init__(id_, zwid, 1, mqtt_prefix)
        await super().init_state({"switch": False, "level": 0, "power": 0, "resumelevel": 99, "resumelevel2": 99})
        self.zwstates["level"] = f"38/1/currentValue"
        self.zwstates["level2"] = f"38/2/currentValue"
        self.zwstates["power"] = f"49/1/Power"
        self.zwstates["event"] = "43/0/sceneId"
        await self.subscribe()
        self.listen("statechange:event", self.scene_change)

    async def scene_change(self, scene):
        events = {
            16: "s1_1click",
            14: "s1_2click",
            12: "s1_hold",
            13: "s1_release",
            26: "s2_1click",
            24: "s2_2click",
            25: "s2_3click",
            22: "s2_hold",
            23: "s2_release",
        }
        if scene in events:
            self.event(events[scene])

    async def set_state(self, upd_state):
        """Update state."""
        if "switch" in upd_state:
            if upd_state["switch"]:
                await self.on()
            else:
                await self.off()
            del upd_state["switch"]

        await super().set_state(upd_state)
        self.state["switch"] = (self.state["level"] > 0.01)
        if self.state["level"] > 0:
            self.state["resumelevel"] = self.state["level"]
        if self.state["level2"] > 0:
            self.state["resumelevel2"] = self.state["level2"]

    async def update_state(self, upd_state, set_seen=True):
        if "level" in upd_state:
            upd_state["switch"] = (upd_state["level"] > 0.01)
            if upd_state["level"] > 0.01:
                upd_state["resumelevel"] = upd_state["level"]
            if upd_state["level2"] > 0.01:
                upd_state["resumelevel2"] = upd_state["level2"]
        await super().update_state(upd_state, set_seen)

    async def on(self):  # pylint: disable=invalid-name
        """Switch on."""
        level = self.state.get("resumelevel", 99)
        if level < 0.01:
            level = 99
        await self.set_state({'level': level})

    async def off(self):
        """Switch off."""
        await self.set_state({'level': 0})

    async def toggle(self):
        """Toggle."""
        await (self.off() if self.state['switch'] else self.on())

    async def brightness(self, bri, transisiontime=0):
        """Set brightness."""
        await self.set_state({'level': min(max(0, int(bri)), 99)})

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
                     "state": "switch"},
                    {"class": "Slider",
                     "props": {"label": "Brightness",
                               "min": 0,
                               "max": 99,
                               "step": 1},
                     "state": "level"},
                    {"class": "Text",
                        "props": {"label": "Power", "format": "{:1} W"},
                     "state": "power"},
                ]}


# class ZWSwitchDimmer(ZWDevice):
    # """ZWave Switch."""
    # async def __init__(self, id_, zwid, device, endpoint=2, mqtt_prefix="zwave"):
        # await super().__init__(id_, zwid, mqtt_prefix)
        # await super().init_state({'switch': False})
        # self.zwstates["switch"] = f"38/{endpoint}/0"
        # self.zwstates["event"] = f"91/1/{endpoint}"
        # self.device = device
        # self.listen("statechange:event:Key Held down", self.device.circle_brightness)
        # self.listen("statechange:event:Key Released", self.device.stop_circle_brightness)
        # hearth.add_devices(device)
        # await self.subscribe()

    # async def on(self):  # pylint: disable=invalid-name
        # """Switch on."""
        # await self.set_state({'switch': True})

    # async def off(self):
        # """Switch off."""
        # await self.set_state({'switch': False})

    # async def toggle(self):
        # """Toggle."""
        # await (self.off() if self.state['switch'] else self.on())

    # def ui(self):
        # """Return ui representation."""
        # return {"rightIcon": "indeterminate_check_box",
                # "rightAction": "toggle",
                # "ui": [
                    # {"class": "Switch",
                     # "props": {"label": "On"},
                     # "state": "switch"},
                    # {"class": "Text",
                        # "props": {"label": "Power", "format": "{:1} W"},
                     # "state": "power"},
                # ]}


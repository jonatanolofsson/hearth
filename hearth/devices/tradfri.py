"""Trådfri device driver."""
import asyncio
import logging
from hearth import zigbee, Device
from bellows.zigbee.zcl.clusters.general import OnOff, LevelControl
from bellows.zigbee.zcl.clusters.lighting import Color

LOGGER = logging.getLogger(__name__)


class Tradfri(Device):
    """Base Trådfri driver."""

    def __init__(self, id_, ieee):
        """Init."""
        Device.__init__(self, id_)
        self.id = id_
        self.ieee = zigbee.convert_ieee(ieee)
        self.device = None
        self.state = {'on': False,
                      'bri': 0}
        asyncio.ensure_future(self.setup())

    async def setup(self):
        """Setup."""
        self.device = await (await zigbee.server()).get_device(ieee=self.ieee)
        self.device.add_listener(self)
        await self.load_state()

    async def load_state(self):
        """Load state from zigbee device."""
        LOGGER.info("Loading state")
        self.update_state({
            'on': bool(await self.device[1].on_off['on_off', ]),
            'bri': int(await self.device[1].level['current_level', ])
        })
        LOGGER.info("Loaded state: %s", self.state)

    async def attribute_updated(self, cluster, attrid, value):
        """Listener for updated attributes."""
        if cluster.ep_attribute == 'on_off':
            if attrid == OnOff._attridx['on_off']:
                self.update_state({'on': bool(value)})
                LOGGER.info("Updated state: %s (%s)", self.state, value)
        elif cluster.ep_attribute == 'on_off':
            if attrid == LevelControl._attridx['current_level']:
                self.update_state({'bri': int(value)})
                LOGGER.info("Updated state: %s (%s)", self.state, value)

    async def state_set(self, new_state, old_state):
        """Update state."""
        LOGGER.info("New state: %s  (%s)", new_state, old_state);
        if new_state['on'] != old_state['on']:
            await (self.on() if new_state['on'] else self.off())
        if new_state['bri'] != old_state['bri']:
            await self.brightness(new_state["bri"])
            self.update_state({'bri': int(await self.device[1].level['current_level', ])})

    def ui(self):
        """Return ui representation."""
        return {"rightIcon": "indeterminate_check_box",
                "rightAction": "toggle",
                "ui": [
                    {"class": "Toggle",
                     "props": {"label": "On"},
                     "state": "on"},
                    {"class": "Slider",
                     "props": {"label": "Brightness",
                               "min": 0,
                               "max": 255,
                               "step": 1},
                     "state": "bri"}
                ]}

    async def on(self):  # pylint: disable=invalid-name
        """Switch on."""
        self.expect_refresh(5)
        LOGGER.info("Putting on light.")
        await self.device[1].on_off.on()
        self.update_state({'on': bool(await self.device[1].on_off['on_off', ])})

    async def off(self):
        """Switch off."""
        self.expect_refresh(5)
        await self.device[1].on_off.off()
        self.update_state({'on': bool(await self.device[1].on_off['on_off', ])})

    async def toggle(self):
        """Toggle."""
        await (self.off() if self.state['on'] else self.on())

    async def brightness(self, bri):
        """Set brightness."""
        await self.device[1].level.move_to_level_with_on_off(bri, 0)


class TradfriTemperature(Tradfri):
    """Trådfri light with controllable color temperature."""

    async def load_state(self):
        """Load state from zigbee device."""
        await Tradfri.load_state(self)
        self.update_state({
            'ct': int(await self.device[1].light_color['color_temperature', ])
        })
        LOGGER.info("Loaded state: %s", self.state)

    async def attribute_updated(self, cluster, attrid, value):
        """Listener for updated attributes."""
        await Tradfri.attribute_updated(self, cluster, attrid, value)
        if cluster.ep_attribute == 'light_color':
            if attrid == Color._attridx['color_temperature']:
                self.update_state({'ct': int(value)})
                LOGGER.info("Updated state: %s (%s)", self.state, value)

    async def state_set(self, new_state, old_state):
        """Update state."""
        await Tradfri.state_set(self, new_state, old_state)
        if new_state['ct'] != old_state['ct']:
            await self.temperature(new_state["ct"])
            self.update_state({'ct': int(await self.device[1].light_color['color_temperature', ])})

    def ui(self):
        """Return ui representation."""
        uix = Tradfri.ui(self)
        uix['ui'].append(
            {"class": "Slider",
             "props": {"label": "Temperature",
                       "min": 250,
                       "max": 454,
                       "step": 1},
             "state": "ct"})
        return uix

    async def temperature(self, ct):
        """Set color temperature."""
        await self.device[1].light_color.move_to_color_temp(ct, 0)

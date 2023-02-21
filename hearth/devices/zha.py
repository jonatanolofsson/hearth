import logging
from hearth.sensor import Sensor
from hearth.device import Device as DeviceBase
from hearth.zigbee import Device as ZDevice

__all__ = ['ZHATemperature', 'ZHAHumidity', 'ZHAPressure', 'ZHAWeather', 'ZHAContact', 'ZHAPresence', 'ZHASwitch', 'ZHALight', 'ZHALightCT']
LOGGER = logging.getLogger(__name__)


class ZHASensor(Sensor, ZDevice):
    """Temperature device."""

    async def __init__(self, sensor_states, *args, **kwargs):
        """Init."""
        await ZDevice.__init__(self, *args, **kwargs)
        await Sensor.__init__(self, sensor_states)
        self.zbstates += self.sensor_states


class ZHATemperature(ZHASensor):
    """Zigbee temperature sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('temperature', *args, **kwargs)


class ZHAHumidity(ZHASensor):
    """Zigbee humidity sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('humidity', *args, **kwargs)


class ZHAPressure(ZHASensor):
    """Zigbee pressure sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('pressure', *args, **kwargs)


class ZHAWeather(ZHASensor):
    """Zigbee pressure sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__(['temperature', 'humidity', 'pressure'], *args, **kwargs)


class ZHAContact(ZHASensor):
    """Zigbee window/door sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('contact', *args, **kwargs)
        self.discrete = True


class ZHAPresence(ZHASensor):
    """Zigbee window/door sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('occupancy', *args, **kwargs)
        self.discrete = True


class ZHASwitch(ZDevice):
    """ZHASwitch remote driver."""

    def ui(self):
        """Return ui representation."""
        return {"ui": self.events_ui() + [
            {"class": "Text",
             "props": {"label": "Battery", "format": "{} %"},
             "state": "battery"},
        ]}

    async def update_state(self, upd_state, set_seen=True):
        """Update state."""
        if 'action' in upd_state:
            self.event(upd_state['action'])
            await super().update_state({}, set_seen)
        else:
            await super().update_state(upd_state, set_seen)


class ZHALight(ZDevice):
    """Base ZHALight driver."""

    async def __init__(self, *args, **kwargs):
        await super().__init__(*args, **kwargs)
        self.zbstates += ['state', 'brightness', 'brightness_move_onoff']
        await super().init_state({'state': False, 'brightness': 100})

    def ui(self):
        """Return ui representation."""
        return {"rightIcon": "indeterminate_check_box",
                "rightAction": "toggle",
                "ui": [
                    {"class": "Switch",
                     "props": {"label": "On"},
                     "state": "state"},
                    {"class": "Slider",
                     "props": {"label": "Brightness",
                               "min": 0,
                               "max": 255,
                               "step": 1},
                     "state": "brightness"}
                ]}

    async def is_on(self):
        """Check if light is on."""
        return self.state['state']

    async def set_state(self, upd_state):
        """Set new state."""
        if 'brightness' in upd_state\
           or 'color_temp' in upd_state:
            upd_state['state'] = True
        if 'state' in upd_state:
            upd_state['state'] = "ON" if upd_state['state'] else "OFF"
        await super().set_state(upd_state)

    async def update_state(self, upd_state, set_seen=True):
        """Update state."""
        if 'state' in upd_state:
            upd_state['state'] = (str(upd_state["state"]).upper() == "ON")
        await super().update_state(upd_state, set_seen)

    async def on(self):  # pylint: disable=invalid-name
        """Switch on."""
        await self.set_state({'state': True})

    async def off(self):
        """Switch off."""
        await self.set_state({'state': False})

    async def toggle(self):
        """Toggle."""
        await (self.off() if self.state['state'] else self.on())

    async def brightness(self, bri, transitiontime=0):
        """Set brightness."""
        await self.set_state({'brightness': min(max(0, int(bri)), 255),
                              'transition': transitiontime})

    async def dim_up(self, percent=10, transitiontime=0):
        """Dim up."""
        await self.brightness(
            self.state['brightness'] + 255 * percent / 100, transitiontime)

    async def dim_down(self, percent=10, transitiontime=0):
        """Dim down."""
        await self.brightness(
            self.state['brightness'] - 255 * percent / 100, transitiontime)

    async def cycle_brightness(self):
        """Start moving brightness level (down if max, else up)"""
        # brightness_move: https://www.zigbee2mqtt.io/devices/LED1545G12.html#ikea-led1545g12
        if self.state['brightness'] >= 250:
            await self.set_state({'brightness_move_onoff': -40})
        else:
            await self.set_state({'brightness_move_onoff': 40})

    async def stop_cycle_brightness(self):
        """Stop moving brightness level"""
        await self.set_state({'brightness_move_onoff': 0})


class ZHALightCT(ZHALight):
    """ZHALight light with controllable color temperature."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__(*args, **kwargs)
        self.zbstates += ['color_temp']
        self.ctmin = 250
        self.ctmax = 454

    def ui(self):
        """Return ui representation."""
        uix = ZHALight.ui(self)
        uix['ui'].append(
            {"class": "Slider",
             "props": {"label": "Temperature",
                       "min": self.ctmin,
                       "max": self.ctmax,
                       "step": 1},
             "state": "color_temp"})
        return uix

    async def temperature(self, ct, transitiontime=0):
        """Set color temperature."""
        await self.set_state({'color_temp': min(max(self.ctmin, ct), self.ctmax),
                              'transition': transitiontime})

    async def warmer(self, percent=10, transitiontime=0):
        """Warmer light color."""
        await self.temperature(self.state['color_temp'] + (self.ctmax - self.ctmin) * percent / 100,
                               transitiontime)

    async def colder(self, percent=10, transitiontime=0):
        """Colder light color."""
        await self.temperature(self.state['color_temp'] - (self.ctmax - self.ctmin) * percent / 100,
                               transitiontime)

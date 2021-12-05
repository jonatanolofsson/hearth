import logging
from datetime import datetime, timedelta
from hearth.device import Device as DeviceBase
from hearth.zigbee import Device as ZDevice

__all__ = ['ZHATemperature', 'ZHAHumidity', 'ZHAOpenClose', 'ZHAPresence', 'ZHASwitch', 'ZHALight', 'ZHALightCT']
LOGGER = logging.getLogger(__name__)


class ZHASensor(ZDevice):
    """Temperature device."""

    async def __init__(self, mainstate, *args, **kwargs):
        """Init."""
        self.mainstate = mainstate
        self.divisor = 100
        self.discrete = True
        await super().__init__(*args, **kwargs)
        await super().init_state({mainstate: False})
        self.zbstates += [mainstate]

    def ui(self):
        """Return ui representation."""
        plotdata = []
        lasttime = str(datetime.now() - timedelta(hours=1)).split('.')[0]
        if self.discrete:
            t = tprev = str(datetime.now()).split('.')[0]
            sprev = self.state[self.mainstate]
            lstart = (tprev, int(sprev))
            for t, s, in reversed(self.history):
                t = t.partition('.')[0]
                if sprev != s[self.mainstate]:
                    plotdata.append({'x': lstart[0], 'y': lstart[1]})
                    plotdata.append({'x': tprev, 'y': lstart[1]})
                    lstart = (tprev, int(s[self.mainstate]))
                tprev = t
                sprev = s[self.mainstate]
                if t < lasttime:
                    t = lasttime
                    break
            plotdata.append({'x': lstart[0], 'y': lstart[1]})
            if t != tprev:
                plotdata.append({'x': t, 'y': lstart[1]})
        else:
            for t, s, in reversed(self.history):
                if self.mainstate not in s:
                    continue
                t = t.partition('.')[0]
                if t < lasttime:
                    break
                plotdata.append({'x': t, 'y': s[self.mainstate] / self.divisor})
        plotdata.reverse()

        return {
            "ui": [
                {"class": "C3Chart",
                 "state": "plotdata",
                 "props": {
                     "data": {
                         "keys": {"x": "x", "value": ["y"]},
                         "types": {"x": "area"},
                         "xFormat": '%Y-%m-%d %H:%M:%S',
                     },
                     "size": {
                         "height": 200
                     },
                     "axis": {
                         "x": {
                             "type": "timeseries",
                             "tick": {"format": "%H:%M"}
                         },
                     }
                 }},
                {"class": "Text",
                 "props": {"label": "Battery", "format": "{} %"},
                 "state": "battery"},
            ],
            "state": {"plotdata": plotdata}}


class ZHATemperature(ZHASensor):
    """Zigbee temperature sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('temperature', *args, **kwargs)
        self.discrete = False


class ZHAHumidity(ZHASensor):
    """Zigbee temperature sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('humidity', *args, **kwargs)
        self.discrete = False


class ZHAOpenClose(ZHASensor):
    """Zigbee window/door sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('contact', *args, **kwargs)


class ZHAPresence(ZHASensor):
    """Zigbee window/door sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('occupancy', *args, **kwargs)


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
        if 'click' in upd_state:
            self.event(upd_state['click'])
            await super().update_state({}, set_seen)
        else:
            await super().update_state(upd_state, set_seen)


class ZHALight(ZDevice):
    """Base ZHALight driver."""

    async def __init__(self, *args, **kwargs):
        await super().__init__(*args, **kwargs)
        self.zbstates += ['state', 'brightness']
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

    async def circle_brightness(self):
        LOGGER.error("Start dim: Not implemented")

    async def stop_circle_brightness(self):
        LOGGER.error("Stop dim: Not implemented")


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

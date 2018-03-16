from datetime import datetime, timedelta
from hearth.zigbee import Device as ZDevice

__all__ = ['ZHATemperature', 'ZHAHumidity', 'ZHAOpenClose', 'ZHAPresence', 'ZHASwitch', 'ZHALight', 'ZHALightCT']


class ZHASensor(ZDevice):
    """Temperature device."""

    async def __init__(self, mainstate, *args, **kwargs):
        """Init."""
        self.mainstate = mainstate
        self.divisor = 100
        await super().__init__(*args, **kwargs)

    def ui(self):
        """Return ui representation."""
        plotdata = []
        lasttime = str(datetime.now() - timedelta(hours=1)).split('.')[0]
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


class ZHAHumidity(ZHASensor):
    """Zigbee temperature sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('humidity', *args, **kwargs)


class ZHAOpenClose(ZHASensor):
    """Zigbee window/door sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('open', *args, **kwargs)
        self.divisor = 1


class ZHAPresence(ZHASensor):
    """Zigbee window/door sensor."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        await super().__init__('presence', *args, **kwargs)
        self.divisor = 1


class ZHASwitch(ZDevice):
    """ZHASwitch remote driver."""

    def ui(self):
        """Return ui representation."""
        return {"ui": [
            {"class": "Text",
             "props": {"label": "Battery", "format": "{} %"},
             "state": "battery"},
        ]}

    async def update_state(self, upd_state, set_seen=True):
        """Update state."""
        eventnames = {
            # big button
            1002: "toggle",
            1001: "toggle_hold",
            # top button
            2001: "up_move",
            2002: "up",
            2003: "up_stop",
            # bottom button
            3001: "down_move",
            3002: "down",
            3003: "down_stop",
            # left button
            4001: "left_move",
            4002: "left",
            4003: "left_stop",
            # right button
            5001: "right_move",
            5002: "right",
            5003: "right_stop",
        }
        if 'buttonevent' in upd_state:
            self.event(eventnames[upd_state['buttonevent']])
            await super().update_state({}, set_seen)
        else:
            await super().update_state(upd_state, set_seen)


class ZHALight(ZDevice):
    """Base ZHALight driver."""

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
        await self.set_state({'on': True})

    async def off(self):
        """Switch off."""
        await self.set_state({'on': False})

    async def toggle(self):
        """Toggle."""
        await (self.off() if self.state['on'] else self.on())

    async def brightness(self, bri, transisiontime=0):
        """Set brightness."""
        await self.set_state({'bri': min(max(0, bri), 255),
                              'transisiontime': transisiontime})

    async def dim_up(self, percent=10, transisiontime=0):
        """Dim up."""
        await self.brightness(
            self.state['bri'] + 255 * percent / 100, transisiontime)

    async def dim_down(self, percent=10, transisiontime=0):
        """Dim down."""
        await self.brightness(
            self.state['bri'] - 255 * percent / 100, transisiontime)


class ZHALightCT(ZHALight):
    """ZHALight light with controllable color temperature."""

    async def __init__(self, *args, **kwargs):
        """Init."""
        self.ctmin = 250
        self.ctmax = 454
        await super().__init__(*args, **kwargs)

    def ui(self):
        """Return ui representation."""
        uix = ZHALight.ui(self)
        uix['ui'].append(
            {"class": "Slider",
             "props": {"label": "Temperature",
                       "min": self.ctmin,
                       "max": self.ctmax,
                       "step": 1},
             "state": "ct"})
        return uix

    async def temperature(self, ct, transisiontime=0):
        """Set color temperature."""
        await self.set_state({'ct': min(max(self.ctmin, ct), self.ctmax),
                              'transisiontime': transisiontime})

    async def warmer(self, percent=10, transisiontime=0):
        """Warmer light color."""
        await self.temperature(self.state['ct'] + (self.ctmax - self.ctmin) * percent / 100,
                               transisiontime)

    async def colder(self, percent=10, transisiontime=0):
        """Colder light color."""
        await self.temperature(self.state['ct'] - (self.ctmax - self.ctmin) * percent / 100,
                               transisiontime)

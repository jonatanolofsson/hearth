from datetime import datetime, timedelta
from hearth.zigbee import Device as ZDevice

__all__ = ['ZHATemperature', 'ZHAHumidity', 'ZHAOpenClose', 'ZHAPresence']


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

import logging
from asyncinit import asyncinit
from datetime import datetime, timedelta

LOGGER = logging.getLogger(__name__)

@asyncinit
class Sensor:
    """Generic sensor with UI"""

    async def __init__(self, sensor_states, state_properties=None):
        """Init."""
        self.sensor_states = [sensor_states] if isinstance(sensor_states, str) else sensor_states
        self.divisor = 1.0
        self.discrete = False
        self.state_properties = state_properties or {}
        await self.init_state({sensorstate: False for sensorstate in self.sensor_states})

    def ui(self):
        """Return ui representation."""
        result = {
            "ui": [],
            "state": {}}
        for sensorstate in self.sensor_states:
            plotdata = []
            windowsize = self.state_properties.get(sensorstate, {}).get('windowsize', 1)
            discrete = self.state_properties.get(sensorstate, {}).get('discrete', self.discrete)
            lasttime = str(datetime.now() - timedelta(hours=windowsize)).split('.', maxsplit=1)[0]
            yname = sensorstate.capitalize()
            if discrete:
                t = tprev = str(datetime.now()).split('.')[0]
                sprev = self.state[sensorstate]
                lstart = (tprev, int(sprev))
                for t, s, in reversed(self.history):
                    t = t.partition('.')[0]
                    if sprev != s[sensorstate]:
                        plotdata.append({'x': lstart[0], yname: lstart[1]})
                        plotdata.append({'x': tprev, yname: lstart[1]})
                        lstart = (tprev, int(s[sensorstate]))
                    tprev = t
                    sprev = s[sensorstate]
                    if t < lasttime:
                        t = lasttime
                        break
                plotdata.append({'x': lstart[0], yname: lstart[1]})
                if t != tprev:
                    plotdata.append({'x': t, yname: lstart[1]})

                unique_values = sorted(list(set(p[yname] for p in plotdata)))
                if len(unique_values) >= 1 and unique_values[0] in (True, False):
                    unique_values = [False, True]
                plottype = 'area'
                tick = {
                    "formatstr": ".1",
                    "values": unique_values
                }
            else:
                plottype = 'spline'
                tick = {
                    "formatstr": ".2",
                    "count": 5
                }
                divisor = self.state_properties.get(sensorstate, {}).get('divisor', self.divisor)
                for t, s, in reversed(self.history):
                    if sensorstate not in s:
                        continue
                    t = t.partition('.')[0]
                    if t < lasttime:
                        break
                    plotdata.append({'x': t, yname: s[sensorstate] / divisor})
            plotdata.reverse()
            result["state"][f"plotdata_{sensorstate}"] = plotdata
            result["ui"].append(
                {"class": "C3Chart",
                 "state": f"plotdata_{sensorstate}",
                 "props": {
                     "data": {
                         "keys": {"x": "x", "value": [yname]},
                         "types": {"x": plottype},
                         # "xFormat": "%Y-%m-%d %H:%M:%S",
                         "xFormat": "%H:%M",
                     },
                     "size": {
                         "height": 200
                     },
                     "axis": {
                         "x": {
                             "type": "timeseries",
                             "tick": {"format": "%H:%M"},
                         },
                         "y": {
                             "label": self.state_properties.get(sensorstate, {}).get("ylabel"),
                             "tick": tick
                         }
                     }
                 }
                }
            )
        if "battery" in self.state:
            result["ui"].append(
                {"class": "Text",
                 "props": {"label": "Battery", "format": "{} %"},
                 "state": "battery"})
        return result



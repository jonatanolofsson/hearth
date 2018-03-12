"""Trådfri device driver."""
import logging
from hearth import zigbee

__all__ = ['Tradfri', 'TradfriTemperature', 'TradfriRemote']

LOGGER = logging.getLogger(__name__)


class Tradfri(zigbee.Device):
    """Base Trådfri driver."""

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
        LOGGER.info("Putting on light.")
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


class TradfriTemperature(Tradfri):
    """Trådfri light with controllable color temperature."""

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

    async def temperature(self, ct, transisiontime=0):
        """Set color temperature."""
        await self.set_state({'ct': min(max(250, ct), 454),
                              'transisiontime': transisiontime})

    async def warmer(self, percent=10, transisiontime=0):
        """Warmer light color."""
        await self.temperature(self.state['ct'] + 204 * percent / 100,
                               transisiontime)

    async def colder(self, percent=10, transisiontime=0):
        """Colder light color."""
        await self.temperature(self.state['ct'] - 204 * percent / 100,
                               transisiontime)


class TradfriRemote(zigbee.Device):
    """Trådfri remote driver."""
    def alerts(self):
        """List of active alerts."""
        active_alerts = super().alerts()
        if self.state['battery'] < 10:
            active_alerts.append(
                {"icon": "battery_alert",
                 "label": f"Low battery: {self.state['battery']} %",
                 "color": "#f44336"})
        return active_alerts

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

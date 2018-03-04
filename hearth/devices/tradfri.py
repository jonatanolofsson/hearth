"""Trådfri device driver."""
import logging
from hearth import zigbee

__all__ = ['Tradfri', 'TradfriTemperature']

LOGGER = logging.getLogger(__name__)


class Tradfri(zigbee.Device):
    """Base Trådfri driver."""

    async def __init__(self, id_, ieee):
        """Init."""
        await super().__init__(id_, f"{ieee}-01")

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
        await self.set_state({'on': True})

    async def off(self):
        """Switch off."""
        self.expect_refresh(5)
        await self.set_state({'on': False})

    async def toggle(self):
        """Toggle."""
        await (self.off() if self.state['on'] else self.on())

    async def brightness(self, bri, transisiontime=0):
        """Set brightness."""
        await self.set_state({'bri': bri, 'transisiontime': transisiontime})


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
        await self.set_state({'ct': ct, 'transisiontime': transisiontime})

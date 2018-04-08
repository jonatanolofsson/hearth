"""Room device classes."""
import asyncio
import logging
import hearth
from hearth import Device

__all__ = ['Room']

LOGGER = logging.getLogger(__name__)


class Room(Device):
    """Room."""

    async def __init__(self, id_, *devices, scenes=None):
        """Init."""
        await super().__init__(id_)
        self.primary_device = devices[0]
        self.devices = {device.id: device for device in devices}
        hearth.add_devices(*devices)
        self.scenes = scenes or ['default']
        await self.init_state({"scene": self.scenes[0]})
        await self.update_state({})

    async def off(self):
        """Shut everything down."""
        LOGGER.info("Shutting down %s", self.id)
        asyncio.gather(*[d.off() for d in self.devices.values()
                         if hasattr(d, 'off')])

    async def on(self):
        """Shut everything down."""
        LOGGER.info("Starting up %s", self.id)
        asyncio.gather(*[d.on() for d in self.devices.values()
                         if hasattr(d, 'on')])

    async def toggle(self):
        """Toggle room, following biglight."""
        LOGGER.debug("Toggle")
        await (self.off() if self.primary_device.state['on'] else self.on())

    async def set_state(self, upd_state):
        """Set new state."""
        if 'scene' in upd_state:
            if upd_state['scene'] not in self.scenes:
                upd_state['scene'] = self.scenes[0]
            LOGGER.debug("Setting scene: %s", upd_state['scene'])
        await self.update_state(upd_state)

    async def cycle_scene(self, step):
        """Cycle scene."""
        await self.set_state({'scene': self.scenes[
            (self.scenes.index(self.state['scene']) + step)
            % len(self.scenes)]})

    def ui(self):
        """UI."""
        return {"rightIcon": "all_out", "rightAction": "off",
                "ui": [
                    {"class": "FlatButton",
                     "props": {"label": "Off"},
                     "action": "off"},
                    {"class": "FlatButton",
                     "props": {"label": "On"},
                     "action": "on"}
                ] + ([
                    {"class": "SelectField",
                     "props": {"floatingLabelText": "Scene"},
                     "items": self.scenes,
                     "state": "scene"}
                ] if len(self.scenes) > 1 else [])
                + self.events_ui()}

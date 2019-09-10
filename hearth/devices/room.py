"""Room device classes."""
import asyncio
import logging
import hearth
from hearth import Device, D, tz

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
        await self.init_state({"scene": self.scenes[0], "automation": True})
        await self.update_state({})

    async def off(self):
        """Shut everything down."""
        LOGGER.debug("Shutting down %s", self.id)
        asyncio.gather(*[d.off() for d in self.devices.values()
                         if hasattr(d, 'off')])

    async def on(self):
        """Shut everything down."""
        LOGGER.debug("Starting up %s", self.id)
        asyncio.gather(*[d.on() for d in self.devices.values()
                         if hasattr(d, 'on')])

    def any(self, state='on', value=True, devices=None):
        """Return true if anything in the room is on."""
        devices = devices or self.devices.keys()
        for devname in devices:
            dev = D(devname)
            if state in dev.state and dev.state[state] == value:
                return True
        return False

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
                    {"class": "Button",
                     "props": {"label": "Off"},
                     "action": "off"},
                    {"class": "Button",
                     "props": {"label": "On"},
                     "action": "on"},
                    {"class": "Switch",
                     "props": {"label": "Automation"},
                     "state": "automation"}
                ] + ([
                    {"class": "Select",
                     "props": {"floatingLabelText": "Scene"},
                     "items": self.scenes,
                     "state": "scene"}
                ] if len(self.scenes) > 1 else [])
                + self.events_ui()}

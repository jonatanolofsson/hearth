"""Room device classes."""
import asyncio
import logging
import hearth
from hearth import Device, D, tz, call_later

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
        self.turn_off = None
        await self.init_state({"scene": self.scenes[0], "automation": True})
        await self.update_state({})

    async def update_state(self, upd_state, set_seen=True):
        """Update state."""
        await super().update_state(upd_state, set_seen)
        if 'automation' in upd_state:
            if not self.state['automation']:
                if self.turn_off:
                    self.turn_off.cancel()

    async def off(self):
        """Shut everything down."""
        asyncio.gather(*[d.off() for d in self.devices.values()
                         if hasattr(d, 'off')])

    async def on(self):
        """Shut everything down."""
        asyncio.gather(*[d.on() for d in self.devices.values()
                         if hasattr(d, 'on')])

    async def motion(self, value, old_value=None):
        """... enters the room."""
        if not self.state["automation"]:
            return
        if self.turn_off:
            self.turn_off.cancel()
        self.turn_off = call_later(self.timeout, self.no_motion)
        if value != old_value:
            await self.on()

    async def no_motion(self):
        """No motion for a while."""
        if not self.state["automation"]:
            return
        await self.off()

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
        await (self.off() if self.primary_device.is_on() else self.on())

    async def set_state(self, upd_state):
        """Set new state."""
        if 'scene' in upd_state:
            if upd_state['scene'] not in self.scenes:
                upd_state['scene'] = self.scenes[0]
            LOGGER.debug("Setting scene: %s", upd_state['scene'])
        await self.update_state(upd_state)

    async def set_scene(self, scene):
        """Set scene."""
        await self.set_state({'scene': scene})

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

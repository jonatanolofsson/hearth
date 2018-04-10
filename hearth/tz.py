"""Hearth timezone module."""
import sys
from datetime import timedelta, datetime, time
import astral
import pytz


class TZ:
    """Timezone functions."""
    def __init__(self):
        self.location = None

    def set_locale(self, name, region, lat, lon, tzname, elevation):
        """Set locale."""
        self.location = astral.Location((name, region, lat, lon, tzname, elevation))

    def daylight(self, when=None, delta=None):
        """Return true if time is within daylight hours

        (plus a timedelta in the morning, minus the same timedelta in the evening)."""
        when = when or self.now()
        delta = delta or timedelta(minutes=30)
        return self.sunrise(when) + delta < when < self.sunset(when) - delta

    def is_dark(self, when=None, delta=None):
        """Return true if time is within dark hours

        (plus a timedelta in the evening, minus the same timedelta in the morning)."""
        return not self.daylight(when, delta)

    def now(self):
        """Return localized time."""
        return self.localize(datetime.now())

    def time(self, *args, **kwargs):
        """Return time object."""
        return time(*args, **kwargs)

    def localize(self, time):
        """Localize to local time."""
        return pytz.timezone(self.location.timezone).localize(time)

    def __getattr__(self, attr):
        """Getattr"""
        return getattr(self.location, attr)


sys.modules[__name__] = TZ()

import sys
import astral


class TZ:
    """Timezone functions."""
    def __init__(self):
        self.location = None

    def set_locale(self, name, region, lat, lon, tzname, elevation):
        """Set locale."""
        self.location = astral.Location((name, region, lat, lon, tzname, elevation))

    def __getattr__(self, attr):
        """Getattr"""
        return getattr(self.location, attr)


sys.modules[__name__] = TZ()

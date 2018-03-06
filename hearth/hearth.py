# Copyright 2018 Jonatan Olofsson
"""Hearth core."""
import argparse
import asyncio
import glob
import os
import importlib.util
import logging
import re
import uvloop


asyncio.set_event_loop(uvloop.new_event_loop())
# asyncio.get_event_loop().set_debug(True)
logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

DEVICES = {}


def parse_args():
    """Parse args."""
    argparser = argparse.ArgumentParser()
    argparser.add_argument("directory", default=".", nargs="?")
    return argparser.parse_args()


def load_module(modname, modpath):
    """Load module from full path."""
    LOGGER.info("Loading module: %s: %s", modname, modpath)
    spec = importlib.util.spec_from_file_location(modname, modpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_module_name(modpath, directory):
    """Get module name from path."""
    relpath = os.path.relpath(modpath, directory)
    modname = re.sub(r"[\\/]", "", relpath)
    modname = os.path.splitext(modname)[0]
    return modname


def load_config_directory(directory):
    """Load all python files in the directory."""
    LOGGER.info("Loading config directory: %s", directory)
    conf_modules = {}
    for modpath in glob.glob(directory + "/*.py"):
        modname = get_module_name(modpath, directory)
        conf_modules[modname] = load_module(modname, modpath)
    return conf_modules


def add_devices(*devices):
    """Add devices."""
    new_devices = {}
    for device in devices:
        new_devices[device.id] = device
    DEVICES.update(new_devices)


def D(device):
    """Get device."""
    return DEVICES.get(device, False)


def main():
    """Main."""
    args = parse_args()
    load_config_directory(os.path.abspath(args.directory))
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        def shutdown_exception_handler(loop, context):
            """Exception handler."""
            if "exception" not in context \
                    or not isinstance(context["exception"],
                                      asyncio.CancelledError):
                loop.default_exception_handler(context)

        tasks = asyncio.gather(*asyncio.Task.all_tasks(loop=loop),
                               loop=loop, return_exceptions=True)
        tasks.add_done_callback(lambda t: loop.stop())
        tasks.cancel()

        loop.set_exception_handler(shutdown_exception_handler)
        while not tasks.done() and not loop.is_closed():
            asyncio.get_event_loop().run_forever()
        asyncio.get_event_loop().close()

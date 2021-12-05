# Copyright 2018 Jonatan Olofsson
"""Hearth core."""
import argparse
import asyncio
import functools
import glob
import os
import importlib.util
import inspect
import logging
import re
import signal
import schedule
import uvloop


asyncio.set_event_loop(uvloop.new_event_loop())
# asyncio.get_event_loop().set_debug(True)
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s %(name)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
LOGGER = logging.getLogger(__name__)


def call_at2(loop, when, callback, *args, **kwargs):
    """Call callback or coroutine later."""
    def _callback(*args2, **kwargs2):
        res = callback(*args2, **kwargs2)
        if inspect.isawaitable(res):
            asyncio.ensure_future(res)

    return loop.call_at_(when, _callback, *args, **kwargs)


def call_at(*args, **kwargs):
    """Call callback or coroutine later."""
    return call_at2(asyncio.get_event_loop(), *args, **kwargs)


def _call_at_mp(self, *args, **kwargs):
    """asyncio call_later monkey patch that works with coroutines."""
    return call_at2(self, *args, **kwargs)


def call_later2(loop, timeout, callback, *args, **kwargs):
    """Call callback or coroutine later."""
    def _callback(*args2, **kwargs2):
        res = callback(*args2, **kwargs2)
        if inspect.isawaitable(res):
            asyncio.ensure_future(res)

    return loop.call_later_(timeout, _callback, *args, **kwargs)


def call_later(*args, **kwargs):
    """Call callback or coroutine later."""
    return call_later2(asyncio.get_event_loop(), *args, **kwargs)


def _call_later_mp(self, *args, **kwargs):
    """asyncio call_later monkey patch that works with coroutines."""
    return call_later2(self, *args, **kwargs)


asyncio.get_event_loop().__class__.call_later_ = asyncio.get_event_loop().__class__.call_later
asyncio.get_event_loop().__class__.call_later = _call_later_mp
asyncio.get_event_loop().__class__.call_at_ = asyncio.get_event_loop().__class__.call_at
asyncio.get_event_loop().__class__.call_at = _call_at_mp

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
    DEVICES.update({d.id: d for d in devices})


async def wait_for(device):
    """Wait for device init."""
    while device not in DEVICES:
        await asyncio.sleep(1)


def D(device):  # pylint: disable=invalid-name
    """Get device."""
    return DEVICES.get(device, False)


def main():
    """Main."""
    args = parse_args()
    load_config_directory(os.path.abspath(args.directory))
    asyncio.ensure_future(schedule.run())
    loop = asyncio.get_event_loop()

    def ask_exit(signame):
        """Signal handler."""
        print("got signal %s: exit" % signame)
        print("Active tasks: ")
        for task in asyncio.Task.all_tasks():
            if not task.done():
                print(task)
        loop.stop()

    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, signame),
                                functools.partial(ask_exit, signame))

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
        asyncio.get_event_loop().run_until_complete(
            asyncio.gather(*[d.shutdown() for d in DEVICES.values()]))
        asyncio.get_event_loop().close()

if __name__ == '__main__':
    main()

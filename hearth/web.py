"""Hearth webserver"""
import os
import asyncio
import json
import logging
from sanic import Sanic, response
from . import hearth
from .hearth import D

LOGGER = logging.getLogger(__name__)
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(THIS_DIR)
WEBROOT = ROOT_DIR + '/www'


WEBAPP = Sanic(__name__)
WEBAPP.static("/static", WEBROOT)
SOCKETS = set()


@WEBAPP.route('/')
async def index(_):
    """Main page."""
    return await response.file(WEBROOT + '/index.html')


@WEBAPP.websocket('/ws')
async def wsocket(_, socket):
    """Websocket route."""
    global SOCKETS  # pylint: disable=global-statement
    SOCKETS.add(socket)
    try:
        while True:
            try:
                raw = await socket.recv()
                data = json.loads(raw)
                if 'id' not in data:
                    LOGGER.warning("Recipient not specified: %s", data)
                    continue
                device = D(data['id'])
                if not device:
                    LOGGER.warning("No such recipient: '%s'", data['id'])
                    continue
                await device.webhandler(data, socket)
            except KeyError as error:
                LOGGER.warning("Key not found: %s", error)
            except json.JSONDecodeError as error:
                LOGGER.warning("Invalid JSON data received: '%s' :: %s",
                               raw, error)
    finally:
        SOCKETS.remove(socket)


def broadcast(payload):
    """Send data to all websocket listeners."""
    asyncio.ensure_future(asyncio.gather(*[s.send(payload) for s in SOCKETS]))


def serve(host="0.0.0.0", port=8080):
    """Start webserver."""
    asyncio.ensure_future(WEBAPP.create_server(host=host, port=port))

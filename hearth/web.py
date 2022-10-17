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


WEBSERVER = None
WEBAPP = Sanic(__name__)
WEBAPP.static("/static", WEBROOT)
SOCKETS = set()


@WEBAPP.route('/')
async def index(_):
    """Main page."""
    return await response.file(WEBROOT + '/index.html')


@WEBAPP.route('/a/<device:string>/<method:string>')
async def action(request, device='', method=''):
    """Main page."""
    data = {
        "id": device if device != "0" else 0,
        "m": method,
        "args": request.args.getlist("args", [])
    }
    device = D(data['id'])
    if not device:
        LOGGER.warning("No such recipient: '%s'", data['id'])
        return response.json({"error": "No such recipient", "data": data}, status=404)

    await device.webhandler(data, None)
    return response.json(data)


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

async def aserve(host="0.0.0.0", port=80):
    """Start webserver."""
    global WEBSERVER
    WEBSERVER = await WEBAPP.create_server(host=host, port=port, return_asyncio_server=True)
    await WEBSERVER.startup()

def serve(host="0.0.0.0", port=80):
    """Start webserver."""
    asyncio.ensure_future(aserve())
    for key in logging.Logger.manager.loggerDict:
        if key.startswith("websockets") or key.startswith("sanic"):
            logging.getLogger(key).setLevel(logging.WARNING)

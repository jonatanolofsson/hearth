"""MQTT Client class."""
import asyncio
import logging
import json
from asyncinit import asyncinit
from hbmqtt.client import MQTTClient

LOGGER = logging.getLogger(__name__)

SERVER = None


@asyncinit
class ServerConnection:
    """MQTT Client."""

    async def __init__(self, uri="mqtt://localhost:1883"):
        if "://" not in uri:
            uri = "mqtt://" + uri
        self.uri = uri
        self.subscriptions = {}
        self.mqtt = MQTTClient(config={"auto_reconnect": False})
        for key in logging.Logger.manager.loggerDict:
            if key.startswith("hbmqtt"):
                logging.getLogger(key).setLevel(logging.WARNING)
        await self.mqtt.connect(self.uri)
        asyncio.ensure_future(self._loop())

    async def _loop(self):
        """Connection handling loop."""
        while True:
            try:
                if self.subscriptions:
                    await self.mqtt.subscribe(
                        [(t, qos)
                         for t, (_, qos) in self.subscriptions.items()])
                while True:
                    message = await self.mqtt.deliver_message()
                    topic = message.publish_packet.variable_header.topic_name
                    payload = message.publish_packet.payload.data.decode()
                    callback = self.subscriptions.get(
                        topic, (self.message_handler,))[0]
                    asyncio.ensure_future(callback(topic, payload))
            except KeyboardInterrupt:
                break
            except asyncio.CancelledError:
                break
            finally:
                await self.mqtt.disconnect()
            await asyncio.sleep(1)
            await self.mqtt.reconnect()

    async def pub(self, topic, payload, qos=0):
        """Publish message on topic."""
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        asyncio.ensure_future(self.mqtt.publish(topic, payload.encode(), qos))

    async def sub(self, topic, callback, qos=0):
        """Subscribe to topic with callback."""
        self.subscriptions[topic] = (callback, qos)
        await self.mqtt.subscribe([(topic, qos)])
        LOGGER.info("Subscribed to topic %s", topic)

    async def message_handler(self, topic, payload):
        """Default message handler."""
        LOGGER.info("Message on unknown topic: %s : {%s}", topic, payload)


async def server():
    """Get server object."""
    while SERVER is None:
        await asyncio.sleep(0.2)
    return SERVER


def connect(*args, **kwargs):
    """Connect to MQTT server."""
    async def astart(*args, **kwargs):
        """Async start server."""
        global SERVER  # pylint: disable=global-statement
        SERVER = await ServerConnection(*args, **kwargs)
    asyncio.ensure_future(astart(*args, **kwargs))

"""MQTT Client class."""
import asyncio
import logging
from hbmqtt.client import MQTTClient

LOGGER = logging.getLogger(__name__)

client = None


class Client:
    """MQTT Client."""

    def __init__(self, uri="mqtt://localhost:1883"):
        if "://" not in uri:
            uri = "mqtt://" + uri
        self.uri = uri
        self.subscriptions = {}
        self.mqtt = MQTTClient(config={"auto_reconnect": False})
        self._loop_future = self._loop()
        asyncio.ensure_future(self._loop_future)

    async def _loop(self):
        """Connection handling loop."""
        await self.mqtt.connect(self.uri)
        while True:
            try:
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
        asyncio.ensure_future(self.mqtt.publish(topic, payload.encode(), qos))

    async def sub(self, topic, callback, qos=0):
        """Subscribe to topic with callback."""
        self.subscriptions[topic] = (callback, qos)
        await self.mqtt.subscribe([(topic, qos)])
        LOGGER.info("Subscribed to topic %s", topic)

    async def message_handler(self, topic, payload):
        """Default message handler."""
        LOGGER.info("Message on unknown topic: %s : {%s}", topic, payload)


def connect(uri="localhost:1883"):
    """Connect to MQTT server."""
    global client
    client = Client(uri)

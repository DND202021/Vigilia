"""Vigilia MQTT client service for IoT device communication.

This service provides async MQTT connectivity to the Mosquitto broker
for subscribing to device topics and publishing config messages.
Separate from FundamentumMQTTClient which handles legacy alert integration.
"""

import asyncio
import json
from typing import Any, Callable, Awaitable

import aiomqtt
import structlog

from app.services.mqtt_handlers.registration_handler import handle_device_registration
from app.services.mqtt_handlers.telemetry_handler import handle_device_telemetry
from app.services.mqtt_handlers.config_reported_handler import handle_device_config_reported

logger = structlog.get_logger()

# Type for async message handlers
MessageHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


class VigiliaMQTTService:
    """Async MQTT client for Vigilia IoT platform."""

    DEFAULT_SUBSCRIPTIONS = [
        "agency/+/device/+/telemetry",
        "agency/+/device/+/config/reported",
        "agency/+/device/+/register",
    ]

    def __init__(
        self,
        broker_host: str,
        broker_port: int = 8883,
        ca_cert_path: str = "/mosquitto/certs/ca.crt",
        client_cert_path: str = "/mosquitto/certs/internal-client.crt",
        client_key_path: str = "/mosquitto/certs/internal-client.key",
        client_id: str = "vigilia-backend",
        reconnect_interval: int = 5,
        max_reconnect_interval: int = 60,
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.ca_cert_path = ca_cert_path
        self.client_cert_path = client_cert_path
        self.client_key_path = client_key_path
        self.client_id = client_id
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_interval = max_reconnect_interval

        self._client: aiomqtt.Client | None = None
        self._listener_task: asyncio.Task | None = None
        self._message_handlers: dict[str, MessageHandler] = {}
        self._connected: bool = False
        self._additional_subscriptions: list[str] = []

        # Register default handlers
        self.register_default_handlers()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def register_handler(self, topic_pattern: str, handler: MessageHandler) -> None:
        self._message_handlers[topic_pattern] = handler
        logger.info("Registered MQTT handler", topic_pattern=topic_pattern)

    def register_default_handlers(self) -> None:
        """Register built-in MQTT message handlers.

        Default handlers:
        - Registration handler: Auto-activates devices on first MQTT connection
        """
        self.register_handler("agency/+/device/+/register", handle_device_registration)
        self.register_handler("agency/+/device/+/telemetry", handle_device_telemetry)
        self.register_handler("agency/+/device/+/config/reported", handle_device_config_reported)

    def add_subscription(self, topic: str) -> None:
        if topic not in self._additional_subscriptions:
            self._additional_subscriptions.append(topic)

    async def start(self) -> None:
        logger.info("Starting Vigilia MQTT service", broker=self.broker_host, port=self.broker_port)
        self._listener_task = asyncio.create_task(self._listen_loop(), name="vigilia-mqtt-listener")

    async def stop(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        self._connected = False
        logger.info("Vigilia MQTT service stopped")

    async def publish(self, topic: str, payload: dict[str, Any], qos: int = 1, retain: bool = False) -> None:
        if not self._client:
            raise RuntimeError("MQTT client not connected")
        payload_json = json.dumps(payload)
        await self._client.publish(topic, payload_json, qos=qos, retain=retain)
        logger.debug("Published MQTT message", topic=topic, qos=qos)

    async def _listen_loop(self) -> None:
        """Main connection loop with exponential backoff reconnection."""
        interval = self.reconnect_interval
        while True:
            try:
                tls_params = aiomqtt.TLSParameters(
                    ca_certs=self.ca_cert_path,
                    certfile=self.client_cert_path,
                    keyfile=self.client_key_path,
                )
                async with aiomqtt.Client(
                    hostname=self.broker_host,
                    port=self.broker_port,
                    tls_params=tls_params,
                    identifier=self.client_id,
                ) as client:
                    self._client = client
                    self._connected = True
                    interval = self.reconnect_interval  # Reset on success
                    logger.info("Connected to MQTT broker", broker=self.broker_host, port=self.broker_port)

                    all_topics = self.DEFAULT_SUBSCRIPTIONS + self._additional_subscriptions
                    for topic in all_topics:
                        await client.subscribe(topic, qos=1)
                        logger.info("Subscribed to MQTT topic", topic=topic)

                    async for message in client.messages:
                        await self._dispatch_message(message)

            except aiomqtt.MqttError as e:
                self._connected = False
                self._client = None
                logger.warning("MQTT connection lost, reconnecting", error=str(e), retry_in=interval)
                await asyncio.sleep(interval)
                interval = min(interval * 2, self.max_reconnect_interval)
            except asyncio.CancelledError:
                self._connected = False
                self._client = None
                logger.info("MQTT listener task cancelled")
                raise
            except Exception as e:
                self._connected = False
                self._client = None
                logger.error("Unexpected MQTT error, reconnecting", error=str(e), retry_in=interval)
                await asyncio.sleep(interval)
                interval = min(interval * 2, self.max_reconnect_interval)

    async def _dispatch_message(self, message: aiomqtt.Message) -> None:
        topic_str = str(message.topic)
        try:
            payload = json.loads(message.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning("Invalid MQTT message payload", topic=topic_str, error=str(e))
            return

        logger.debug("Received MQTT message", topic=topic_str)
        matched = False
        for pattern, handler in self._message_handlers.items():
            if self._topic_matches(topic_str, pattern):
                try:
                    await handler(topic_str, payload)
                    matched = True
                except Exception as e:
                    logger.error("MQTT handler error", topic=topic_str, pattern=pattern, error=str(e))
                break

        if not matched:
            logger.debug("No handler for MQTT topic", topic=topic_str)

    @staticmethod
    def _topic_matches(topic: str, pattern: str) -> bool:
        topic_parts = topic.split("/")
        pattern_parts = pattern.split("/")
        for i, pat in enumerate(pattern_parts):
            if pat == "#":
                return True
            if i >= len(topic_parts):
                return False
            if pat != "+" and pat != topic_parts[i]:
                return False
        return len(topic_parts) == len(pattern_parts)

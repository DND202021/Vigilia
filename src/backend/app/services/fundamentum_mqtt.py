"""Fundamentum MQTT client for IoT sensor integration.

This service connects to the Fundamentum MQTT broker to receive
real-time alerts from IoT sensors (motion, smoke, glass break, etc.)
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

import paho.mqtt.client as mqtt
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.alert import Alert, AlertSource, AlertSeverity, AlertStatus
from app.services.socketio import emit_alert_created

logger = structlog.get_logger()


# Alert type to severity mapping
ALERT_SEVERITY_MAP = {
    "smoke_detected": AlertSeverity.CRITICAL,
    "fire_detected": AlertSeverity.CRITICAL,
    "glass_break": AlertSeverity.HIGH,
    "motion_detected": AlertSeverity.MEDIUM,
    "door_opened": AlertSeverity.LOW,
    "temperature_alert": AlertSeverity.HIGH,
    "intrusion_detected": AlertSeverity.CRITICAL,
    "panic_button": AlertSeverity.CRITICAL,
    "water_leak": AlertSeverity.HIGH,
    "power_failure": AlertSeverity.MEDIUM,
    "battery_low": AlertSeverity.LOW,
    "device_offline": AlertSeverity.INFO,
    "device_online": AlertSeverity.INFO,
}


class FundamentumMQTTClient:
    """MQTT client for receiving alerts from Fundamentum IoT platform."""

    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        username: str | None = None,
        password: str | None = None,
        topic_prefix: str = "fundamentum/alerts",
        client_id: str | None = None,
    ):
        """Initialize MQTT client.

        Args:
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            username: Optional username for authentication
            password: Optional password for authentication
            topic_prefix: Base topic to subscribe to
            client_id: Client ID for MQTT connection
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix
        self.client_id = client_id or f"vigilia-{uuid.uuid4().hex[:8]}"

        self._client: mqtt.Client | None = None
        self._connected = False
        self._db_session_factory: Callable[[], AsyncSession] | None = None
        self._event_loop: asyncio.AbstractEventLoop | None = None

    def set_db_session_factory(self, factory: Callable[[], AsyncSession]) -> None:
        """Set the database session factory for creating sessions."""
        self._db_session_factory = factory

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict,
        rc: int,
    ) -> None:
        """Handle MQTT connection."""
        if rc == 0:
            self._connected = True
            logger.info(
                "Connected to Fundamentum MQTT broker",
                broker=self.broker_host,
                port=self.broker_port,
            )
            # Subscribe to all alert topics
            topic = f"{self.topic_prefix}/#"
            client.subscribe(topic)
            logger.info("Subscribed to topic", topic=topic)
        else:
            logger.error("Failed to connect to MQTT broker", rc=rc)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        rc: int,
    ) -> None:
        """Handle MQTT disconnection."""
        self._connected = False
        if rc != 0:
            logger.warning("Unexpected MQTT disconnection", rc=rc)
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        """Handle incoming MQTT message."""
        try:
            topic = message.topic
            payload = json.loads(message.payload.decode("utf-8"))

            logger.debug("Received MQTT message", topic=topic, payload=payload)

            # Schedule async processing
            if self._event_loop:
                asyncio.run_coroutine_threadsafe(
                    self._process_alert(topic, payload),
                    self._event_loop,
                )
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in MQTT message", error=str(e))
        except Exception as e:
            logger.error("Error processing MQTT message", error=str(e))

    async def _process_alert(self, topic: str, payload: dict) -> None:
        """Process incoming alert from Fundamentum.

        Expected payload format:
        {
            "device_id": "sensor_001",
            "alert_type": "motion_detected",
            "timestamp": "2025-01-11T10:30:00Z",
            "location": {
                "latitude": 45.5017,
                "longitude": -73.5673,
                "address": "123 Main St",
                "zone": "Zone A"
            },
            "details": {
                "confidence": 0.95,
                "sensor_type": "pir"
            }
        }
        """
        if not self._db_session_factory:
            logger.error("No database session factory configured")
            return

        try:
            async with self._db_session_factory() as db:
                # Extract alert information
                device_id = payload.get("device_id", "unknown")
                alert_type = payload.get("alert_type", "unknown_alert")
                timestamp_str = payload.get("timestamp")
                location = payload.get("location", {})
                details = payload.get("details", {})

                # Parse timestamp
                if timestamp_str:
                    received_at = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                else:
                    received_at = datetime.now(timezone.utc)

                # Determine severity
                severity = ALERT_SEVERITY_MAP.get(
                    alert_type, AlertSeverity.MEDIUM
                )

                # Create alert title
                title = self._generate_alert_title(alert_type, device_id)

                # Create alert in database
                alert = Alert(
                    id=uuid.uuid4(),
                    source=AlertSource.FUNDAMENTUM,
                    source_id=f"fundamentum:{device_id}:{payload.get('alert_id', uuid.uuid4().hex[:8])}",
                    source_device_id=device_id,
                    severity=severity,
                    status=AlertStatus.PENDING,
                    alert_type=alert_type,
                    title=title,
                    description=payload.get("description"),
                    latitude=location.get("latitude"),
                    longitude=location.get("longitude"),
                    address=location.get("address"),
                    zone=location.get("zone"),
                    raw_payload=payload,
                    received_at=received_at,
                )

                db.add(alert)
                await db.commit()
                await db.refresh(alert)

                logger.info(
                    "Created alert from Fundamentum",
                    alert_id=str(alert.id),
                    alert_type=alert_type,
                    device_id=device_id,
                )

                # Emit real-time notification
                await emit_alert_created({
                    "id": str(alert.id),
                    "source": alert.source.value,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "alert_type": alert.alert_type,
                    "title": alert.title,
                    "created_at": alert.created_at.isoformat(),
                })

        except Exception as e:
            logger.error("Failed to process Fundamentum alert", error=str(e))

    def _generate_alert_title(self, alert_type: str, device_id: str) -> str:
        """Generate human-readable alert title."""
        type_titles = {
            "smoke_detected": "Smoke Detected",
            "fire_detected": "Fire Detected",
            "glass_break": "Glass Break Detected",
            "motion_detected": "Motion Detected",
            "door_opened": "Door Opened",
            "temperature_alert": "Temperature Alert",
            "intrusion_detected": "Intrusion Detected",
            "panic_button": "Panic Button Activated",
            "water_leak": "Water Leak Detected",
            "power_failure": "Power Failure",
            "battery_low": "Low Battery Warning",
            "device_offline": "Device Offline",
            "device_online": "Device Online",
        }
        title = type_titles.get(alert_type, alert_type.replace("_", " ").title())
        return f"{title} - {device_id}"

    def connect(self, event_loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Connect to the MQTT broker."""
        self._event_loop = event_loop or asyncio.get_event_loop()

        self._client = mqtt.Client(client_id=self.client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        if self.username and self.password:
            self._client.username_pw_set(self.username, self.password)

        try:
            self._client.connect(self.broker_host, self.broker_port, keepalive=60)
            self._client.loop_start()
            logger.info(
                "MQTT client started",
                broker=self.broker_host,
                port=self.broker_port,
            )
        except Exception as e:
            logger.error("Failed to connect to MQTT broker", error=str(e))
            raise

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            self._connected = False
            logger.info("MQTT client disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    def publish(self, topic: str, payload: dict) -> None:
        """Publish a message to a topic."""
        if not self._client or not self._connected:
            logger.warning("Cannot publish: MQTT client not connected")
            return

        self._client.publish(
            f"{self.topic_prefix}/{topic}",
            json.dumps(payload),
        )


# Global client instance
_mqtt_client: FundamentumMQTTClient | None = None


def get_mqtt_client() -> FundamentumMQTTClient | None:
    """Get the global MQTT client instance."""
    return _mqtt_client


def init_mqtt_client(
    db_session_factory: Callable[[], AsyncSession],
    event_loop: asyncio.AbstractEventLoop | None = None,
) -> FundamentumMQTTClient | None:
    """Initialize and start the MQTT client.

    Returns None if MQTT is not configured.
    """
    global _mqtt_client

    # Check if MQTT is configured
    if not hasattr(settings, "mqtt_broker_host") or not settings.mqtt_broker_host:
        logger.info("MQTT not configured, skipping Fundamentum integration")
        return None

    _mqtt_client = FundamentumMQTTClient(
        broker_host=settings.mqtt_broker_host,
        broker_port=getattr(settings, "mqtt_broker_port", 1883),
        username=getattr(settings, "mqtt_username", None),
        password=getattr(settings, "mqtt_password", None),
        topic_prefix=getattr(settings, "mqtt_topic_prefix", "fundamentum/alerts"),
    )

    _mqtt_client.set_db_session_factory(db_session_factory)
    _mqtt_client.connect(event_loop)

    return _mqtt_client


def shutdown_mqtt_client() -> None:
    """Shutdown the MQTT client."""
    global _mqtt_client

    if _mqtt_client:
        _mqtt_client.disconnect()
        _mqtt_client = None

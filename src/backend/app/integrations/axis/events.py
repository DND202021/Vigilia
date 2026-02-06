"""Axis audio event handling."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Awaitable, Any
import asyncio
import logging
import defusedxml.ElementTree as ET

from app.integrations.axis.client import AxisDeviceClient, AxisDeviceInfo


logger = logging.getLogger(__name__)


class AudioEventType(str, Enum):
    """Types of audio events detected by Axis analytics."""
    GUNSHOT = "gunshot"
    GLASS_BREAK = "glass_break"
    AGGRESSION = "aggression"
    SCREAM = "scream"
    EXPLOSION = "explosion"
    CAR_ALARM = "car_alarm"
    UNKNOWN = "unknown"


@dataclass
class AxisAudioEvent:
    """Audio event from Axis device."""
    device_id: str
    device_name: str
    event_type: AudioEventType
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    location: tuple[float, float] | None = None  # (lat, lon)
    location_name: str | None = None
    audio_clip_url: str | None = None
    raw_event: dict[str, Any] = field(default_factory=dict)


# Type alias for event handlers
EventHandler = Callable[[AxisAudioEvent], Awaitable[None]]


class AxisEventSubscriber:
    """
    Subscribes to real-time events from Axis devices.

    Uses HTTP long-polling for event subscription since ONVIF
    requires additional complexity.
    """

    def __init__(
        self,
        devices: list[AxisDeviceClient],
        poll_interval: float = 1.0,
    ):
        self.devices = devices
        self.poll_interval = poll_interval
        self._handlers: list[EventHandler] = []
        self._running = False
        self._tasks: list[asyncio.Task] = []

    def on_event(self, handler: EventHandler):
        """
        Register event handler callback.

        Args:
            handler: Async function to call with each event
        """
        self._handlers.append(handler)

    async def start(self):
        """Start listening for events from all devices."""
        if self._running:
            return

        self._running = True
        logger.info(f"Starting event subscription for {len(self.devices)} devices")

        for device in self.devices:
            task = asyncio.create_task(
                self._poll_device(device),
                name=f"axis_poll_{device.device_ip}"
            )
            self._tasks.append(task)

    async def stop(self):
        """Stop listening for events."""
        self._running = False

        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()
        logger.info("Event subscription stopped")

    async def _poll_device(self, device: AxisDeviceClient):
        """Poll a single device for events."""
        while self._running:
            try:
                events = await self._fetch_events(device)
                for event in events:
                    await self._dispatch_event(event)

                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error polling device {device.device_ip}: {e}")
                await asyncio.sleep(5)  # Wait before retry

    async def _fetch_events(self, device: AxisDeviceClient) -> list[AxisAudioEvent]:
        """
        Fetch audio analytics events from device.

        Uses Axis event API to get recent audio events.
        """
        if not device._session:
            return []

        url = f"{device.base_url}/axis-cgi/eventlist.cgi"
        params = {
            "format": "xml",
            "event": "AudioAnalytics",
        }

        try:
            async with device._session.get(url, params=params) as response:
                if response.status != 200:
                    return []

                xml_text = await response.text()
                return self._parse_events(xml_text, device)

        except Exception as e:
            logger.debug(f"Error fetching events: {e}")
            return []

    def _parse_events(
        self,
        xml_text: str,
        device: AxisDeviceClient,
    ) -> list[AxisAudioEvent]:
        """Parse XML event response."""
        events = []

        try:
            root = ET.fromstring(xml_text)

            for event_elem in root.findall(".//event"):
                event_type_str = event_elem.findtext("type", "")
                confidence_str = event_elem.findtext("confidence", "0")
                timestamp_str = event_elem.findtext("timestamp", "")

                # Map event type
                event_type = self._map_event_type(event_type_str)
                if event_type == AudioEventType.UNKNOWN:
                    continue

                # Parse confidence
                try:
                    confidence = float(confidence_str) / 100.0
                except ValueError:
                    confidence = 0.5

                # Parse timestamp
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except ValueError:
                    timestamp = datetime.now(timezone.utc)

                device_info = device.device_info
                event = AxisAudioEvent(
                    device_id=device_info.device_id if device_info else device.device_ip,
                    device_name=device_info.name if device_info else device.device_ip,
                    event_type=event_type,
                    confidence=confidence,
                    timestamp=timestamp,
                    location=device.device_location,
                    location_name=device.location_name,
                    raw_event={
                        "type": event_type_str,
                        "confidence": confidence_str,
                        "timestamp": timestamp_str,
                    },
                )
                events.append(event)

        except ET.ParseError as e:
            logger.debug(f"Failed to parse event XML: {e}")

        return events

    def _map_event_type(self, event_type_str: str) -> AudioEventType:
        """Map Axis event type string to AudioEventType."""
        type_map = {
            "gunshot": AudioEventType.GUNSHOT,
            "gunshotdetection": AudioEventType.GUNSHOT,
            "glassbreak": AudioEventType.GLASS_BREAK,
            "glassbreaking": AudioEventType.GLASS_BREAK,
            "aggression": AudioEventType.AGGRESSION,
            "aggressionsound": AudioEventType.AGGRESSION,
            "scream": AudioEventType.SCREAM,
            "screaming": AudioEventType.SCREAM,
            "explosion": AudioEventType.EXPLOSION,
            "caralarm": AudioEventType.CAR_ALARM,
        }

        normalized = event_type_str.lower().replace("_", "").replace("-", "")
        return type_map.get(normalized, AudioEventType.UNKNOWN)

    async def _dispatch_event(self, event: AxisAudioEvent):
        """Dispatch event to all registered handlers."""
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")


class MockAxisEventGenerator:
    """
    Mock event generator for testing without real devices.

    Generates simulated audio events for development and testing.
    """

    def __init__(
        self,
        device_id: str = "mock-device-001",
        device_name: str = "Mock Audio Device",
        location: tuple[float, float] | None = None,
    ):
        self.device_id = device_id
        self.device_name = device_name
        self.location = location or (45.5017, -73.5673)
        self._handlers: list[EventHandler] = []
        self._running = False
        self._task: asyncio.Task | None = None

    def on_event(self, handler: EventHandler):
        """Register event handler."""
        self._handlers.append(handler)

    async def start(self, interval: float = 30.0):
        """Start generating mock events."""
        self._running = True
        self._task = asyncio.create_task(self._generate_loop(interval))

    async def stop(self):
        """Stop generating events."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def generate_event(
        self,
        event_type: AudioEventType,
        confidence: float = 0.85,
    ) -> AxisAudioEvent:
        """Generate a single mock event."""
        event = AxisAudioEvent(
            device_id=self.device_id,
            device_name=self.device_name,
            event_type=event_type,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc),
            location=self.location,
            location_name="Test Location",
        )

        for handler in self._handlers:
            await handler(event)

        return event

    async def _generate_loop(self, interval: float):
        """Generate random events periodically."""
        import random

        event_types = list(AudioEventType)
        event_types.remove(AudioEventType.UNKNOWN)

        while self._running:
            try:
                await asyncio.sleep(interval)

                event_type = random.choice(event_types)
                confidence = random.uniform(0.6, 0.99)

                await self.generate_event(event_type, confidence)

            except asyncio.CancelledError:
                break

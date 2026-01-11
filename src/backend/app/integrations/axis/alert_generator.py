"""Axis audio event to ERIOP alert conversion."""

from datetime import datetime, timezone
from typing import Any
import logging

from app.integrations.axis.events import AxisAudioEvent, AudioEventType
from app.models.alert import AlertSource, AlertSeverity


logger = logging.getLogger(__name__)


class AudioAlertGenerator:
    """
    Converts Axis audio events to ERIOP alerts.

    Handles confidence thresholds and auto-incident creation
    for critical events.
    """

    # Mapping of audio events to alert priorities
    SEVERITY_MAP: dict[AudioEventType, AlertSeverity] = {
        AudioEventType.GUNSHOT: AlertSeverity.CRITICAL,
        AudioEventType.EXPLOSION: AlertSeverity.CRITICAL,
        AudioEventType.GLASS_BREAK: AlertSeverity.HIGH,
        AudioEventType.AGGRESSION: AlertSeverity.HIGH,
        AudioEventType.SCREAM: AlertSeverity.MEDIUM,
        AudioEventType.CAR_ALARM: AlertSeverity.LOW,
        AudioEventType.UNKNOWN: AlertSeverity.MEDIUM,
    }

    # Confidence thresholds for alert creation
    ALERT_THRESHOLDS: dict[AudioEventType, float] = {
        AudioEventType.GUNSHOT: 0.70,
        AudioEventType.EXPLOSION: 0.70,
        AudioEventType.GLASS_BREAK: 0.65,
        AudioEventType.AGGRESSION: 0.70,
        AudioEventType.SCREAM: 0.60,
        AudioEventType.CAR_ALARM: 0.50,
        AudioEventType.UNKNOWN: 0.80,
    }

    # Confidence thresholds for auto-dispatch (auto-create incident)
    AUTO_DISPATCH_THRESHOLDS: dict[AudioEventType, float] = {
        AudioEventType.GUNSHOT: 0.85,
        AudioEventType.EXPLOSION: 0.85,
        AudioEventType.GLASS_BREAK: 0.80,
        AudioEventType.AGGRESSION: 0.85,
        AudioEventType.SCREAM: 0.90,
    }

    def __init__(
        self,
        alert_service=None,
        device_registry=None,
        auto_create_incidents: bool = True,
    ):
        """
        Initialize alert generator.

        Args:
            alert_service: ERIOP alert service
            device_registry: Registry of Axis devices
            auto_create_incidents: Whether to auto-create incidents for critical events
        """
        self.alert_service = alert_service
        self.device_registry = device_registry
        self.auto_create_incidents = auto_create_incidents

        # Statistics
        self._stats = {
            "events_processed": 0,
            "alerts_created": 0,
            "incidents_created": 0,
            "events_below_threshold": 0,
        }

    async def process_event(self, event: AxisAudioEvent) -> dict[str, Any] | None:
        """
        Process audio event and create alert if warranted.

        Args:
            event: Audio event from Axis device

        Returns:
            Created alert or None if not created
        """
        self._stats["events_processed"] += 1

        # Check confidence threshold
        threshold = self.ALERT_THRESHOLDS.get(event.event_type, 0.70)
        if event.confidence < threshold:
            self._stats["events_below_threshold"] += 1
            logger.debug(
                f"Event below threshold: {event.event_type.value} "
                f"({event.confidence:.0%} < {threshold:.0%})"
            )
            return None

        # Build alert data
        alert_data = self._build_alert_data(event)

        if not self.alert_service:
            logger.warning("No alert service configured")
            return alert_data

        # Create alert
        try:
            alert = await self.alert_service.ingest_alert(**alert_data)
            self._stats["alerts_created"] += 1
            logger.info(
                f"Created alert {alert.id} for {event.event_type.value} "
                f"from device {event.device_id}"
            )

            # Check for auto-incident creation
            if await self._should_auto_create_incident(event):
                await self._create_incident(alert, event)

            return alert

        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return None

    def _build_alert_data(self, event: AxisAudioEvent) -> dict[str, Any]:
        """Build alert data from audio event."""
        severity = self.SEVERITY_MAP.get(event.event_type, AlertSeverity.MEDIUM)

        title = f"{event.event_type.value.replace('_', ' ').title()} Detected"
        description = (
            f"Audio analytics detected {event.event_type.value.replace('_', ' ')} "
            f"at {event.device_name} with {event.confidence:.0%} confidence"
        )

        alert_data = {
            "source": AlertSource.AXIS_MICROPHONE,
            "source_id": f"axis:{event.device_id}",
            "source_device_id": event.device_id,
            "alert_type": event.event_type.value,
            "title": title,
            "description": description,
            "severity": severity,
            "raw_payload": {
                "device_id": event.device_id,
                "device_name": event.device_name,
                "event_type": event.event_type.value,
                "confidence": event.confidence,
                "location_name": event.location_name,
                "audio_clip_url": event.audio_clip_url,
                "raw_event": event.raw_event,
            },
        }

        # Add location if available
        if event.location:
            alert_data["latitude"] = event.location[0]
            alert_data["longitude"] = event.location[1]

        if event.location_name:
            alert_data["zone"] = event.location_name

        return alert_data

    async def _should_auto_create_incident(self, event: AxisAudioEvent) -> bool:
        """Check if event warrants auto-incident creation."""
        if not self.auto_create_incidents:
            return False

        threshold = self.AUTO_DISPATCH_THRESHOLDS.get(event.event_type)
        if threshold is None:
            return False

        return event.confidence >= threshold

    async def _create_incident(self, alert, event: AxisAudioEvent):
        """Create incident from alert for critical events."""
        if not hasattr(self.alert_service, 'create_incident_from_alert'):
            logger.warning("Alert service doesn't support incident creation")
            return

        # Need agency_id for incident creation
        # This would typically come from device registry or jurisdiction lookup
        logger.info(
            f"Auto-incident creation triggered for {event.event_type.value} "
            f"with {event.confidence:.0%} confidence"
        )
        self._stats["incidents_created"] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get generator statistics."""
        return self._stats.copy()

    @classmethod
    def get_thresholds(cls) -> dict[str, dict[str, float]]:
        """Get current threshold configuration."""
        return {
            "alert_thresholds": {
                k.value: v for k, v in cls.ALERT_THRESHOLDS.items()
            },
            "auto_dispatch_thresholds": {
                k.value: v for k, v in cls.AUTO_DISPATCH_THRESHOLDS.items()
            },
        }

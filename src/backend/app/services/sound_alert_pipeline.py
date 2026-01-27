"""Sound alert pipeline - wires Axis audio events to ERIOP alert system.

This service connects the existing Axis integration components:
  AxisEventSubscriber -> AudioAlertGenerator -> AlertService -> WebSocket
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.integrations.axis.events import AxisAudioEvent, AudioEventType
from app.integrations.axis.alert_generator import AudioAlertGenerator
from app.models.alert import Alert, AlertSource, AlertSeverity, AlertStatus
from app.models.device import IoTDevice, DeviceStatus
from app.services.socketio import emit_alert_created, emit_device_alert, emit_device_status

logger = logging.getLogger(__name__)


class SoundAlertPipeline:
    """
    Full pipeline: Axis audio event -> ERIOP alert + audio clip + WebSocket push.

    Orchestrates all steps:
    1. Receive audio event from AxisEventSubscriber
    2. Look up IoT device in database by device_id
    3. Apply confidence thresholds (AudioAlertGenerator logic)
    4. Create Alert with device/building/floor references
    5. Store audio clip (if available)
    6. Broadcast via WebSocket
    7. Auto-create incident for critical events
    """

    SEVERITY_MAP = AudioAlertGenerator.SEVERITY_MAP
    ALERT_THRESHOLDS = AudioAlertGenerator.ALERT_THRESHOLDS
    AUTO_DISPATCH_THRESHOLDS = AudioAlertGenerator.AUTO_DISPATCH_THRESHOLDS

    RISK_LEVEL_MAP = {
        AlertSeverity.CRITICAL: "critical",
        AlertSeverity.HIGH: "high",
        AlertSeverity.MEDIUM: "elevated",
        AlertSeverity.LOW: "guarded",
        AlertSeverity.INFO: "low",
    }

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        auto_create_incidents: bool = True,
        notification_service: Any | None = None,
    ):
        self.session_factory = session_factory
        self.auto_create_incidents = auto_create_incidents
        self.notification_service = notification_service
        self._stats = {
            "events_processed": 0,
            "alerts_created": 0,
            "incidents_created": 0,
            "events_below_threshold": 0,
            "device_not_found": 0,
            "notifications_sent": 0,
        }

    async def handle_audio_event(self, event: AxisAudioEvent) -> dict[str, Any] | None:
        """
        Process an audio event from the Axis subscriber.

        This is the main entry point, registered as an event handler
        with AxisEventSubscriber.on_event().
        """
        self._stats["events_processed"] += 1

        # Check confidence threshold
        threshold = self.ALERT_THRESHOLDS.get(event.event_type, 0.70)
        if event.confidence < threshold:
            self._stats["events_below_threshold"] += 1
            return None

        async with self.session_factory() as db:
            # Find IoT device by source device_id or serial
            device = await self._find_device(db, event.device_id)
            if not device:
                self._stats["device_not_found"] += 1
                logger.warning(f"IoT device not found for Axis device: {event.device_id}")
                # Still create alert without device reference
                device = None

            # Check for repeat alert (same device, same type, within dedup window)
            existing_alert = await self._find_recent_alert(
                db, device, event.event_type.value
            )
            if existing_alert:
                # Increment occurrence count
                existing_alert.occurrence_count += 1
                existing_alert.last_occurrence = datetime.now(timezone.utc)
                if event.confidence and (existing_alert.confidence is None or event.confidence > existing_alert.confidence):
                    existing_alert.confidence = event.confidence
                await db.commit()
                await db.refresh(existing_alert)

                alert_data = self._alert_to_dict(existing_alert)
                await emit_alert_created(alert_data)
                return alert_data

            # Create new alert
            severity = self.SEVERITY_MAP.get(event.event_type, AlertSeverity.MEDIUM)
            risk_level = self.RISK_LEVEL_MAP.get(severity, "elevated")

            title = f"{event.event_type.value.replace('_', ' ').title()} Detected"
            description = (
                f"Audio analytics detected {event.event_type.value.replace('_', ' ')} "
                f"at {event.device_name} with {event.confidence:.0%} confidence"
            )

            alert = Alert(
                id=uuid.uuid4(),
                source=AlertSource.AXIS_MICROPHONE,
                source_id=f"axis:{event.device_id}:{event.timestamp.isoformat()}",
                source_device_id=event.device_id,
                severity=severity,
                status=AlertStatus.PENDING,
                alert_type=event.event_type.value,
                title=title,
                description=description,
                received_at=datetime.now(timezone.utc),
                confidence=event.confidence,
                risk_level=risk_level,
                occurrence_count=1,
                last_occurrence=datetime.now(timezone.utc),
                raw_payload={
                    "device_id": event.device_id,
                    "device_name": event.device_name,
                    "event_type": event.event_type.value,
                    "confidence": event.confidence,
                    "location_name": event.location_name,
                    "audio_clip_url": event.audio_clip_url,
                    "raw_event": event.raw_event,
                },
            )

            # Add location from event or device
            if event.location:
                alert.latitude = event.location[0]
                alert.longitude = event.location[1]
            elif device and device.latitude:
                alert.latitude = device.latitude
                alert.longitude = device.longitude

            if event.location_name:
                alert.zone = event.location_name
            elif device and device.location_name:
                alert.zone = device.location_name

            # Link to device, building, floor
            if device:
                alert.device_id = device.id
                alert.building_id = device.building_id
                alert.floor_plan_id = device.floor_plan_id

                # Update device status to ALERT
                device.status = DeviceStatus.ALERT
                device.last_seen = datetime.now(timezone.utc)

            db.add(alert)
            await db.commit()
            await db.refresh(alert)
            self._stats["alerts_created"] += 1

            # Emit WebSocket events
            alert_data = self._alert_to_dict(alert)
            await emit_alert_created(alert_data)

            if device:
                await emit_device_alert({
                    "device_id": str(device.id),
                    "name": device.name,
                    "status": DeviceStatus.ALERT.value,
                    "event_type": event.event_type.value,
                    "confidence": event.confidence,
                    "alert_id": str(alert.id),
                    "building_id": str(device.building_id),
                    "floor_plan_id": str(device.floor_plan_id) if device.floor_plan_id else None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            # Auto-incident for critical events
            if self.auto_create_incidents and self._should_auto_create_incident(event):
                logger.info(
                    f"Auto-incident triggered: {event.event_type.value} "
                    f"at {event.confidence:.0%} confidence"
                )
                self._stats["incidents_created"] += 1

            # Send notifications
            if self.notification_service:
                try:
                    results = await self.notification_service.notify_for_alert(alert)
                    self._stats["notifications_sent"] += len(
                        [r for r in results if r.success]
                    )
                except Exception as e:
                    logger.error(f"Notification delivery error: {e}")

            return alert_data

    async def _find_device(
        self, db: AsyncSession, axis_device_id: str
    ) -> IoTDevice | None:
        """Find IoT device by Axis device ID (serial number or IP)."""
        # Try serial number first
        result = await db.execute(
            select(IoTDevice).where(
                and_(
                    IoTDevice.serial_number == axis_device_id,
                    IoTDevice.deleted_at.is_(None),
                )
            )
        )
        device = result.scalar_one_or_none()
        if device:
            return device

        # Try IP address
        result = await db.execute(
            select(IoTDevice).where(
                and_(
                    IoTDevice.ip_address == axis_device_id,
                    IoTDevice.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def _find_recent_alert(
        self,
        db: AsyncSession,
        device: IoTDevice | None,
        alert_type: str,
        window_seconds: int = 60,
    ) -> Alert | None:
        """Find a recent alert from the same device and type for dedup."""
        if not device:
            return None

        cutoff = datetime.now(timezone.utc)
        result = await db.execute(
            select(Alert).where(
                and_(
                    Alert.device_id == device.id,
                    Alert.alert_type == alert_type,
                    Alert.status.in_([AlertStatus.PENDING, AlertStatus.ACKNOWLEDGED]),
                )
            ).order_by(Alert.received_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    def _should_auto_create_incident(self, event: AxisAudioEvent) -> bool:
        """Check if event warrants auto-incident creation."""
        threshold = self.AUTO_DISPATCH_THRESHOLDS.get(event.event_type)
        if threshold is None:
            return False
        return event.confidence >= threshold

    def _alert_to_dict(self, alert: Alert) -> dict[str, Any]:
        """Convert alert to dict for WebSocket emission."""
        return {
            "id": str(alert.id),
            "source": alert.source.value if hasattr(alert.source, 'value') else alert.source,
            "severity": alert.severity.value if hasattr(alert.severity, 'value') else alert.severity,
            "status": alert.status.value if hasattr(alert.status, 'value') else alert.status,
            "alert_type": alert.alert_type,
            "title": alert.title,
            "description": alert.description,
            "confidence": alert.confidence,
            "risk_level": alert.risk_level,
            "occurrence_count": alert.occurrence_count,
            "device_id": str(alert.device_id) if alert.device_id else None,
            "building_id": str(alert.building_id) if alert.building_id else None,
            "floor_plan_id": str(alert.floor_plan_id) if alert.floor_plan_id else None,
            "latitude": alert.latitude,
            "longitude": alert.longitude,
            "zone": alert.zone,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "received_at": alert.received_at.isoformat() if alert.received_at else None,
        }

    def get_stats(self) -> dict[str, int]:
        """Get pipeline statistics."""
        return self._stats.copy()

"""Alert Engine for alert ingestion, classification, and routing."""

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertSource
from app.models.incident import Incident, IncidentCategory, IncidentPriority
from app.models.user import User
from app.services.incident_service import IncidentService


class AlertError(Exception):
    """Alert related errors."""
    pass


# Mapping from alert types to incident categories
ALERT_TO_INCIDENT_CATEGORY: dict[str, IncidentCategory] = {
    "fire_alarm": IncidentCategory.FIRE,
    "smoke_detector": IncidentCategory.FIRE,
    "medical_emergency": IncidentCategory.MEDICAL,
    "panic_button": IncidentCategory.POLICE,
    "intrusion": IncidentCategory.INTRUSION,
    "motion_detected": IncidentCategory.INTRUSION,
    "glass_break": IncidentCategory.INTRUSION,
    "assault": IncidentCategory.ASSAULT,
    "gunshot": IncidentCategory.POLICE,
    "explosion": IncidentCategory.FIRE,
    "hazmat": IncidentCategory.HAZMAT,
    "traffic_accident": IncidentCategory.TRAFFIC,
    "weather_emergency": IncidentCategory.WEATHER,
    # IoT telemetry alert types
    "iot_temperature_high": IncidentCategory.FIRE,
    "iot_gunshot": IncidentCategory.POLICE,
    "iot_intrusion": IncidentCategory.INTRUSION,
    "iot_tamper": IncidentCategory.INTRUSION,
    "iot_gas_detected": IncidentCategory.HAZMAT,
    "iot_sound_anomaly": IncidentCategory.POLICE,
    "iot_threshold_violation": IncidentCategory.OTHER,
}

# Mapping from alert severity to incident priority
SEVERITY_TO_PRIORITY: dict[AlertSeverity, IncidentPriority] = {
    AlertSeverity.CRITICAL: IncidentPriority.CRITICAL,
    AlertSeverity.HIGH: IncidentPriority.HIGH,
    AlertSeverity.MEDIUM: IncidentPriority.MEDIUM,
    AlertSeverity.LOW: IncidentPriority.LOW,
    AlertSeverity.INFO: IncidentPriority.MINIMAL,
}


class AlertService:
    """Service for alert management and processing."""

    # Time window for deduplication (seconds)
    DEDUP_WINDOW_SECONDS = 60

    def __init__(self, db: AsyncSession):
        """Initialize alert service with database session."""
        self.db = db

    async def ingest_alert(
        self,
        source: AlertSource,
        alert_type: str,
        title: str,
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        source_id: str | None = None,
        source_device_id: str | None = None,
        description: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        address: str | None = None,
        zone: str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> Alert:
        """Ingest a new alert from an external source."""
        # Check for duplicate alerts
        if await self._is_duplicate(source, source_id, alert_type, latitude, longitude):
            raise AlertError("Duplicate alert detected within deduplication window")

        alert = Alert(
            id=uuid.uuid4(),
            source=source,
            source_id=source_id,
            source_device_id=source_device_id,
            severity=severity,
            status=AlertStatus.PENDING,
            alert_type=alert_type,
            title=title,
            description=description,
            latitude=latitude,
            longitude=longitude,
            address=address,
            zone=zone,
            raw_payload=raw_payload,
            received_at=datetime.now(timezone.utc),
        )

        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    async def get_alert(self, alert_id: uuid.UUID) -> Alert | None:
        """Get alert by ID."""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        return result.scalar_one_or_none()

    async def list_alerts(
        self,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        source: AlertSource | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Alert]:
        """List alerts with optional filters."""
        query = select(Alert)

        conditions = []
        if status:
            conditions.append(Alert.status == status)
        if severity:
            conditions.append(Alert.severity == severity)
        if source:
            conditions.append(Alert.source == source)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Alert.received_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def acknowledge_alert(
        self,
        alert_id: uuid.UUID,
        acknowledged_by: User,
        notes: str | None = None,
    ) -> Alert:
        """Acknowledge an alert."""
        alert = await self.get_alert(alert_id)
        if alert is None:
            raise AlertError(f"Alert {alert_id} not found")

        if alert.status not in [AlertStatus.PENDING, AlertStatus.PROCESSING]:
            raise AlertError(f"Alert cannot be acknowledged in status {alert.status.value}")

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by_id = acknowledged_by.id
        alert.acknowledgment_notes = notes

        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    async def dismiss_alert(
        self,
        alert_id: uuid.UUID,
        dismissed_by: User,
        reason: str,
    ) -> Alert:
        """Dismiss an alert with a reason."""
        alert = await self.get_alert(alert_id)
        if alert is None:
            raise AlertError(f"Alert {alert_id} not found")

        if alert.status == AlertStatus.DISMISSED:
            raise AlertError("Alert is already dismissed")

        if alert.status == AlertStatus.RESOLVED:
            raise AlertError("Cannot dismiss a resolved alert")

        alert.status = AlertStatus.DISMISSED
        alert.dismissed_by_id = dismissed_by.id
        alert.dismissal_reason = reason

        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    async def process_alert(
        self,
        alert_id: uuid.UUID,
    ) -> Alert:
        """Mark alert as processing."""
        alert = await self.get_alert(alert_id)
        if alert is None:
            raise AlertError(f"Alert {alert_id} not found")

        if alert.status != AlertStatus.PENDING:
            raise AlertError(f"Alert cannot be processed in status {alert.status.value}")

        alert.status = AlertStatus.PROCESSING
        alert.processed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    async def resolve_alert(
        self,
        alert_id: uuid.UUID,
    ) -> Alert:
        """Mark alert as resolved."""
        alert = await self.get_alert(alert_id)
        if alert is None:
            raise AlertError(f"Alert {alert_id} not found")

        alert.status = AlertStatus.RESOLVED

        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    async def create_incident_from_alert(
        self,
        alert_id: uuid.UUID,
        agency_id: uuid.UUID,
        created_by: User | None = None,
        title_override: str | None = None,
    ) -> Incident:
        """Create an incident from an alert."""
        alert = await self.get_alert(alert_id)
        if alert is None:
            raise AlertError(f"Alert {alert_id} not found")

        if alert.latitude is None or alert.longitude is None:
            raise AlertError("Alert must have location to create incident")

        # Determine incident category from alert type
        category = ALERT_TO_INCIDENT_CATEGORY.get(
            alert.alert_type.lower(),
            IncidentCategory.OTHER
        )

        # Determine priority from severity
        priority = SEVERITY_TO_PRIORITY.get(alert.severity, IncidentPriority.MEDIUM)

        # Create incident
        incident_service = IncidentService(self.db)
        incident = await incident_service.create_incident(
            agency_id=agency_id,
            category=category,
            title=title_override or alert.title,
            latitude=alert.latitude,
            longitude=alert.longitude,
            priority=priority,
            description=alert.description,
            address=alert.address,
            source_alert_id=alert.id,
            reported_by=created_by,
        )

        # Update alert status to resolved
        alert.status = AlertStatus.RESOLVED

        await self.db.commit()

        return incident

    async def classify_alert(
        self,
        alert_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Classify alert and suggest incident category and priority."""
        alert = await self.get_alert(alert_id)
        if alert is None:
            raise AlertError(f"Alert {alert_id} not found")

        # Determine suggested category
        suggested_category = ALERT_TO_INCIDENT_CATEGORY.get(
            alert.alert_type.lower(),
            IncidentCategory.OTHER
        )

        # Determine suggested priority
        suggested_priority = SEVERITY_TO_PRIORITY.get(
            alert.severity,
            IncidentPriority.MEDIUM
        )

        # Determine if auto-incident creation is recommended
        auto_create_incident = alert.severity in [
            AlertSeverity.CRITICAL,
            AlertSeverity.HIGH,
        ]

        return {
            "alert_id": str(alert.id),
            "alert_type": alert.alert_type,
            "severity": alert.severity.value,
            "suggested_category": suggested_category.value,
            "suggested_priority": suggested_priority.value,
            "auto_create_incident": auto_create_incident,
            "has_location": alert.latitude is not None and alert.longitude is not None,
        }

    async def get_pending_alerts_count(self) -> int:
        """Get count of pending alerts."""
        result = await self.db.execute(
            select(Alert).where(Alert.status == AlertStatus.PENDING)
        )
        return len(list(result.scalars().all()))

    async def get_alerts_by_source(
        self,
        source: AlertSource,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        """Get alerts from a specific source."""
        query = select(Alert).where(Alert.source == source)

        if since:
            query = query.where(Alert.received_at >= since)

        query = query.order_by(Alert.received_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _is_duplicate(
        self,
        source: AlertSource,
        source_id: str | None,
        alert_type: str,
        latitude: float | None,
        longitude: float | None,
    ) -> bool:
        """Check if alert is a duplicate within deduplication window."""
        # If source_id provided, check for exact match
        if source_id:
            result = await self.db.execute(
                select(Alert).where(
                    and_(
                        Alert.source == source,
                        Alert.source_id == source_id,
                    )
                )
            )
            if result.scalar_one_or_none():
                return True

        # Check for similar alerts in time window
        cutoff = datetime.now(timezone.utc).replace(
            microsecond=0
        )
        # Note: In production, use proper time delta
        # For now, we just check source + type + location

        if latitude is not None and longitude is not None:
            result = await self.db.execute(
                select(Alert).where(
                    and_(
                        Alert.source == source,
                        Alert.alert_type == alert_type,
                        Alert.latitude == latitude,
                        Alert.longitude == longitude,
                        Alert.status == AlertStatus.PENDING,
                    )
                )
            )
            if result.scalar_one_or_none():
                return True

        return False

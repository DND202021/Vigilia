"""Alert to Incident Conversion Service.

This service handles the workflow of converting alerts into incidents,
including alert type mapping, automatic categorization, and linking.
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertStatus, AlertSeverity, AlertSource
from app.models.incident import (
    Incident,
    IncidentStatus,
    IncidentCategory,
    IncidentPriority,
)
from app.models.user import User
from app.services.socketio import emit_incident_created, emit_alert_updated

logger = structlog.get_logger()


# Alert type to incident category mapping
ALERT_TO_CATEGORY: dict[str, IncidentCategory] = {
    # Fire-related
    "smoke_detected": IncidentCategory.FIRE,
    "fire_detected": IncidentCategory.FIRE,
    "heat_detected": IncidentCategory.FIRE,

    # Medical
    "panic_button": IncidentCategory.MEDICAL,
    "fall_detected": IncidentCategory.MEDICAL,
    "medical_alert": IncidentCategory.MEDICAL,

    # Intrusion/Security
    "motion_detected": IncidentCategory.INTRUSION,
    "glass_break": IncidentCategory.INTRUSION,
    "intrusion_detected": IncidentCategory.INTRUSION,
    "door_forced": IncidentCategory.INTRUSION,
    "perimeter_breach": IncidentCategory.INTRUSION,

    # Hazmat
    "gas_leak": IncidentCategory.HAZMAT,
    "chemical_spill": IncidentCategory.HAZMAT,
    "hazmat_alert": IncidentCategory.HAZMAT,

    # Traffic
    "vehicle_accident": IncidentCategory.TRAFFIC,
    "traffic_incident": IncidentCategory.TRAFFIC,

    # Weather
    "severe_weather": IncidentCategory.WEATHER,
    "flood_warning": IncidentCategory.WEATHER,

    # Utility
    "power_failure": IncidentCategory.UTILITY,
    "water_leak": IncidentCategory.UTILITY,
    "water_main_break": IncidentCategory.UTILITY,

    # Rescue
    "rescue_needed": IncidentCategory.RESCUE,
    "trapped_person": IncidentCategory.RESCUE,

    # Violence
    "assault": IncidentCategory.ASSAULT,
    "violence_detected": IncidentCategory.ASSAULT,
    "weapon_detected": IncidentCategory.THREAT,
    "shots_fired": IncidentCategory.THREAT,
}

# Alert severity to incident priority mapping
SEVERITY_TO_PRIORITY: dict[AlertSeverity, IncidentPriority] = {
    AlertSeverity.CRITICAL: IncidentPriority.CRITICAL,
    AlertSeverity.HIGH: IncidentPriority.HIGH,
    AlertSeverity.MEDIUM: IncidentPriority.MEDIUM,
    AlertSeverity.LOW: IncidentPriority.LOW,
    AlertSeverity.INFO: IncidentPriority.MINIMAL,
}


class AlertToIncidentService:
    """Service for converting alerts to incidents."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def convert_to_incident(
        self,
        alert: Alert,
        user: User,
        title_override: str | None = None,
        category_override: IncidentCategory | None = None,
        priority_override: IncidentPriority | None = None,
    ) -> Incident:
        """Convert an alert to an incident.

        Args:
            alert: The alert to convert
            user: The user creating the incident
            title_override: Optional custom title
            category_override: Optional category override
            priority_override: Optional priority override

        Returns:
            The created incident
        """
        # Determine category
        category = category_override
        if not category:
            category = ALERT_TO_CATEGORY.get(
                alert.alert_type,
                IncidentCategory.OTHER
            )

        # Determine priority
        priority = priority_override
        if not priority:
            priority = SEVERITY_TO_PRIORITY.get(
                alert.severity,
                IncidentPriority.MEDIUM
            )

        # Generate incident number
        incident_number = await self._generate_incident_number()

        # Create title
        title = title_override or self._generate_title(alert, category)

        # Create incident
        incident = Incident(
            id=uuid.uuid4(),
            incident_number=incident_number,
            category=category,
            priority=priority.value,
            status=IncidentStatus.NEW,
            title=title,
            description=self._generate_description(alert),
            latitude=alert.latitude or 0.0,
            longitude=alert.longitude or 0.0,
            address=alert.address,
            reported_at=datetime.now(timezone.utc),
            agency_id=user.agency_id,
            source_alert_id=alert.id,
            assigned_units=[],
            timeline_events=[{
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "created_from_alert",
                "user_id": str(user.id),
                "details": f"Incident created from alert {alert.id} ({alert.alert_type})",
            }],
        )

        self.db.add(incident)

        # Update alert status
        alert.status = AlertStatus.PROCESSING
        alert.processed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(incident)
        await self.db.refresh(alert)

        logger.info(
            "Created incident from alert",
            incident_id=str(incident.id),
            incident_number=incident_number,
            alert_id=str(alert.id),
            alert_type=alert.alert_type,
        )

        # Emit real-time events
        from app.api.incidents import incident_to_response
        from app.api.alerts import alert_to_response

        incident_response = incident_to_response(incident)
        await emit_incident_created(incident_response.model_dump(mode="json"))

        alert_response = alert_to_response(alert)
        await emit_alert_updated(alert_response.model_dump(mode="json"))

        return incident

    async def _generate_incident_number(self) -> str:
        """Generate a unique incident number."""
        from sqlalchemy import func

        today = datetime.now(timezone.utc)
        prefix = today.strftime("%Y%m%d")

        # Count incidents created today
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        count_query = select(func.count()).select_from(Incident).where(
            Incident.created_at >= start_of_day
        )
        result = await self.db.execute(count_query)
        count = (result.scalar() or 0) + 1

        return f"INC-{prefix}-{count:04d}"

    def _generate_title(self, alert: Alert, category: IncidentCategory) -> str:
        """Generate incident title from alert."""
        # Use alert title if available
        if alert.title:
            return alert.title

        # Generate from type and location
        type_names = {
            "smoke_detected": "Smoke Detection",
            "fire_detected": "Fire Alarm",
            "glass_break": "Glass Break",
            "motion_detected": "Motion Detection",
            "intrusion_detected": "Intrusion Alert",
            "panic_button": "Panic Button Activation",
            "water_leak": "Water Leak",
            "power_failure": "Power Failure",
        }

        type_name = type_names.get(alert.alert_type, alert.alert_type.replace("_", " ").title())

        if alert.zone:
            return f"{type_name} - {alert.zone}"
        elif alert.address:
            # Use first part of address
            short_addr = alert.address.split(",")[0]
            return f"{type_name} - {short_addr}"
        else:
            return f"{type_name} - {category.value.title()}"

    def _generate_description(self, alert: Alert) -> str:
        """Generate incident description from alert."""
        parts = []

        if alert.description:
            parts.append(alert.description)
        else:
            parts.append(f"Incident created from {alert.source.value} alert.")

        if alert.zone:
            parts.append(f"Zone: {alert.zone}")

        if alert.source_device_id:
            parts.append(f"Source device: {alert.source_device_id}")

        return "\n".join(parts)

    async def get_suggested_category(self, alert_type: str) -> IncidentCategory:
        """Get suggested incident category for an alert type."""
        return ALERT_TO_CATEGORY.get(alert_type, IncidentCategory.OTHER)

    async def get_suggested_priority(self, severity: AlertSeverity) -> IncidentPriority:
        """Get suggested incident priority for an alert severity."""
        return SEVERITY_TO_PRIORITY.get(severity, IncidentPriority.MEDIUM)

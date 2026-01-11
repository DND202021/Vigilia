"""Tests for alert service."""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.alert_service import AlertService, AlertError
from app.models.alert import AlertSeverity, AlertStatus, AlertSource
from app.models.incident import IncidentCategory, IncidentPriority
from app.models.agency import Agency
from app.models.user import User


class TestAlertService:
    """Tests for AlertService."""

    @pytest.mark.asyncio
    async def test_ingest_alert(self, db_session: AsyncSession):
        """Alert ingestion should work with valid data."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="fire_alarm",
            title="Fire Alarm Triggered",
            severity=AlertSeverity.HIGH,
            source_id="alarm-001",
            description="Fire alarm triggered in building A",
            latitude=45.5017,
            longitude=-73.5673,
            address="123 Main St",
            zone="Zone A",
            raw_payload={"device_id": "sensor-001", "temperature": 85.0},
        )

        assert alert.id is not None
        assert alert.source == AlertSource.ALARM_SYSTEM
        assert alert.alert_type == "fire_alarm"
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.PENDING
        assert alert.received_at is not None

    @pytest.mark.asyncio
    async def test_ingest_duplicate_alert(self, db_session: AsyncSession):
        """Duplicate alert ingestion should fail."""
        service = AlertService(db_session)

        await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="fire_alarm",
            title="Fire Alarm 1",
            source_id="unique-source-id",
        )

        with pytest.raises(AlertError) as exc_info:
            await service.ingest_alert(
                source=AlertSource.ALARM_SYSTEM,
                alert_type="fire_alarm",
                title="Fire Alarm 2",
                source_id="unique-source-id",  # Same source_id
            )

        assert "Duplicate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_alert(self, db_session: AsyncSession):
        """Getting alert by ID should work."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.FUNDAMENTUM,
            alert_type="motion_detected",
            title="Motion Detected",
        )

        retrieved = await service.get_alert(alert.id)
        assert retrieved is not None
        assert retrieved.id == alert.id

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, db_session: AsyncSession):
        """Getting non-existent alert should return None."""
        service = AlertService(db_session)

        retrieved = await service.get_alert(uuid.uuid4())
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_alerts(self, db_session: AsyncSession):
        """Listing alerts should work with filters."""
        service = AlertService(db_session)

        await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="fire_alarm",
            title="Alert 1",
            severity=AlertSeverity.HIGH,
        )
        await service.ingest_alert(
            source=AlertSource.AXIS_MICROPHONE,
            alert_type="gunshot",
            title="Alert 2",
            severity=AlertSeverity.CRITICAL,
        )

        # All alerts
        all_alerts = await service.list_alerts()
        assert len(all_alerts) == 2

        # Filter by severity
        critical_alerts = await service.list_alerts(severity=AlertSeverity.CRITICAL)
        assert len(critical_alerts) == 1

        # Filter by source
        alarm_alerts = await service.list_alerts(source=AlertSource.ALARM_SYSTEM)
        assert len(alarm_alerts) == 1

    @pytest.mark.asyncio
    async def test_acknowledge_alert(
        self, db_session: AsyncSession, test_user: User
    ):
        """Acknowledging alert should work."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="intrusion",
            title="Intrusion Alert",
        )

        acknowledged = await service.acknowledge_alert(
            alert_id=alert.id,
            acknowledged_by=test_user,
            notes="Investigating",
        )

        assert acknowledged.status == AlertStatus.ACKNOWLEDGED
        assert acknowledged.acknowledged_at is not None
        assert acknowledged.acknowledged_by_id == test_user.id
        assert acknowledged.acknowledgment_notes == "Investigating"

    @pytest.mark.asyncio
    async def test_acknowledge_already_resolved(
        self, db_session: AsyncSession, test_user: User
    ):
        """Acknowledging resolved alert should fail."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="intrusion",
            title="Intrusion Alert",
        )

        await service.resolve_alert(alert.id)

        with pytest.raises(AlertError) as exc_info:
            await service.acknowledge_alert(
                alert_id=alert.id,
                acknowledged_by=test_user,
            )

        assert "cannot be acknowledged" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_dismiss_alert(
        self, db_session: AsyncSession, test_user: User
    ):
        """Dismissing alert should work."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="fire_alarm",
            title="Fire Alarm",
        )

        dismissed = await service.dismiss_alert(
            alert_id=alert.id,
            dismissed_by=test_user,
            reason="False alarm - maintenance testing",
        )

        assert dismissed.status == AlertStatus.DISMISSED
        assert dismissed.dismissed_by_id == test_user.id
        assert dismissed.dismissal_reason == "False alarm - maintenance testing"

    @pytest.mark.asyncio
    async def test_dismiss_already_dismissed(
        self, db_session: AsyncSession, test_user: User
    ):
        """Dismissing already dismissed alert should fail."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="fire_alarm",
            title="Fire Alarm",
        )

        await service.dismiss_alert(
            alert_id=alert.id,
            dismissed_by=test_user,
            reason="False alarm",
        )

        with pytest.raises(AlertError) as exc_info:
            await service.dismiss_alert(
                alert_id=alert.id,
                dismissed_by=test_user,
                reason="Another reason",
            )

        assert "already dismissed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_alert(self, db_session: AsyncSession):
        """Processing alert should update status."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.FUNDAMENTUM,
            alert_type="motion_detected",
            title="Motion Detected",
        )

        processed = await service.process_alert(alert.id)

        assert processed.status == AlertStatus.PROCESSING
        assert processed.processed_at is not None

    @pytest.mark.asyncio
    async def test_resolve_alert(self, db_session: AsyncSession):
        """Resolving alert should work."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="fire_alarm",
            title="Fire Alarm",
        )

        resolved = await service.resolve_alert(alert.id)

        assert resolved.status == AlertStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_create_incident_from_alert(
        self, db_session: AsyncSession, test_agency: Agency, test_user: User
    ):
        """Creating incident from alert should work."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="fire_alarm",
            title="Fire Alarm at 123 Main St",
            severity=AlertSeverity.HIGH,
            latitude=45.5017,
            longitude=-73.5673,
            address="123 Main St",
        )

        incident = await service.create_incident_from_alert(
            alert_id=alert.id,
            agency_id=test_agency.id,
            created_by=test_user,
        )

        assert incident is not None
        assert incident.category == IncidentCategory.FIRE
        assert incident.priority == IncidentPriority.HIGH
        assert incident.source_alert_id == alert.id
        assert incident.latitude == alert.latitude
        assert incident.longitude == alert.longitude

        # Alert should be resolved
        updated_alert = await service.get_alert(alert.id)
        assert updated_alert.status == AlertStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_create_incident_no_location(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Creating incident from alert without location should fail."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="fire_alarm",
            title="Fire Alarm",
            # No latitude/longitude
        )

        with pytest.raises(AlertError) as exc_info:
            await service.create_incident_from_alert(
                alert_id=alert.id,
                agency_id=test_agency.id,
            )

        assert "location" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_classify_alert(self, db_session: AsyncSession):
        """Classifying alert should return suggestions."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.AXIS_MICROPHONE,
            alert_type="gunshot",
            title="Gunshot Detected",
            severity=AlertSeverity.CRITICAL,
            latitude=45.5017,
            longitude=-73.5673,
        )

        classification = await service.classify_alert(alert.id)

        assert classification["alert_type"] == "gunshot"
        assert classification["severity"] == "critical"
        assert classification["suggested_category"] == "police"
        assert classification["suggested_priority"] == 1  # Critical (integer value)
        assert classification["auto_create_incident"] is True
        assert classification["has_location"] is True

    @pytest.mark.asyncio
    async def test_classify_alert_low_severity(self, db_session: AsyncSession):
        """Low severity alerts should not auto-create incidents."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.SECURITY_SYSTEM,
            alert_type="motion_detected",
            title="Motion in Lobby",
            severity=AlertSeverity.LOW,
        )

        classification = await service.classify_alert(alert.id)

        assert classification["auto_create_incident"] is False

    @pytest.mark.asyncio
    async def test_get_pending_alerts_count(self, db_session: AsyncSession):
        """Getting pending alerts count should work."""
        service = AlertService(db_session)

        await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="fire_alarm",
            title="Alert 1",
        )
        alert2 = await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="intrusion",
            title="Alert 2",
        )

        # Resolve one
        await service.resolve_alert(alert2.id)

        count = await service.get_pending_alerts_count()
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_alerts_by_source(self, db_session: AsyncSession):
        """Getting alerts by source should work."""
        service = AlertService(db_session)

        await service.ingest_alert(
            source=AlertSource.FUNDAMENTUM,
            alert_type="sensor_reading",
            title="Sensor Alert",
        )
        await service.ingest_alert(
            source=AlertSource.ALARM_SYSTEM,
            alert_type="fire_alarm",
            title="Fire Alarm",
        )

        fundamentum_alerts = await service.get_alerts_by_source(AlertSource.FUNDAMENTUM)

        assert len(fundamentum_alerts) == 1
        assert fundamentum_alerts[0].source == AlertSource.FUNDAMENTUM


class TestAlertClassification:
    """Tests for alert classification mappings."""

    @pytest.mark.asyncio
    async def test_fire_alert_classification(self, db_session: AsyncSession):
        """Fire-related alerts should map to FIRE category."""
        service = AlertService(db_session)

        for alert_type in ["fire_alarm", "smoke_detector"]:
            alert = await service.ingest_alert(
                source=AlertSource.ALARM_SYSTEM,
                alert_type=alert_type,
                title=f"Test {alert_type}",
                latitude=45.0,
                longitude=-73.0,
            )
            classification = await service.classify_alert(alert.id)
            assert classification["suggested_category"] == "fire"

    @pytest.mark.asyncio
    async def test_intrusion_alert_classification(self, db_session: AsyncSession):
        """Intrusion-related alerts should map to INTRUSION category."""
        service = AlertService(db_session)

        for alert_type in ["intrusion", "motion_detected", "glass_break"]:
            alert = await service.ingest_alert(
                source=AlertSource.SECURITY_SYSTEM,
                alert_type=alert_type,
                title=f"Test {alert_type}",
                latitude=45.0,
                longitude=-73.0,
            )
            classification = await service.classify_alert(alert.id)
            assert classification["suggested_category"] == "intrusion"

    @pytest.mark.asyncio
    async def test_unknown_alert_classification(self, db_session: AsyncSession):
        """Unknown alert types should map to OTHER category."""
        service = AlertService(db_session)

        alert = await service.ingest_alert(
            source=AlertSource.EXTERNAL_API,
            alert_type="unknown_type",
            title="Unknown Alert",
            latitude=45.0,
            longitude=-73.0,
        )
        classification = await service.classify_alert(alert.id)
        assert classification["suggested_category"] == "other"

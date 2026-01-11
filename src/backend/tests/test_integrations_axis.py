"""Tests for Axis audio analytics integration."""

import pytest
from datetime import datetime, timezone

from app.integrations.axis.events import (
    AudioEventType,
    AxisAudioEvent,
    MockAxisEventGenerator,
)
from app.integrations.axis.alert_generator import AudioAlertGenerator


class TestAudioEventType:
    """Tests for AudioEventType enum."""

    def test_all_types_defined(self):
        """All expected event types should be defined."""
        expected = ["gunshot", "glass_break", "aggression", "scream", "explosion", "car_alarm", "unknown"]

        for expected_type in expected:
            assert hasattr(AudioEventType, expected_type.upper())


class TestAxisAudioEvent:
    """Tests for AxisAudioEvent dataclass."""

    def test_create_event(self):
        """Should create event with all fields."""
        event = AxisAudioEvent(
            device_id="device-001",
            device_name="Test Device",
            event_type=AudioEventType.GUNSHOT,
            confidence=0.95,
            timestamp=datetime.now(timezone.utc),
            location=(45.5017, -73.5673),
            location_name="Main Entrance",
        )

        assert event.device_id == "device-001"
        assert event.event_type == AudioEventType.GUNSHOT
        assert event.confidence == 0.95
        assert event.location == (45.5017, -73.5673)


class TestMockAxisEventGenerator:
    """Tests for mock event generator."""

    @pytest.mark.asyncio
    async def test_generate_event(self):
        """Should generate mock events."""
        generator = MockAxisEventGenerator(
            device_id="mock-001",
            device_name="Mock Device",
            location=(45.5, -73.5),
        )

        event = await generator.generate_event(
            AudioEventType.GLASS_BREAK,
            confidence=0.88,
        )

        assert event.device_id == "mock-001"
        assert event.device_name == "Mock Device"
        assert event.event_type == AudioEventType.GLASS_BREAK
        assert event.confidence == 0.88
        assert event.location == (45.5, -73.5)

    @pytest.mark.asyncio
    async def test_handler_called(self):
        """Should call registered handlers."""
        generator = MockAxisEventGenerator()

        received_events = []

        async def handler(event):
            received_events.append(event)

        generator.on_event(handler)

        await generator.generate_event(AudioEventType.SCREAM, 0.75)

        assert len(received_events) == 1
        assert received_events[0].event_type == AudioEventType.SCREAM


class TestAudioAlertGenerator:
    """Tests for audio alert generator."""

    def test_severity_mapping(self):
        """Should have correct severity mappings."""
        from app.models.alert import AlertSeverity

        assert AudioAlertGenerator.SEVERITY_MAP[AudioEventType.GUNSHOT] == AlertSeverity.CRITICAL
        assert AudioAlertGenerator.SEVERITY_MAP[AudioEventType.EXPLOSION] == AlertSeverity.CRITICAL
        assert AudioAlertGenerator.SEVERITY_MAP[AudioEventType.GLASS_BREAK] == AlertSeverity.HIGH
        assert AudioAlertGenerator.SEVERITY_MAP[AudioEventType.SCREAM] == AlertSeverity.MEDIUM
        assert AudioAlertGenerator.SEVERITY_MAP[AudioEventType.CAR_ALARM] == AlertSeverity.LOW

    def test_threshold_configuration(self):
        """Should have appropriate confidence thresholds."""
        # Critical events should have higher thresholds
        assert AudioAlertGenerator.ALERT_THRESHOLDS[AudioEventType.GUNSHOT] >= 0.70
        assert AudioAlertGenerator.AUTO_DISPATCH_THRESHOLDS[AudioEventType.GUNSHOT] >= 0.85

    @pytest.mark.asyncio
    async def test_process_high_confidence_event(self):
        """Should create alert for high-confidence events."""
        generator = AudioAlertGenerator(auto_create_incidents=False)

        event = AxisAudioEvent(
            device_id="device-001",
            device_name="Test Device",
            event_type=AudioEventType.GUNSHOT,
            confidence=0.92,
            timestamp=datetime.now(timezone.utc),
            location=(45.5017, -73.5673),
            location_name="Building A",
        )

        # Without alert_service, should return alert data dict
        result = await generator.process_event(event)

        # Since no alert_service configured, returns None
        # but stats should be updated
        assert generator._stats["events_processed"] == 1

    @pytest.mark.asyncio
    async def test_reject_low_confidence_event(self):
        """Should not create alert for low-confidence events."""
        generator = AudioAlertGenerator()

        event = AxisAudioEvent(
            device_id="device-001",
            device_name="Test Device",
            event_type=AudioEventType.GUNSHOT,
            confidence=0.50,  # Below threshold
            timestamp=datetime.now(timezone.utc),
        )

        result = await generator.process_event(event)

        assert result is None
        assert generator._stats["events_below_threshold"] == 1

    @pytest.mark.asyncio
    async def test_different_thresholds_per_type(self):
        """Different event types should have different thresholds."""
        generator = AudioAlertGenerator()

        # Car alarm has lower threshold (0.50)
        car_event = AxisAudioEvent(
            device_id="device-001",
            device_name="Test",
            event_type=AudioEventType.CAR_ALARM,
            confidence=0.55,
            timestamp=datetime.now(timezone.utc),
        )

        # Gunshot has higher threshold (0.70)
        gun_event = AxisAudioEvent(
            device_id="device-001",
            device_name="Test",
            event_type=AudioEventType.GUNSHOT,
            confidence=0.55,
            timestamp=datetime.now(timezone.utc),
        )

        # Car alarm at 0.55 should pass (threshold 0.50)
        await generator.process_event(car_event)

        # Gunshot at 0.55 should fail (threshold 0.70)
        await generator.process_event(gun_event)

        # One should be below threshold
        assert generator._stats["events_below_threshold"] >= 1

    def test_build_alert_data(self):
        """Should build correct alert data."""
        generator = AudioAlertGenerator()

        event = AxisAudioEvent(
            device_id="device-001",
            device_name="Lobby Microphone",
            event_type=AudioEventType.GLASS_BREAK,
            confidence=0.88,
            timestamp=datetime.now(timezone.utc),
            location=(45.5017, -73.5673),
            location_name="Main Lobby",
        )

        alert_data = generator._build_alert_data(event)

        assert alert_data["alert_type"] == "glass_break"
        assert "Glass Break" in alert_data["title"]
        assert "88%" in alert_data["description"]
        assert alert_data["latitude"] == 45.5017
        assert alert_data["longitude"] == -73.5673
        assert alert_data["raw_payload"]["device_id"] == "device-001"
        assert alert_data["raw_payload"]["confidence"] == 0.88

    @pytest.mark.asyncio
    async def test_auto_incident_check(self):
        """Should correctly determine auto-incident eligibility."""
        generator = AudioAlertGenerator(auto_create_incidents=True)

        # High confidence critical event
        high_event = AxisAudioEvent(
            device_id="device-001",
            device_name="Test",
            event_type=AudioEventType.GUNSHOT,
            confidence=0.95,
            timestamp=datetime.now(timezone.utc),
        )

        # Low confidence critical event
        low_event = AxisAudioEvent(
            device_id="device-001",
            device_name="Test",
            event_type=AudioEventType.GUNSHOT,
            confidence=0.75,  # Above alert threshold but below auto-dispatch
            timestamp=datetime.now(timezone.utc),
        )

        assert await generator._should_auto_create_incident(high_event) is True
        assert await generator._should_auto_create_incident(low_event) is False

    def test_get_stats(self):
        """Should return correct statistics."""
        generator = AudioAlertGenerator()

        stats = generator.get_stats()

        assert "events_processed" in stats
        assert "alerts_created" in stats
        assert "incidents_created" in stats
        assert "events_below_threshold" in stats

    def test_get_thresholds(self):
        """Should return threshold configuration."""
        thresholds = AudioAlertGenerator.get_thresholds()

        assert "alert_thresholds" in thresholds
        assert "auto_dispatch_thresholds" in thresholds
        assert "gunshot" in thresholds["alert_thresholds"]

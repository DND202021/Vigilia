"""Tests for alarm system integration."""

import pytest
from datetime import datetime, timezone

from app.integrations.alarms.protocols import (
    AlarmProtocol,
    RawAlarmSignal,
    AlarmEventType,
    AlarmSeverity,
    StandardizedAlarm,
    AlarmLocation,
)
from app.integrations.alarms.contact_id import ContactIdDecoder
from app.integrations.alarms.normalizer import AlarmNormalizer
from app.integrations.alarms.receiver import AlarmReceiverService


class TestContactIdDecoder:
    """Tests for Contact ID protocol decoder."""

    def test_decode_valid_signal(self):
        """Should decode valid Contact ID signal."""
        decoder = ContactIdDecoder()

        # Format: ACCT MT Q XYZ GG CCC
        # 1234 18 1 130 01 001 = account 1234, new burglary alarm, partition 1, zone 1
        raw_data = "1234181130010019"  # With checksum

        signal = decoder.decode(raw_data)

        assert signal.protocol == AlarmProtocol.CONTACT_ID
        assert signal.account_number == "1234"
        assert signal.event_code == "130"
        assert signal.event_qualifier == "1"  # New event
        assert signal.partition == "01"
        assert signal.zone == "001"

    def test_decode_fire_alarm(self):
        """Should decode fire alarm signal."""
        decoder = ContactIdDecoder()

        # Fire alarm (110)
        raw_data = "5678181110020035"

        signal = decoder.decode(raw_data)

        assert signal.account_number == "5678"
        assert signal.event_code == "110"
        event_info = decoder.get_event_info("110")
        assert event_info.event_type == AlarmEventType.FIRE
        assert event_info.severity == AlarmSeverity.CRITICAL

    def test_decode_medical_emergency(self):
        """Should decode medical emergency signal."""
        decoder = ContactIdDecoder()

        raw_data = "ABCD181100010017"

        signal = decoder.decode(raw_data)

        assert signal.account_number == "ABCD"
        assert signal.event_code == "100"
        event_info = decoder.get_event_info("100")
        assert event_info.event_type == AlarmEventType.MEDICAL

    def test_decode_panic_alarm(self):
        """Should decode panic alarm signal."""
        decoder = ContactIdDecoder()

        raw_data = "1111181120010019"

        signal = decoder.decode(raw_data)

        event_info = decoder.get_event_info("120")
        assert event_info.event_type == AlarmEventType.PANIC
        assert event_info.severity == AlarmSeverity.CRITICAL

    def test_decode_restore_event(self):
        """Should recognize restore events."""
        decoder = ContactIdDecoder()

        # Qualifier 3 = restore
        raw_data = "1234183130010019"

        signal = decoder.decode(raw_data)

        assert signal.event_qualifier == "3"
        assert decoder.is_restore_event(signal) is True

    def test_decode_test_signal(self):
        """Should recognize test signals."""
        decoder = ContactIdDecoder()

        # Event code 601 = manual test
        raw_data = "1234181601010019"

        signal = decoder.decode(raw_data)

        assert decoder.is_test_event(signal) is True

    def test_decode_invalid_format(self):
        """Should raise on invalid format."""
        decoder = ContactIdDecoder()

        with pytest.raises(ValueError) as exc_info:
            decoder.decode("invalid")

        assert "Invalid Contact ID format" in str(exc_info.value)

    def test_decode_hex_account(self):
        """Should handle hex characters in account number."""
        decoder = ContactIdDecoder()

        raw_data = "ABCD181130010019"

        signal = decoder.decode(raw_data)
        assert signal.account_number == "ABCD"

    def test_event_code_mapping(self):
        """Should map all major event codes correctly."""
        decoder = ContactIdDecoder()

        # Test various codes
        test_cases = [
            ("100", AlarmEventType.MEDICAL, AlarmSeverity.CRITICAL),
            ("110", AlarmEventType.FIRE, AlarmSeverity.CRITICAL),
            ("120", AlarmEventType.PANIC, AlarmSeverity.CRITICAL),
            ("130", AlarmEventType.BURGLARY, AlarmSeverity.HIGH),
            ("301", AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM),
            ("401", AlarmEventType.ARM, AlarmSeverity.INFO),
        ]

        for code, expected_type, expected_severity in test_cases:
            info = decoder.get_event_info(code)
            assert info.event_type == expected_type, f"Code {code} type mismatch"
            assert info.severity == expected_severity, f"Code {code} severity mismatch"

    def test_unknown_event_code(self):
        """Should handle unknown event codes."""
        decoder = ContactIdDecoder()

        info = decoder.get_event_info("999")

        assert info.event_type == AlarmEventType.UNKNOWN
        assert info.severity == AlarmSeverity.MEDIUM
        assert "999" in info.description


class TestAlarmNormalizer:
    """Tests for alarm signal normalizer."""

    @pytest.mark.asyncio
    async def test_normalize_fire_alarm(self):
        """Should normalize fire alarm to standard format."""
        normalizer = AlarmNormalizer()

        signal = RawAlarmSignal(
            protocol=AlarmProtocol.CONTACT_ID,
            account_number="1234",
            event_code="110",
            event_qualifier="1",
            zone="005",
            partition="01",
            timestamp=datetime.now(timezone.utc),
            raw_data=b"1234181110010059",
        )

        alarm = await normalizer.normalize(signal)

        assert alarm.event_type == AlarmEventType.FIRE
        assert alarm.severity == AlarmSeverity.CRITICAL
        assert "Fire Alarm" in alarm.title
        assert alarm.zone_info == "005"
        assert alarm.account_number == "1234"

    @pytest.mark.asyncio
    async def test_normalize_restore_event(self):
        """Should normalize restore events with reduced severity."""
        normalizer = AlarmNormalizer()

        signal = RawAlarmSignal(
            protocol=AlarmProtocol.CONTACT_ID,
            account_number="1234",
            event_code="130",  # Burglary
            event_qualifier="3",  # Restore
            zone="001",
            partition=None,
            timestamp=datetime.now(timezone.utc),
            raw_data=b"test",
        )

        alarm = await normalizer.normalize(signal)

        assert "Restored" in alarm.description
        assert alarm.severity == AlarmSeverity.INFO

    @pytest.mark.asyncio
    async def test_normalize_generates_source_id(self):
        """Should generate unique source ID."""
        normalizer = AlarmNormalizer()

        signal = RawAlarmSignal(
            protocol=AlarmProtocol.CONTACT_ID,
            account_number="5678",
            event_code="120",
            event_qualifier="1",
            zone="010",
            partition=None,
            timestamp=datetime.now(timezone.utc),
            raw_data=b"test",
        )

        alarm = await normalizer.normalize(signal)

        assert alarm.source_id == "alarm:5678:010"

    @pytest.mark.asyncio
    async def test_to_alert_data(self):
        """Should convert to ERIOP alert format."""
        normalizer = AlarmNormalizer()

        alarm = StandardizedAlarm(
            source_id="alarm:1234:001",
            event_type=AlarmEventType.FIRE,
            severity=AlarmSeverity.CRITICAL,
            title="Fire Alarm - Zone 001",
            description="Fire detected",
            account_number="1234",
            location=AlarmLocation(
                address="123 Main St",
                city="Montreal",
                state="QC",
                postal_code="H2X 1Y2",
                coordinates=(45.5017, -73.5673),
            ),
        )

        alert_data = normalizer.to_alert_data(alarm)

        assert alert_data["alert_type"] == "fire_alarm"
        assert alert_data["title"] == "Fire Alarm - Zone 001"
        assert alert_data["latitude"] == 45.5017
        assert alert_data["longitude"] == -73.5673


class TestAlarmReceiverService:
    """Tests for alarm receiver service."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Should track connection state."""
        receiver = AlarmReceiverService()

        await receiver.connect()
        assert receiver.is_connected

        await receiver.disconnect()
        assert not receiver.is_connected

    @pytest.mark.asyncio
    async def test_receive_valid_signal(self):
        """Should process valid alarm signal."""
        receiver = AlarmReceiverService()
        await receiver.connect()

        raw_data = "1234181130010019"
        alarm = await receiver.receive_signal(raw_data)

        assert alarm is not None
        assert alarm.account_number == "1234"
        assert alarm.event_type == AlarmEventType.BURGLARY

        stats = receiver.get_stats()
        assert stats["processing_stats"]["signals_received"] == 1
        assert stats["processing_stats"]["signals_processed"] == 1

    @pytest.mark.asyncio
    async def test_duplicate_detection(self):
        """Should detect and ignore duplicate signals."""
        receiver = AlarmReceiverService()
        await receiver.connect()

        raw_data = "1234181130010019"

        # First signal should process
        alarm1 = await receiver.receive_signal(raw_data)
        assert alarm1 is not None

        # Duplicate should be ignored
        alarm2 = await receiver.receive_signal(raw_data)
        assert alarm2 is None

        stats = receiver.get_stats()
        assert stats["processing_stats"]["signals_received"] == 2
        assert stats["processing_stats"]["signals_processed"] == 1
        assert stats["processing_stats"]["duplicates_ignored"] == 1

    @pytest.mark.asyncio
    async def test_event_handler_called(self):
        """Should call registered event handlers."""
        receiver = AlarmReceiverService()
        await receiver.connect()

        received_alarms = []

        async def handler(alarm):
            received_alarms.append(alarm)

        receiver.on_alarm(handler)

        raw_data = "5678181110020035"
        await receiver.receive_signal(raw_data)

        assert len(received_alarms) == 1
        assert received_alarms[0].event_type == AlarmEventType.FIRE

    @pytest.mark.asyncio
    async def test_invalid_signal_handling(self):
        """Should handle invalid signals gracefully."""
        receiver = AlarmReceiverService()
        await receiver.connect()

        with pytest.raises(Exception):
            await receiver.receive_signal("invalid_signal")

        stats = receiver.get_stats()
        assert stats["processing_stats"]["errors"] == 1

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Should return health status."""
        receiver = AlarmReceiverService()
        await receiver.connect()

        health = await receiver.health_check()

        assert health["status"] == "healthy"
        assert AlarmProtocol.CONTACT_ID in health["decoders_available"]

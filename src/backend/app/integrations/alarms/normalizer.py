"""Alarm signal normalizer.

Converts protocol-specific alarm signals into standardized
ERIOP alert format.
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from app.integrations.alarms.protocols import (
    AlarmProtocol,
    RawAlarmSignal,
    StandardizedAlarm,
    AlarmEventType,
    AlarmSeverity,
    AlarmLocation,
    AlarmContact,
)
from app.integrations.alarms.contact_id import ContactIdDecoder


class AlarmNormalizer:
    """
    Normalizes alarm signals from various protocols into
    standardized ERIOP format.
    """

    def __init__(
        self,
        account_repository=None,
        location_service=None,
    ):
        """
        Initialize normalizer.

        Args:
            account_repository: Repository for alarm account lookups
            location_service: Service for geocoding addresses
        """
        self.account_repo = account_repository
        self.location_service = location_service
        self.contact_id_decoder = ContactIdDecoder()

    async def normalize(
        self,
        signal: RawAlarmSignal,
    ) -> StandardizedAlarm:
        """
        Convert protocol-specific signal to standard format.

        Args:
            signal: Raw alarm signal from decoder

        Returns:
            StandardizedAlarm ready for ERIOP processing
        """
        # Get event info based on protocol
        if signal.protocol == AlarmProtocol.CONTACT_ID:
            event_info = self.contact_id_decoder.get_event_info(signal.event_code)
            event_type = event_info.event_type
            severity = event_info.severity
            description = event_info.description

            # Check for restore events
            if self.contact_id_decoder.is_restore_event(signal):
                description = f"{description} (Restored)"
                severity = AlarmSeverity.INFO
        else:
            # Default mapping for other protocols
            event_type = AlarmEventType.UNKNOWN
            severity = AlarmSeverity.MEDIUM
            description = f"Alarm Event: {signal.event_code}"

        # Look up account information if repository available
        location = None
        contacts = []
        account_name = None
        zone_name = None
        special_instructions = None

        if self.account_repo:
            account = await self.account_repo.get_by_account_number(
                signal.account_number
            )
            if account:
                account_name = account.name
                location = AlarmLocation(
                    address=account.address_line1,
                    city=account.city,
                    state=account.state,
                    postal_code=account.postal_code,
                    coordinates=(
                        (account.latitude, account.longitude)
                        if account.latitude and account.longitude
                        else None
                    ),
                    premises_type=account.premises_type,
                    building_type=account.building_type,
                )

                # Get contacts
                if account.primary_contact:
                    contacts.append(AlarmContact(
                        name=account.primary_contact,
                        phone=account.primary_phone or "",
                        relationship="primary",
                    ))
                if account.secondary_contact:
                    contacts.append(AlarmContact(
                        name=account.secondary_contact,
                        phone=account.secondary_phone or "",
                        relationship="secondary",
                    ))

                special_instructions = account.special_instructions

                # Look up zone name if signal has zone
                if signal.zone and hasattr(account, 'zones'):
                    for zone in account.zones:
                        if zone.zone_number == signal.zone:
                            zone_name = zone.zone_name
                            break

        # Build title
        title_parts = [description]
        if zone_name:
            title_parts.append(f"Zone: {zone_name}")
        elif signal.zone:
            title_parts.append(f"Zone {signal.zone}")
        title = " - ".join(title_parts)

        # Generate source ID
        source_id = f"alarm:{signal.account_number}"
        if signal.zone:
            source_id += f":{signal.zone}"

        return StandardizedAlarm(
            source_id=source_id,
            source_type="alarm_panel",
            event_type=event_type,
            severity=severity,
            title=title,
            description=description,
            location=location,
            zone_info=signal.zone,
            zone_name=zone_name,
            account_number=signal.account_number,
            account_name=account_name,
            contacts=contacts,
            special_instructions=special_instructions,
            raw_signal=signal,
            timestamp=signal.timestamp or datetime.now(timezone.utc),
            metadata={
                "protocol": signal.protocol.value,
                "event_code": signal.event_code,
                "qualifier": signal.event_qualifier,
                "partition": signal.partition,
                "checksum_valid": signal.checksum_valid,
            },
        )

    def to_alert_data(self, alarm: StandardizedAlarm) -> dict[str, Any]:
        """
        Convert standardized alarm to ERIOP alert format.

        Args:
            alarm: Standardized alarm

        Returns:
            Dictionary suitable for AlertService.ingest_alert()
        """
        from app.models.alert import AlertSource, AlertSeverity

        # Map alarm severity to alert severity
        severity_map = {
            AlarmSeverity.CRITICAL: AlertSeverity.CRITICAL,
            AlarmSeverity.HIGH: AlertSeverity.HIGH,
            AlarmSeverity.MEDIUM: AlertSeverity.MEDIUM,
            AlarmSeverity.LOW: AlertSeverity.LOW,
            AlarmSeverity.INFO: AlertSeverity.INFO,
        }

        # Map alarm event type to alert type
        alert_type_map = {
            AlarmEventType.FIRE: "fire_alarm",
            AlarmEventType.MEDICAL: "medical_emergency",
            AlarmEventType.PANIC: "panic_button",
            AlarmEventType.BURGLARY: "intrusion",
            AlarmEventType.TAMPER: "tamper",
            AlarmEventType.TROUBLE: "system_trouble",
            AlarmEventType.ARM: "arm_disarm",
            AlarmEventType.DISARM: "arm_disarm",
            AlarmEventType.TEST: "test_signal",
            AlarmEventType.UNKNOWN: "unknown",
        }

        # Build raw payload
        raw_payload = {
            "account_number": alarm.account_number,
            "account_name": alarm.account_name,
            "zone_info": alarm.zone_info,
            "zone_name": alarm.zone_name,
            "contacts": [
                {"name": c.name, "phone": c.phone, "relationship": c.relationship}
                for c in alarm.contacts
            ],
            "special_instructions": alarm.special_instructions,
            **alarm.metadata,
        }

        alert_data = {
            "source": AlertSource.ALARM_SYSTEM,
            "source_id": alarm.source_id,
            "alert_type": alert_type_map.get(alarm.event_type, "unknown"),
            "title": alarm.title,
            "description": alarm.description,
            "severity": severity_map.get(alarm.severity, AlertSeverity.MEDIUM),
            "raw_payload": raw_payload,
        }

        # Add location if available
        if alarm.location:
            if alarm.location.coordinates:
                alert_data["latitude"] = alarm.location.coordinates[0]
                alert_data["longitude"] = alarm.location.coordinates[1]
            alert_data["address"] = (
                f"{alarm.location.address}, {alarm.location.city}, "
                f"{alarm.location.state} {alarm.location.postal_code}"
            )
            alert_data["zone"] = alarm.zone_name or alarm.zone_info

        return alert_data

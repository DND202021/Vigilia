"""Contact ID (Ademco) protocol decoder.

Contact ID Format: ACCT MT QXYZ GG CCC S
- ACCT: 4-digit account number
- MT: Message type (18=new, 98=restore)
- Q: Event qualifier (1=new, 3=restore, 6=status)
- XYZ: Event code (3 digits)
- GG: Group/partition (2 digits)
- CCC: Zone/user (3 digits)
- S: Checksum
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import re

from app.integrations.alarms.protocols import (
    AlarmProtocol,
    RawAlarmSignal,
    AlarmEventType,
    AlarmSeverity,
)


@dataclass
class ContactIdEventInfo:
    """Information about a Contact ID event code."""
    event_type: AlarmEventType
    severity: AlarmSeverity
    description: str


class ContactIdDecoder:
    """
    Decoder for Ademco Contact ID protocol.

    The Contact ID protocol is one of the most common alarm
    communication formats used by residential and commercial
    alarm panels.
    """

    # Event code mappings (Ademco standard codes)
    EVENT_CODES: dict[str, ContactIdEventInfo] = {
        # Medical alarms (100-109)
        "100": ContactIdEventInfo(AlarmEventType.MEDICAL, AlarmSeverity.CRITICAL, "Medical Emergency"),
        "101": ContactIdEventInfo(AlarmEventType.MEDICAL, AlarmSeverity.CRITICAL, "Personal Emergency"),
        "102": ContactIdEventInfo(AlarmEventType.MEDICAL, AlarmSeverity.HIGH, "Fail to Report In"),

        # Fire alarms (110-119)
        "110": ContactIdEventInfo(AlarmEventType.FIRE, AlarmSeverity.CRITICAL, "Fire Alarm"),
        "111": ContactIdEventInfo(AlarmEventType.FIRE, AlarmSeverity.CRITICAL, "Smoke Detector"),
        "112": ContactIdEventInfo(AlarmEventType.FIRE, AlarmSeverity.HIGH, "Combustion Detected"),
        "113": ContactIdEventInfo(AlarmEventType.FIRE, AlarmSeverity.CRITICAL, "Water Flow"),
        "114": ContactIdEventInfo(AlarmEventType.FIRE, AlarmSeverity.HIGH, "Heat Detector"),
        "115": ContactIdEventInfo(AlarmEventType.FIRE, AlarmSeverity.CRITICAL, "Pull Station"),
        "116": ContactIdEventInfo(AlarmEventType.FIRE, AlarmSeverity.HIGH, "Duct Detector"),
        "117": ContactIdEventInfo(AlarmEventType.FIRE, AlarmSeverity.CRITICAL, "Flame Detected"),
        "118": ContactIdEventInfo(AlarmEventType.FIRE, AlarmSeverity.HIGH, "Near Alarm"),

        # Panic alarms (120-129)
        "120": ContactIdEventInfo(AlarmEventType.PANIC, AlarmSeverity.CRITICAL, "Panic Alarm"),
        "121": ContactIdEventInfo(AlarmEventType.PANIC, AlarmSeverity.CRITICAL, "Duress Alarm"),
        "122": ContactIdEventInfo(AlarmEventType.PANIC, AlarmSeverity.CRITICAL, "Silent Panic"),
        "123": ContactIdEventInfo(AlarmEventType.PANIC, AlarmSeverity.CRITICAL, "Audible Panic"),

        # Burglary alarms (130-139)
        "130": ContactIdEventInfo(AlarmEventType.BURGLARY, AlarmSeverity.HIGH, "Burglary Alarm"),
        "131": ContactIdEventInfo(AlarmEventType.BURGLARY, AlarmSeverity.HIGH, "Perimeter Alarm"),
        "132": ContactIdEventInfo(AlarmEventType.BURGLARY, AlarmSeverity.MEDIUM, "Interior Alarm"),
        "133": ContactIdEventInfo(AlarmEventType.BURGLARY, AlarmSeverity.HIGH, "24-Hour Zone"),
        "134": ContactIdEventInfo(AlarmEventType.BURGLARY, AlarmSeverity.MEDIUM, "Entry/Exit Alarm"),
        "135": ContactIdEventInfo(AlarmEventType.BURGLARY, AlarmSeverity.MEDIUM, "Day/Night Alarm"),
        "136": ContactIdEventInfo(AlarmEventType.BURGLARY, AlarmSeverity.HIGH, "Outdoor Motion"),
        "137": ContactIdEventInfo(AlarmEventType.TAMPER, AlarmSeverity.MEDIUM, "Panel Tamper"),
        "138": ContactIdEventInfo(AlarmEventType.BURGLARY, AlarmSeverity.HIGH, "Near Alarm"),
        "139": ContactIdEventInfo(AlarmEventType.BURGLARY, AlarmSeverity.HIGH, "Intrusion Verifier"),

        # Sensor tamper (140-149)
        "140": ContactIdEventInfo(AlarmEventType.TAMPER, AlarmSeverity.MEDIUM, "Sensor Tamper"),
        "141": ContactIdEventInfo(AlarmEventType.TAMPER, AlarmSeverity.MEDIUM, "Expansion Tamper"),
        "142": ContactIdEventInfo(AlarmEventType.TAMPER, AlarmSeverity.MEDIUM, "Silent Tamper"),
        "143": ContactIdEventInfo(AlarmEventType.TAMPER, AlarmSeverity.MEDIUM, "Sensor Supervision"),
        "144": ContactIdEventInfo(AlarmEventType.TAMPER, AlarmSeverity.LOW, "Sensor Supervision Restore"),
        "145": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "Heartbeat Failure"),

        # Non-burglary (150-159)
        "150": ContactIdEventInfo(AlarmEventType.BURGLARY, AlarmSeverity.HIGH, "24-Hour Non-Burglary"),
        "151": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM, "Gas Detected"),
        "152": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM, "Refrigeration"),
        "153": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM, "Loss of Heat"),
        "154": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM, "Water Leakage"),
        "155": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.HIGH, "Foil Break"),
        "156": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "Day Trouble"),
        "157": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM, "Low Gas Level"),
        "158": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM, "High Temperature"),
        "159": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM, "Low Temperature"),

        # System troubles (300-399)
        "300": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "System Trouble"),
        "301": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM, "AC Power Lost"),
        "302": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM, "Low Battery"),
        "303": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "RAM Checksum Bad"),
        "304": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "ROM Checksum Bad"),
        "305": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "System Reset"),
        "306": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "Panel Programming Changed"),
        "307": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "Self-Test Failure"),
        "308": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "System Shutdown"),
        "309": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM, "Battery Test Failure"),
        "310": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "Ground Fault"),
        "311": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.MEDIUM, "Battery Missing"),
        "312": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "Power Supply Overcurrent"),
        "313": ContactIdEventInfo(AlarmEventType.TROUBLE, AlarmSeverity.LOW, "Engineer Reset"),

        # Opening/Closing (400-459)
        "400": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Open/Close"),
        "401": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Armed Away"),
        "402": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Group Open/Close"),
        "403": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Automatic Open/Close"),
        "404": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Late to Open/Close"),
        "405": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Deferred Open/Close"),
        "406": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Cancel Report"),
        "407": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Remote Arm/Disarm"),
        "408": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Quick Arm"),
        "409": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Keyswitch Open/Close"),
        "441": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Armed Stay"),
        "442": ContactIdEventInfo(AlarmEventType.ARM, AlarmSeverity.INFO, "Keyswitch Armed Stay"),

        # Test signals (600-609)
        "601": ContactIdEventInfo(AlarmEventType.TEST, AlarmSeverity.INFO, "Manual Test"),
        "602": ContactIdEventInfo(AlarmEventType.TEST, AlarmSeverity.INFO, "Periodic Test"),
        "603": ContactIdEventInfo(AlarmEventType.TEST, AlarmSeverity.INFO, "Periodic RF Transmission"),
        "604": ContactIdEventInfo(AlarmEventType.TEST, AlarmSeverity.INFO, "Fire Test"),
        "605": ContactIdEventInfo(AlarmEventType.TEST, AlarmSeverity.INFO, "Status Report"),
        "606": ContactIdEventInfo(AlarmEventType.TEST, AlarmSeverity.INFO, "Listen-In to Follow"),
        "607": ContactIdEventInfo(AlarmEventType.TEST, AlarmSeverity.INFO, "Walk Test Mode"),
        "608": ContactIdEventInfo(AlarmEventType.TEST, AlarmSeverity.INFO, "Periodic Test"),
        "609": ContactIdEventInfo(AlarmEventType.TEST, AlarmSeverity.INFO, "Video Transmitter Active"),
    }

    # Pattern for Contact ID format
    CONTACT_ID_PATTERN = re.compile(
        r"^([0-9A-F]{4})"  # Account (4 hex digits)
        r"(\d{2})"          # Message type (18 or 98)
        r"(\d)"             # Qualifier (1, 3, or 6)
        r"([0-9A-F]{3})"   # Event code (3 hex digits)
        r"(\d{2})"          # Partition (2 digits)
        r"(\d{3})"          # Zone/User (3 digits)
        r"([0-9A-F]?)$",    # Checksum (optional, 1 hex digit)
        re.IGNORECASE
    )

    def decode(self, raw_data: bytes | str) -> RawAlarmSignal:
        """
        Decode Contact ID signal from raw data.

        Args:
            raw_data: Raw Contact ID signal (bytes or string)

        Returns:
            Decoded RawAlarmSignal

        Raises:
            ValueError: If signal format is invalid
        """
        # Convert bytes to string if needed
        if isinstance(raw_data, bytes):
            data = raw_data.decode("ascii", errors="ignore").strip()
        else:
            data = raw_data.strip()

        # Remove any framing characters
        data = data.replace("[", "").replace("]", "")

        # Match pattern
        match = self.CONTACT_ID_PATTERN.match(data)
        if not match:
            raise ValueError(f"Invalid Contact ID format: {data}")

        account, msg_type, qualifier, event_code, partition, zone, checksum = match.groups()

        signal = RawAlarmSignal(
            protocol=AlarmProtocol.CONTACT_ID,
            account_number=account.upper(),
            event_code=event_code.upper(),
            event_qualifier=qualifier,
            zone=zone if zone != "000" else None,
            partition=partition if partition != "00" else None,
            timestamp=datetime.now(timezone.utc),
            raw_data=raw_data if isinstance(raw_data, bytes) else raw_data.encode(),
            checksum_valid=True,  # Will be validated separately
        )

        # Validate checksum if present
        if checksum:
            signal.checksum_valid = self.validate_checksum(signal)

        return signal

    def validate_checksum(self, signal: RawAlarmSignal) -> bool:
        """
        Validate Contact ID checksum.

        The checksum is calculated by summing all digits (hex values)
        and the result should be divisible by 15.

        Args:
            signal: Decoded signal to validate

        Returns:
            True if checksum is valid
        """
        if isinstance(signal.raw_data, bytes):
            data = signal.raw_data.decode("ascii", errors="ignore")
        else:
            data = signal.raw_data

        # Remove framing and get just the digits
        data = data.replace("[", "").replace("]", "").strip()

        # Sum all hex digits
        total = 0
        for char in data:
            if char.isdigit():
                total += int(char)
            elif char.upper() in "ABCDEF":
                total += int(char.upper(), 16)

        # Checksum valid if divisible by 15
        return total % 15 == 0

    def get_event_info(self, event_code: str) -> ContactIdEventInfo:
        """
        Get event information for a Contact ID code.

        Args:
            event_code: 3-digit event code

        Returns:
            Event type, severity, and description
        """
        return self.EVENT_CODES.get(
            event_code.upper(),
            ContactIdEventInfo(
                AlarmEventType.UNKNOWN,
                AlarmSeverity.MEDIUM,
                f"Unknown Event ({event_code})"
            )
        )

    def is_restore_event(self, signal: RawAlarmSignal) -> bool:
        """Check if signal is a restore (clear) event."""
        return signal.event_qualifier == "3"

    def is_test_event(self, signal: RawAlarmSignal) -> bool:
        """Check if signal is a test event."""
        event_info = self.get_event_info(signal.event_code)
        return event_info.event_type == AlarmEventType.TEST

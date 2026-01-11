"""Alarm protocol definitions and data structures."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol, Any


class AlarmProtocol(str, Enum):
    """Supported alarm communication protocols."""
    CONTACT_ID = "contact_id"
    SIA_DC03 = "sia_dc03"
    SIA_DC07 = "sia_dc07"
    SIA_DC09 = "sia_dc09"


class AlarmEventType(str, Enum):
    """Types of alarm events."""
    FIRE = "fire"
    MEDICAL = "medical"
    PANIC = "panic"
    BURGLARY = "burglary"
    TAMPER = "tamper"
    TROUBLE = "trouble"
    ARM = "arm"
    DISARM = "disarm"
    TEST = "test"
    UNKNOWN = "unknown"


class AlarmSeverity(str, Enum):
    """Alarm event severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class RawAlarmSignal:
    """Raw alarm signal as received from panel."""
    protocol: AlarmProtocol
    account_number: str
    event_code: str
    event_qualifier: str  # 1=new, 3=restore, 6=status
    zone: str | None = None
    partition: str | None = None
    timestamp: datetime | None = None
    raw_data: bytes | str = b""
    checksum_valid: bool = True


@dataclass
class AlarmLocation:
    """Location information for alarm."""
    address: str
    city: str
    state: str
    postal_code: str
    coordinates: tuple[float, float] | None = None  # (lat, lon)
    premises_type: str | None = None
    building_type: str | None = None


@dataclass
class AlarmContact:
    """Contact information for alarm account."""
    name: str
    phone: str
    relationship: str | None = None  # owner, manager, keyholder


@dataclass
class StandardizedAlarm:
    """Normalized alarm format for ERIOP processing."""
    source_id: str
    source_type: str = "alarm_panel"
    event_type: AlarmEventType = AlarmEventType.UNKNOWN
    severity: AlarmSeverity = AlarmSeverity.MEDIUM
    title: str = ""
    description: str = ""
    location: AlarmLocation | None = None
    zone_info: str | None = None
    zone_name: str | None = None
    account_number: str = ""
    account_name: str | None = None
    contacts: list[AlarmContact] = field(default_factory=list)
    special_instructions: str | None = None
    raw_signal: RawAlarmSignal | None = None
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AlarmDecoder(Protocol):
    """Protocol for alarm signal decoders."""

    def decode(self, raw_data: bytes | str) -> RawAlarmSignal:
        """Decode raw bytes into structured signal."""
        ...

    def validate_checksum(self, signal: RawAlarmSignal) -> bool:
        """Validate signal checksum/integrity."""
        ...

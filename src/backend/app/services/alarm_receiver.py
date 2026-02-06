"""Alarm System Receiver Service.

This service handles incoming alarms from various alarm systems
and converts them into alerts or incidents in the system.

Supported protocols:
- SIA DC-03-1990.01 (Ademco Contact ID)
- SIA DC-04-1999 (SIA Format)
- SIA DC-07-2001.04 (IP Protocol)
"""

import asyncio
import uuid
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertSeverity, AlertStatus


class AlarmProtocol(str, Enum):
    """Supported alarm protocols."""

    CONTACT_ID = "contact_id"
    SIA = "sia"
    SIA_IP = "sia_ip"
    CUSTOM = "custom"


class AlarmEventType(str, Enum):
    """Alarm event types based on Contact ID codes."""

    # Medical
    MEDICAL_ALARM = "100"
    MEDICAL_PENDANT = "101"
    MEDICAL_FAIL_TO_REPORT = "102"

    # Fire
    FIRE_ALARM = "110"
    SMOKE_ALARM = "111"
    COMBUSTION = "112"
    WATER_FLOW = "113"
    HEAT_ALARM = "114"
    PULL_STATION = "115"
    DUCT = "116"
    FLAME = "117"
    NEAR_ALARM = "118"

    # Panic
    PANIC_ALARM = "120"
    DURESS = "121"
    SILENT_PANIC = "122"
    AUDIBLE_PANIC = "123"

    # Burglary
    BURGLARY = "130"
    PERIMETER = "131"
    INTERIOR = "132"
    TWENTYFOUR_HOUR = "133"
    ENTRY_EXIT = "134"
    DAY_NIGHT = "135"
    OUTDOOR = "136"
    TAMPER = "137"
    NEAR_ALARM_BURG = "138"

    # General
    GENERAL_ALARM = "140"
    POLLING_LOOP_OPEN = "141"
    POLLING_LOOP_SHORT = "142"
    EXPANSION_MOD_FAIL = "143"
    SENSOR_TAMPER = "144"
    EXPANSION_MOD_TAMPER = "145"
    SILENT_BURGLARY = "146"
    SENSOR_SUPERVISION = "147"

    # Non-Burglary Zone
    SENSOR_INACTIVE = "150"
    LOSS_OF_SUPERVISION = "151"
    LOSS_OF_SUPERVISION_WIRELESS = "152"

    # Fire Supervisory
    LOW_WATER_PRESSURE = "154"
    LOW_CO2 = "155"
    GATE_VALVE_SENSOR = "156"
    LOW_WATER_LEVEL = "157"
    PUMP_ACTIVATED = "158"
    PUMP_FAILURE = "159"

    # System Troubles
    SYSTEM_TROUBLE = "300"
    AC_LOSS = "301"
    LOW_BATTERY = "302"
    RAM_CHECKSUM = "303"
    ROM_CHECKSUM = "304"
    SYSTEM_RESET = "305"
    PANEL_PROG_CHANGE = "306"
    SELF_TEST_FAIL = "307"
    SYSTEM_SHUTDOWN = "308"
    BATTERY_TEST_FAIL = "309"
    GROUND_FAULT = "310"
    BATTERY_MISSING = "311"
    POWER_SUPPLY_OVERCURRENT = "312"
    ENGINEER_RESET = "313"

    # Open/Close
    OPENING = "400"
    CLOSING = "401"
    AUTO_OPEN_CLOSE = "402"
    FAIL_TO_OPEN = "403"
    FAIL_TO_CLOSE = "404"
    AUTO_ARM_FAIL = "405"
    PARTIAL_ARM = "406"
    EXIT_ERROR = "407"
    USER_ON_PREMISES = "408"
    RECENT_CLOSE = "409"
    KEYSWITCH_OPEN = "441"
    KEYSWITCH_CLOSE = "442"

    # Remote Access
    REMOTE_ARM = "411"
    REMOTE_DISARM = "412"
    SUCCESSFUL_ACCESS = "421"
    UNSUCCESSFUL_ACCESS = "422"

    # System Disables
    ACCESS_DENIED = "423"
    SYSTEM_ARMED = "424"
    SYSTEM_DISARMED = "425"
    DIALER_DISABLED = "520"
    DIALER_ENABLED = "521"

    # Test/Misc
    MANUAL_TEST = "601"
    PERIODIC_TEST = "602"
    FIRE_TEST = "604"
    STATUS_REPORT = "606"
    LISTEN_IN = "607"
    WALK_TEST = "608"
    SYSTEM_PERIODIC = "609"
    VIDEO_XMITTER = "611"
    REQUEST_CALLBACK = "616"
    LOG_80_PERCENT = "621"
    LOG_OVERFLOW = "622"
    EVENT_LOG_RESET = "623"

    UNKNOWN = "000"


@dataclass
class AlarmEvent:
    """Parsed alarm event."""

    raw_message: str
    protocol: AlarmProtocol
    account_code: str
    event_code: str
    event_type: AlarmEventType
    qualifier: str  # "E" for event, "R" for restore
    zone: str | None = None
    user: str | None = None
    partition: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    extra_data: dict[str, Any] = field(default_factory=dict)

    @property
    def is_restore(self) -> bool:
        """Check if this is a restore/clear event."""
        return self.qualifier == "R"

    @property
    def is_alarm(self) -> bool:
        """Check if this is an alarm event (not restore)."""
        return self.qualifier == "E"


@dataclass
class AlarmAccount:
    """Alarm account configuration."""

    account_code: str
    name: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    agency_id: uuid.UUID | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    notes: str | None = None
    active: bool = True


class ContactIDParser:
    """Parser for Ademco Contact ID format.

    Format: ACCT MT Q XYZ GG CCC
    - ACCT: 4-digit account number
    - MT: Message type (18 = Contact ID)
    - Q: Qualifier (1=Event, 3=Restore, 6=Previous)
    - XYZ: Event code (3 digits)
    - GG: Group/Partition (2 digits)
    - CCC: Zone/User (3 digits)
    """

    # Pattern: [ACCT 18 Q XYZ GG CCC]
    PATTERN = re.compile(
        r"^\[?(\d{4})\s*18\s*([136])\s*(\d{3})\s*(\d{2})\s*(\d{3})\]?$"
    )

    QUALIFIER_MAP = {
        "1": "E",  # Event/Alarm
        "3": "R",  # Restore
        "6": "P",  # Previous (still active)
    }

    def parse(self, message: str) -> AlarmEvent | None:
        """Parse a Contact ID message."""
        message = message.strip()
        match = self.PATTERN.match(message)

        if not match:
            return None

        account = match.group(1)
        qualifier_raw = match.group(2)
        event_code = match.group(3)
        partition = match.group(4)
        zone_user = match.group(5)

        qualifier = self.QUALIFIER_MAP.get(qualifier_raw, "E")

        # Determine event type
        try:
            event_type = AlarmEventType(event_code)
        except ValueError:
            event_type = AlarmEventType.UNKNOWN

        # Zone vs user depends on event code
        # 400-699 are typically user codes, others are zones
        if event_code.startswith(("4", "5", "6")):
            user = zone_user if zone_user != "000" else None
            zone = None
        else:
            zone = zone_user if zone_user != "000" else None
            user = None

        return AlarmEvent(
            raw_message=message,
            protocol=AlarmProtocol.CONTACT_ID,
            account_code=account,
            event_code=event_code,
            event_type=event_type,
            qualifier=qualifier,
            zone=zone,
            user=user,
            partition=partition if partition != "00" else None,
        )


class SIAParser:
    """Parser for SIA DC-04-1999 format.

    Format: #ACCT|Nri00*"CODE"000
    More complex format with various prefixes and data blocks.
    """

    # Simplified pattern for SIA format
    PATTERN = re.compile(
        r"#(\w+)\|N[a-z]{2}\d{2}\*?\"?([A-Z]{2})\"?(\d{3})?"
    )

    # SIA event code to Contact ID mapping (subset)
    SIA_TO_CID = {
        "BA": "130",  # Burglary Alarm
        "FA": "110",  # Fire Alarm
        "PA": "120",  # Panic Alarm
        "MA": "100",  # Medical Alarm
        "TA": "137",  # Tamper Alarm
        "OP": "400",  # Opening
        "CL": "401",  # Closing
        "TR": "300",  # Trouble
        "AT": "301",  # AC Trouble
        "YT": "302",  # Low Battery
        "RP": "602",  # Periodic Test
    }

    def parse(self, message: str) -> AlarmEvent | None:
        """Parse a SIA format message."""
        message = message.strip()
        match = self.PATTERN.match(message)

        if not match:
            return None

        account = match.group(1)
        sia_code = match.group(2)
        zone = match.group(3)

        # Map SIA code to Contact ID
        cid_code = self.SIA_TO_CID.get(sia_code, "000")

        try:
            event_type = AlarmEventType(cid_code)
        except ValueError:
            event_type = AlarmEventType.UNKNOWN

        # Qualifier: SIA uses trailing characters
        # For simplicity, assume all are events unless restored
        qualifier = "R" if message.endswith("R") else "E"

        return AlarmEvent(
            raw_message=message,
            protocol=AlarmProtocol.SIA,
            account_code=account,
            event_code=cid_code,
            event_type=event_type,
            qualifier=qualifier,
            zone=zone,
            extra_data={"sia_code": sia_code},
        )


class AlarmReceiverService:
    """Service for receiving and processing alarms."""

    def __init__(self, db: AsyncSession):
        """Initialize alarm receiver service."""
        self.db = db
        self.contact_id_parser = ContactIDParser()
        self.sia_parser = SIAParser()
        self._accounts: dict[str, AlarmAccount] = {}
        self._event_handlers: list[Callable[[AlarmEvent, AlarmAccount | None], Awaitable[None]]] = []

    def register_account(self, account: AlarmAccount) -> None:
        """Register an alarm account."""
        self._accounts[account.account_code] = account

    def register_handler(
        self,
        handler: Callable[[AlarmEvent, AlarmAccount | None], Awaitable[None]]
    ) -> None:
        """Register an event handler."""
        self._event_handlers.append(handler)

    def parse_message(self, message: str, protocol: AlarmProtocol | None = None) -> AlarmEvent | None:
        """Parse an alarm message.

        Args:
            message: Raw alarm message
            protocol: Optional protocol hint

        Returns:
            Parsed AlarmEvent or None if parsing failed
        """
        # Try specified protocol first
        if protocol == AlarmProtocol.CONTACT_ID:
            return self.contact_id_parser.parse(message)
        elif protocol == AlarmProtocol.SIA:
            return self.sia_parser.parse(message)

        # Auto-detect protocol
        event = self.contact_id_parser.parse(message)
        if event:
            return event

        event = self.sia_parser.parse(message)
        if event:
            return event

        return None

    async def process_alarm(
        self,
        message: str,
        protocol: AlarmProtocol | None = None,
        source_ip: str | None = None,
    ) -> Alert | None:
        """Process an incoming alarm message.

        Args:
            message: Raw alarm message
            protocol: Optional protocol hint
            source_ip: Source IP address

        Returns:
            Created Alert or None
        """
        event = self.parse_message(message, protocol)
        if not event:
            return None

        # Add source IP
        if source_ip:
            event.extra_data["source_ip"] = source_ip

        # Get account info
        account = self._accounts.get(event.account_code)

        # Notify handlers
        for handler in self._event_handlers:
            try:
                await handler(event, account)
            except Exception:
                pass  # Don't let handler errors stop processing

        # Only create alerts for alarm events, not restores
        if event.is_restore:
            # Could update existing alert status here
            return None

        # Map event to alert
        alert = await self._create_alert_from_event(event, account)
        return alert

    async def _create_alert_from_event(
        self,
        event: AlarmEvent,
        account: AlarmAccount | None,
    ) -> Alert:
        """Create an alert from an alarm event."""
        # Determine severity based on event type
        severity = self._get_severity(event.event_type)

        # Build title
        title = self._get_event_title(event.event_type)
        if event.zone:
            title = f"{title} - Zone {event.zone}"

        # Build description
        description_parts = [
            f"Account: {event.account_code}",
            f"Event Code: {event.event_code}",
        ]
        if account:
            description_parts.insert(0, f"Location: {account.name}")
            if account.address:
                description_parts.append(f"Address: {account.address}")
        if event.partition:
            description_parts.append(f"Partition: {event.partition}")
        if event.user:
            description_parts.append(f"User: {event.user}")

        description = "\n".join(description_parts)

        # Create alert
        alert = Alert(
            id=uuid.uuid4(),
            title=title,
            description=description,
            alert_type="alarm_receiver",
            severity=severity,
            status=AlertStatus.PENDING,
            source=f"alarm:{event.protocol.value}",
            source_id=event.account_code,
            latitude=account.latitude if account else None,
            longitude=account.longitude if account else None,
            raw_data={
                "event": {
                    "raw_message": event.raw_message,
                    "protocol": event.protocol.value,
                    "account_code": event.account_code,
                    "event_code": event.event_code,
                    "event_type": event.event_type.value,
                    "qualifier": event.qualifier,
                    "zone": event.zone,
                    "user": event.user,
                    "partition": event.partition,
                },
                "account": {
                    "name": account.name if account else None,
                    "address": account.address if account else None,
                    "contact_name": account.contact_name if account else None,
                    "contact_phone": account.contact_phone if account else None,
                } if account else None,
            },
        )

        if account and account.agency_id:
            alert.agency_id = account.agency_id

        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    def _get_severity(self, event_type: AlarmEventType) -> AlertSeverity:
        """Get alert severity based on event type."""
        # Fire alarms are critical
        if event_type.value.startswith("11"):
            return AlertSeverity.CRITICAL

        # Medical and panic are high
        if event_type.value.startswith(("10", "12")):
            return AlertSeverity.HIGH

        # Burglary is medium-high
        if event_type.value.startswith("13"):
            return AlertSeverity.MEDIUM

        # System troubles are low
        if event_type.value.startswith("3"):
            return AlertSeverity.LOW

        # Open/close are info level
        if event_type.value.startswith("4"):
            return AlertSeverity.INFO

        return AlertSeverity.MEDIUM

    def _get_event_title(self, event_type: AlarmEventType) -> str:
        """Get human-readable title for event type."""
        titles = {
            AlarmEventType.FIRE_ALARM: "Fire Alarm",
            AlarmEventType.SMOKE_ALARM: "Smoke Alarm",
            AlarmEventType.HEAT_ALARM: "Heat Alarm",
            AlarmEventType.COMBUSTION: "Combustion Detected",
            AlarmEventType.WATER_FLOW: "Water Flow Alarm",
            AlarmEventType.PULL_STATION: "Pull Station Activated",

            AlarmEventType.MEDICAL_ALARM: "Medical Alarm",
            AlarmEventType.MEDICAL_PENDANT: "Medical Pendant Alarm",

            AlarmEventType.PANIC_ALARM: "Panic Alarm",
            AlarmEventType.DURESS: "Duress Alarm",
            AlarmEventType.SILENT_PANIC: "Silent Panic",
            AlarmEventType.AUDIBLE_PANIC: "Audible Panic",

            AlarmEventType.BURGLARY: "Burglary Alarm",
            AlarmEventType.PERIMETER: "Perimeter Alarm",
            AlarmEventType.INTERIOR: "Interior Alarm",
            AlarmEventType.ENTRY_EXIT: "Entry/Exit Alarm",
            AlarmEventType.TAMPER: "Tamper Alarm",
            AlarmEventType.SILENT_BURGLARY: "Silent Burglary",

            AlarmEventType.AC_LOSS: "AC Power Loss",
            AlarmEventType.LOW_BATTERY: "Low Battery",
            AlarmEventType.SYSTEM_TROUBLE: "System Trouble",

            AlarmEventType.OPENING: "System Opening",
            AlarmEventType.CLOSING: "System Closing",
            AlarmEventType.FAIL_TO_OPEN: "Fail to Open",
            AlarmEventType.FAIL_TO_CLOSE: "Fail to Close",

            AlarmEventType.PERIODIC_TEST: "Periodic Test",
            AlarmEventType.MANUAL_TEST: "Manual Test",
        }
        return titles.get(event_type, f"Alarm Event {event_type.value}")


class AlarmReceiverTCPServer:
    """TCP server for receiving alarm signals.

    This implements a basic receiver that can accept
    connections from alarm panels or central station software.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",  # nosec B104 - Intentional for alarm panel server
        port: int = 5000,
        receiver_service: AlarmReceiverService | None = None,
    ):
        """Initialize TCP server.

        Args:
            host: Interface to bind to. Default "0.0.0.0" accepts connections from any interface,
                  which is intentional for alarm panel connections. In production, restrict
                  via firewall or set to specific interface IP.
            port: TCP port to listen on.
            receiver_service: AlarmReceiverService instance for processing.
        """
        self.host = host
        self.port = port
        self.receiver_service = receiver_service
        self._server: asyncio.Server | None = None
        self._running = False

    async def start(self) -> None:
        """Start the TCP server."""
        self._server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port,
        )
        self._running = True

        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        """Stop the TCP server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming connection."""
        addr = writer.get_extra_info("peername")
        source_ip = addr[0] if addr else None

        try:
            while self._running:
                # Read line (most alarm protocols are line-based)
                data = await asyncio.wait_for(
                    reader.readline(),
                    timeout=60.0,
                )

                if not data:
                    break

                message = data.decode("ascii", errors="ignore").strip()
                if not message:
                    continue

                # Process the alarm
                if self.receiver_service:
                    try:
                        await self.receiver_service.process_alarm(
                            message=message,
                            source_ip=source_ip,
                        )
                    except Exception:
                        pass

                # Send acknowledgment (protocol-specific)
                # Contact ID expects specific ACK format
                writer.write(b"\x06")  # ACK
                await writer.drain()

        except asyncio.TimeoutError:
            pass
        except Exception:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

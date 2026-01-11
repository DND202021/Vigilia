# Phase 3: External Integrations

**Duration:** Weeks 11-14  
**Status:** Planned  
**Dependencies:** Phase 2 (Core Services)

## Overview

Phase 3 establishes secure, reliable connections between ERIOP and external systems critical to emergency response operations. This includes alarm systems, audio detection devices, CAD systems, GIS platforms, and agency databases.

## Objectives

1. **Alarm System Integration** - Connect commercial and municipal alarm systems
2. **Audio Detection** - Integrate Axis audio analytics for gunshot/glass break detection
3. **CAD Integration** - Bidirectional sync with Computer-Aided Dispatch systems
4. **GIS Integration** - Map layers and geospatial data from municipal GIS
5. **Agency Databases** - Personnel and vehicle databases synchronization

## Integration Architecture

### Pattern: Adapter with Circuit Breaker

```
┌─────────────────────────────────────────────────────────────────┐
│                     Integration Service                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Adapter    │  │   Adapter    │  │   Adapter    │          │
│  │  (Alarms)    │  │   (Axis)     │  │   (CAD)      │   ...    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐          │
│  │   Circuit    │  │   Circuit    │  │   Circuit    │          │
│  │   Breaker    │  │   Breaker    │  │   Breaker    │          │
│  └──────┬───────┘  └──────┴───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └────────────┬────┴────────────┬────┘                   │
│                      │                 │                        │
│              ┌───────┴───────┐ ┌───────┴───────┐               │
│              │  Event Queue  │ │  Retry Queue  │               │
│              │   (Redis)     │ │   (Redis)     │               │
│              └───────────────┘ └───────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### Circuit Breaker States

| State | Description | Behavior |
|-------|-------------|----------|
| **Closed** | Normal operation | Requests pass through |
| **Open** | Failures exceeded threshold | Requests fail fast |
| **Half-Open** | Testing recovery | Limited requests allowed |

### Configuration

```python
# config/integrations.py
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 5,        # Failures before opening
    "success_threshold": 3,        # Successes to close from half-open
    "timeout_seconds": 30,         # Time before half-open attempt
    "expected_exception": IntegrationException,
}

RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay_ms": 100,
    "max_delay_ms": 5000,
    "exponential_base": 2,
}
```

## Week 11: Alarm System Integration

### 11.1 Alarm Protocol Support

#### Supported Protocols

| Protocol | Type | Use Case |
|----------|------|----------|
| **Contact ID (Ademco)** | DTMF | Traditional alarm panels |
| **SIA DC-03-1990** | Digital | Commercial systems |
| **SIA DC-07-2001** | IP | Modern IP-based panels |
| **SIA DC-09-2013** | Internet | Cloud-connected alarms |

#### Alarm Receiver Service

```python
# src/backend/integrations/alarms/receiver.py
"""
Alarm Receiver Service

Handles incoming alarm signals from various protocols and converts
them to standardized ERIOP alert format.
"""

from enum import Enum
from typing import Protocol, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

class AlarmProtocol(Enum):
    """Supported alarm communication protocols."""
    CONTACT_ID = "contact_id"
    SIA_DC03 = "sia_dc03"
    SIA_DC07 = "sia_dc07"
    SIA_DC09 = "sia_dc09"

@dataclass
class RawAlarmSignal:
    """Raw alarm signal as received from panel."""
    protocol: AlarmProtocol
    account_number: str
    event_code: str
    zone: Optional[str]
    partition: Optional[str]
    timestamp: datetime
    raw_data: bytes

@dataclass
class StandardizedAlarm:
    """Normalized alarm format for ERIOP processing."""
    source_id: str
    source_type: str = "alarm_panel"
    event_type: str  # burglary, fire, medical, panic
    severity: str    # critical, high, medium, low
    location: dict   # address, coordinates
    zone_info: Optional[str] = None
    account_info: dict = None
    raw_signal: RawAlarmSignal = None

class AlarmDecoder(Protocol):
    """Protocol for alarm signal decoders."""
    
    async def decode(self, raw_data: bytes) -> RawAlarmSignal:
        """Decode raw bytes into structured signal."""
        ...
    
    async def validate(self, signal: RawAlarmSignal) -> bool:
        """Validate signal integrity and authenticity."""
        ...

class ContactIdDecoder:
    """
    Decoder for Ademco Contact ID protocol.
    
    Format: ACCT MT QXYZ GG CCC S
    - ACCT: 4-digit account number
    - MT: Message type (18=new, 98=restore)
    - Q: Event qualifier (1=new, 3=restore, 6=status)
    - XYZ: Event code (3 digits)
    - GG: Group/partition (2 digits)
    - CCC: Zone/user (3 digits)
    - S: Checksum
    """
    
    # Event code mappings (partial list)
    EVENT_CODES = {
        "100": ("medical", "critical", "Medical Emergency"),
        "110": ("fire", "critical", "Fire Alarm"),
        "120": ("panic", "critical", "Panic Alarm"),
        "130": ("burglary", "high", "Burglary Alarm"),
        "131": ("burglary", "high", "Perimeter Alarm"),
        "132": ("burglary", "medium", "Interior Alarm"),
        "133": ("burglary", "high", "24-Hour Zone"),
        "134": ("burglary", "medium", "Entry/Exit Alarm"),
        "137": ("tamper", "medium", "Panel Tamper"),
        "140": ("burglary", "high", "Sensor Tamper"),
        "150": ("burglary", "high", "24-Hour Non-Burglary"),
        "300": ("trouble", "low", "System Trouble"),
        "301": ("trouble", "medium", "AC Power Lost"),
        "302": ("trouble", "medium", "Low Battery"),
        "401": ("arm", "info", "Armed Away"),
        "441": ("arm", "info", "Armed Stay"),
    }
    
    async def decode(self, raw_data: bytes) -> RawAlarmSignal:
        """Decode Contact ID signal from raw bytes."""
        # Implementation details...
        pass
    
    async def validate(self, signal: RawAlarmSignal) -> bool:
        """Validate checksum and signal integrity."""
        # Implementation details...
        pass

class AlarmNormalizer:
    """
    Normalizes alarm signals from various protocols into
    standardized ERIOP format.
    """
    
    def __init__(self, account_repository, location_service):
        self.account_repo = account_repository
        self.location_service = location_service
    
    async def normalize(
        self, 
        signal: RawAlarmSignal
    ) -> StandardizedAlarm:
        """
        Convert protocol-specific signal to standard format.
        
        Args:
            signal: Raw alarm signal from decoder
            
        Returns:
            StandardizedAlarm ready for ERIOP processing
        """
        # Look up account information
        account = await self.account_repo.get_by_number(
            signal.account_number
        )
        
        # Resolve location
        location = await self.location_service.resolve(
            account.address
        )
        
        # Map event code to ERIOP types
        event_type, severity, description = self._map_event(
            signal.protocol,
            signal.event_code
        )
        
        return StandardizedAlarm(
            source_id=f"alarm:{account.id}:{signal.zone}",
            event_type=event_type,
            severity=severity,
            location={
                "address": account.address,
                "coordinates": location.coordinates,
                "premises_type": account.premises_type,
            },
            zone_info=signal.zone,
            account_info={
                "name": account.name,
                "contact": account.primary_contact,
                "phone": account.phone,
                "special_instructions": account.instructions,
            },
            raw_signal=signal,
        )
```

### 11.2 Alarm Account Database

```sql
-- migrations/V011__alarm_accounts.sql

-- Alarm monitoring accounts
CREATE TABLE alarm_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    
    -- Location
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(50) DEFAULT 'USA',
    coordinates GEOGRAPHY(POINT, 4326),
    
    -- Premises information
    premises_type VARCHAR(50) NOT NULL,  -- residential, commercial, industrial
    building_type VARCHAR(50),           -- single_family, apartment, warehouse
    floors INTEGER,
    special_hazards TEXT[],
    
    -- Contact information
    primary_contact VARCHAR(255),
    primary_phone VARCHAR(50),
    secondary_contact VARCHAR(255),
    secondary_phone VARCHAR(50),
    
    -- Monitoring details
    monitoring_company_id UUID REFERENCES monitoring_companies(id),
    contract_start DATE,
    contract_end DATE,
    service_level VARCHAR(50),  -- basic, enhanced, premium
    
    -- Special instructions
    access_instructions TEXT,
    special_instructions TEXT,
    passcode_hint VARCHAR(255),
    
    -- Jurisdiction
    primary_agency_id UUID REFERENCES agencies(id),
    fire_district_id UUID REFERENCES agencies(id),
    ems_district_id UUID REFERENCES agencies(id),
    
    -- Metadata
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Zone definitions for each account
CREATE TABLE alarm_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES alarm_accounts(id),
    zone_number VARCHAR(10) NOT NULL,
    zone_name VARCHAR(100),
    zone_type VARCHAR(50) NOT NULL,  -- door, window, motion, smoke, etc.
    location_description VARCHAR(255),
    is_24_hour BOOLEAN DEFAULT FALSE,
    is_entry_exit BOOLEAN DEFAULT FALSE,
    bypass_allowed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(account_id, zone_number)
);

-- Alarm history for pattern analysis
CREATE TABLE alarm_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES alarm_accounts(id),
    zone_id UUID REFERENCES alarm_zones(id),
    event_code VARCHAR(10) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    disposition VARCHAR(50),  -- dispatched, cancelled, false_alarm, verified
    notes TEXT,
    created_alert_id UUID REFERENCES alerts(id),
    created_incident_id UUID REFERENCES incidents(id)
);

-- Indexes for performance
CREATE INDEX idx_alarm_accounts_number ON alarm_accounts(account_number);
CREATE INDEX idx_alarm_accounts_location ON alarm_accounts USING GIST(coordinates);
CREATE INDEX idx_alarm_accounts_agency ON alarm_accounts(primary_agency_id);
CREATE INDEX idx_alarm_history_account ON alarm_history(account_id, received_at DESC);
CREATE INDEX idx_alarm_history_type ON alarm_history(event_type, received_at DESC);
```

### 11.3 Deliverables

- [ ] Contact ID decoder with checksum validation
- [ ] SIA DC-07/DC-09 IP receiver
- [ ] Alarm account management API
- [ ] Zone configuration interface
- [ ] Signal-to-alert pipeline integration
- [ ] Duplicate/false alarm detection

## Week 12: Audio Detection Integration

### 12.1 Axis Audio Analytics

```python
# src/backend/integrations/axis/audio_analytics.py
"""
Axis Audio Analytics Integration

Integrates with Axis network audio devices for:
- Gunshot detection
- Glass break detection  
- Aggression detection
- Scream detection
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import aiohttp
import asyncio

class AudioEventType(Enum):
    """Types of audio events detected by Axis analytics."""
    GUNSHOT = "gunshot"
    GLASS_BREAK = "glass_break"
    AGGRESSION = "aggression"
    SCREAM = "scream"
    EXPLOSION = "explosion"
    CAR_ALARM = "car_alarm"
    CUSTOM = "custom"

@dataclass
class AxisAudioEvent:
    """Audio event from Axis device."""
    device_id: str
    device_name: str
    event_type: AudioEventType
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    location: dict
    audio_clip_url: Optional[str] = None
    metadata: dict = None

class AxisDeviceClient:
    """
    Client for communicating with Axis audio devices.
    
    Uses VAPIX API for device management and ONVIF for
    event subscription.
    """
    
    def __init__(
        self, 
        device_ip: str,
        username: str,
        password: str,
        verify_ssl: bool = True
    ):
        self.device_ip = device_ip
        self.auth = aiohttp.BasicAuth(username, password)
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{device_ip}"
        
    async def get_device_info(self) -> dict:
        """Retrieve device information via VAPIX."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/axis-cgi/basicdeviceinfo.cgi"
            async with session.get(
                url, 
                auth=self.auth,
                ssl=self.verify_ssl
            ) as response:
                return await response.json()
    
    async def get_audio_analytics_config(self) -> dict:
        """Get current audio analytics configuration."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/axis-cgi/param.cgi"
            params = {
                "action": "list",
                "group": "AudioAnalytics"
            }
            async with session.get(
                url,
                params=params,
                auth=self.auth,
                ssl=self.verify_ssl
            ) as response:
                return await response.text()
    
    async def configure_detection(
        self,
        event_type: AudioEventType,
        sensitivity: int = 50,
        enabled: bool = True
    ) -> bool:
        """
        Configure audio detection parameters.
        
        Args:
            event_type: Type of audio event to configure
            sensitivity: Detection sensitivity (0-100)
            enabled: Whether detection is enabled
            
        Returns:
            True if configuration successful
        """
        # Implementation via VAPIX parameter API
        pass
    
    async def get_audio_clip(
        self, 
        event_timestamp: datetime,
        duration_seconds: int = 10
    ) -> bytes:
        """
        Retrieve audio clip around event timestamp.
        
        Args:
            event_timestamp: When the event occurred
            duration_seconds: Duration of clip to retrieve
            
        Returns:
            Audio data in WAV format
        """
        # Implementation via media API
        pass

class AxisEventSubscriber:
    """
    Subscribes to real-time events from Axis devices
    using ONVIF event service.
    """
    
    def __init__(self, devices: list[AxisDeviceClient]):
        self.devices = devices
        self.event_handlers = []
        self._running = False
        
    def on_event(self, handler):
        """Register event handler callback."""
        self.event_handlers.append(handler)
        
    async def start(self):
        """Start listening for events from all devices."""
        self._running = True
        tasks = [
            self._subscribe_device(device) 
            for device in self.devices
        ]
        await asyncio.gather(*tasks)
        
    async def stop(self):
        """Stop listening for events."""
        self._running = False
        
    async def _subscribe_device(self, device: AxisDeviceClient):
        """Subscribe to events from a single device."""
        # ONVIF PullPoint subscription implementation
        while self._running:
            try:
                events = await self._pull_events(device)
                for event in events:
                    await self._dispatch_event(event)
            except Exception as e:
                # Log error, wait, and retry
                await asyncio.sleep(5)
                
    async def _dispatch_event(self, event: AxisAudioEvent):
        """Dispatch event to all registered handlers."""
        for handler in self.event_handlers:
            try:
                await handler(event)
            except Exception as e:
                # Log handler error but continue
                pass

class AudioAlertGenerator:
    """
    Converts Axis audio events to ERIOP alerts.
    """
    
    # Mapping of audio events to alert priorities
    PRIORITY_MAP = {
        AudioEventType.GUNSHOT: "critical",
        AudioEventType.EXPLOSION: "critical",
        AudioEventType.GLASS_BREAK: "high",
        AudioEventType.AGGRESSION: "high",
        AudioEventType.SCREAM: "medium",
        AudioEventType.CAR_ALARM: "low",
    }
    
    # Confidence thresholds for auto-dispatch
    CONFIDENCE_THRESHOLDS = {
        AudioEventType.GUNSHOT: 0.85,
        AudioEventType.EXPLOSION: 0.85,
        AudioEventType.GLASS_BREAK: 0.75,
        AudioEventType.AGGRESSION: 0.80,
        AudioEventType.SCREAM: 0.70,
    }
    
    def __init__(self, alert_service, device_registry):
        self.alert_service = alert_service
        self.device_registry = device_registry
        
    async def process_event(self, event: AxisAudioEvent):
        """
        Process audio event and create alert if warranted.
        
        Args:
            event: Audio event from Axis device
        """
        # Get device location from registry
        device_info = await self.device_registry.get(event.device_id)
        
        # Determine if confidence meets threshold
        threshold = self.CONFIDENCE_THRESHOLDS.get(
            event.event_type, 0.70
        )
        
        if event.confidence < threshold:
            # Log low-confidence event but don't alert
            return
            
        # Create alert
        alert = await self.alert_service.create({
            "source_type": "audio_analytics",
            "source_id": event.device_id,
            "alert_type": event.event_type.value,
            "priority": self.PRIORITY_MAP.get(event.event_type, "medium"),
            "title": f"{event.event_type.value.replace('_', ' ').title()} Detected",
            "description": (
                f"Audio analytics detected {event.event_type.value} "
                f"at {device_info.name} with {event.confidence:.0%} confidence"
            ),
            "location": device_info.location,
            "metadata": {
                "device_id": event.device_id,
                "device_name": device_info.name,
                "confidence": event.confidence,
                "audio_clip_url": event.audio_clip_url,
            },
        })
        
        # Auto-create incident for critical events
        if (
            self.PRIORITY_MAP.get(event.event_type) == "critical"
            and event.confidence >= 0.90
        ):
            await self.alert_service.convert_to_incident(
                alert.id,
                auto_dispatch=True
            )
```

### 12.2 Deliverables

- [ ] Axis VAPIX client library
- [ ] ONVIF event subscription service
- [ ] Audio device registry and management
- [ ] Event-to-alert pipeline
- [ ] Audio clip storage and retrieval
- [ ] Confidence-based auto-dispatch rules

## Week 13: CAD System Integration

### 13.1 CAD Integration Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      ERIOP Platform                           │
├──────────────────────────────────────────────────────────────┤
│  Incident Service  ◄──────────►  CAD Adapter Service          │
└──────────────────────────────────────────────────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
            ┌───────▼───────┐     ┌───────▼───────┐     ┌───────▼───────┐
            │  Hexagon CAD  │     │  Tyler CAD    │     │  Motorola     │
            │   Connector   │     │   Connector   │     │  PremierOne   │
            └───────────────┘     └───────────────┘     └───────────────┘
```

### 13.2 CAD Adapter Interface

```python
# src/backend/integrations/cad/base.py
"""
CAD System Integration Base Classes

Provides abstract interfaces for CAD system integration,
supporting bidirectional sync of incidents and units.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, AsyncIterator

class CADIncidentStatus(Enum):
    """Standard CAD incident statuses."""
    PENDING = "pending"
    DISPATCHED = "dispatched"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    CLEARED = "cleared"
    CANCELLED = "cancelled"

class CADUnitStatus(Enum):
    """Standard CAD unit statuses."""
    AVAILABLE = "available"
    BUSY = "busy"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    AT_HOSPITAL = "at_hospital"
    OUT_OF_SERVICE = "out_of_service"

@dataclass
class CADIncident:
    """Incident data from CAD system."""
    cad_incident_id: str
    incident_type: str
    priority: int
    status: CADIncidentStatus
    location_address: str
    location_coordinates: Optional[tuple] = None
    caller_name: Optional[str] = None
    caller_phone: Optional[str] = None
    narrative: Optional[str] = None
    assigned_units: list[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    metadata: dict = None

@dataclass
class CADUnit:
    """Unit/resource data from CAD system."""
    cad_unit_id: str
    unit_name: str
    unit_type: str  # police, fire, ems, etc.
    status: CADUnitStatus
    current_incident_id: Optional[str] = None
    location: Optional[tuple] = None
    personnel: list[str] = None
    capabilities: list[str] = None

class CADAdapter(ABC):
    """
    Abstract base class for CAD system adapters.
    
    Each CAD system (Hexagon, Tyler, Motorola, etc.) must
    implement this interface for integration with ERIOP.
    """
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to CAD system."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to CAD system."""
        pass
    
    @abstractmethod
    async def health_check(self) -> dict:
        """Check CAD system connectivity and status."""
        pass
    
    # Incident operations
    
    @abstractmethod
    async def get_incident(
        self, 
        cad_incident_id: str
    ) -> Optional[CADIncident]:
        """Retrieve single incident from CAD."""
        pass
    
    @abstractmethod
    async def get_active_incidents(self) -> list[CADIncident]:
        """Retrieve all active incidents from CAD."""
        pass
    
    @abstractmethod
    async def create_incident(
        self, 
        incident: CADIncident
    ) -> str:
        """
        Create new incident in CAD system.
        
        Returns:
            CAD system's incident ID
        """
        pass
    
    @abstractmethod
    async def update_incident(
        self, 
        cad_incident_id: str,
        updates: dict
    ) -> bool:
        """Update existing incident in CAD."""
        pass
    
    @abstractmethod
    async def add_incident_narrative(
        self, 
        cad_incident_id: str,
        text: str
    ) -> bool:
        """Add narrative/notes to incident."""
        pass
    
    # Unit operations
    
    @abstractmethod
    async def get_unit(
        self, 
        cad_unit_id: str
    ) -> Optional[CADUnit]:
        """Retrieve single unit from CAD."""
        pass
    
    @abstractmethod
    async def get_available_units(
        self, 
        unit_type: Optional[str] = None
    ) -> list[CADUnit]:
        """Retrieve available units, optionally filtered by type."""
        pass
    
    @abstractmethod
    async def dispatch_unit(
        self, 
        cad_unit_id: str,
        cad_incident_id: str
    ) -> bool:
        """Dispatch unit to incident."""
        pass
    
    @abstractmethod
    async def update_unit_status(
        self, 
        cad_unit_id: str,
        status: CADUnitStatus
    ) -> bool:
        """Update unit status."""
        pass
    
    # Real-time updates
    
    @abstractmethod
    async def subscribe_incidents(self) -> AsyncIterator[CADIncident]:
        """Subscribe to real-time incident updates."""
        pass
    
    @abstractmethod
    async def subscribe_units(self) -> AsyncIterator[CADUnit]:
        """Subscribe to real-time unit updates."""
        pass
```

### 13.3 Synchronization Service

```python
# src/backend/integrations/cad/sync_service.py
"""
CAD Synchronization Service

Manages bidirectional synchronization between ERIOP
and external CAD systems.
"""

import asyncio
from datetime import datetime
from typing import Optional

class CADSyncService:
    """
    Bidirectional synchronization between ERIOP and CAD.
    
    Handles:
    - Initial full sync
    - Real-time incremental sync
    - Conflict resolution
    - Mapping between systems
    """
    
    def __init__(
        self,
        cad_adapter: CADAdapter,
        incident_service,
        resource_service,
        mapping_repository
    ):
        self.cad = cad_adapter
        self.incidents = incident_service
        self.resources = resource_service
        self.mappings = mapping_repository
        self._sync_task = None
        
    async def start_sync(self):
        """Start continuous synchronization."""
        # Initial full sync
        await self._full_sync()
        
        # Start real-time subscriptions
        self._sync_task = asyncio.create_task(
            self._real_time_sync()
        )
        
    async def stop_sync(self):
        """Stop synchronization."""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
                
    async def _full_sync(self):
        """Perform full synchronization of all active data."""
        # Sync active incidents from CAD to ERIOP
        cad_incidents = await self.cad.get_active_incidents()
        for cad_incident in cad_incidents:
            await self._sync_incident_from_cad(cad_incident)
            
        # Sync available units
        cad_units = await self.cad.get_available_units()
        for cad_unit in cad_units:
            await self._sync_unit_from_cad(cad_unit)
            
    async def _real_time_sync(self):
        """Handle real-time updates from CAD."""
        # Run incident and unit subscriptions concurrently
        await asyncio.gather(
            self._handle_incident_updates(),
            self._handle_unit_updates()
        )
        
    async def _handle_incident_updates(self):
        """Process real-time incident updates."""
        async for cad_incident in self.cad.subscribe_incidents():
            try:
                await self._sync_incident_from_cad(cad_incident)
            except Exception as e:
                # Log error but continue processing
                pass
                
    async def _sync_incident_from_cad(
        self, 
        cad_incident: CADIncident
    ):
        """
        Sync single incident from CAD to ERIOP.
        
        Handles:
        - Creating new incidents
        - Updating existing incidents
        - Conflict resolution
        """
        # Check if we have a mapping
        mapping = await self.mappings.get_by_cad_id(
            "incident", 
            cad_incident.cad_incident_id
        )
        
        if mapping:
            # Update existing ERIOP incident
            await self._update_eriop_incident(
                mapping.eriop_id,
                cad_incident
            )
        else:
            # Create new ERIOP incident
            eriop_incident = await self._create_eriop_incident(
                cad_incident
            )
            # Store mapping
            await self.mappings.create({
                "entity_type": "incident",
                "cad_id": cad_incident.cad_incident_id,
                "eriop_id": eriop_incident.id,
            })
            
    async def push_to_cad(self, eriop_incident_id: str):
        """
        Push ERIOP incident to CAD system.
        
        Used when incidents originate in ERIOP (e.g., from alerts).
        """
        # Get ERIOP incident
        incident = await self.incidents.get(eriop_incident_id)
        
        # Check for existing mapping
        mapping = await self.mappings.get_by_eriop_id(
            "incident",
            eriop_incident_id
        )
        
        if mapping:
            # Update in CAD
            await self.cad.update_incident(
                mapping.cad_id,
                self._to_cad_format(incident)
            )
        else:
            # Create in CAD
            cad_id = await self.cad.create_incident(
                self._to_cad_incident(incident)
            )
            # Store mapping
            await self.mappings.create({
                "entity_type": "incident",
                "cad_id": cad_id,
                "eriop_id": eriop_incident_id,
            })
```

### 13.3 Deliverables

- [ ] CAD adapter interface specification
- [ ] At least one production CAD connector (TBD based on agency)
- [ ] Bidirectional sync service
- [ ] ID mapping repository
- [ ] Conflict resolution logic
- [ ] Real-time update pipeline

## Week 14: GIS Integration

### 14.1 GIS Data Sources

```python
# src/backend/integrations/gis/service.py
"""
GIS Integration Service

Provides geographic information services including:
- Address geocoding/reverse geocoding
- Jurisdiction boundary lookup
- Map layer management
- Routing and distance calculations
"""

from dataclasses import dataclass
from typing import Optional, List
import aiohttp

@dataclass
class GeocodedAddress:
    """Result of geocoding operation."""
    formatted_address: str
    coordinates: tuple[float, float]  # (lat, lon)
    confidence: float
    address_components: dict
    source: str  # esri, google, local

@dataclass
class Jurisdiction:
    """Jurisdiction/district information."""
    id: str
    name: str
    type: str  # police, fire, ems, city, county
    agency_id: Optional[str]
    boundaries: dict  # GeoJSON
    
@dataclass
class MapLayer:
    """Map layer definition."""
    id: str
    name: str
    type: str  # vector, raster, feature
    source_url: str
    visible_by_default: bool
    min_zoom: int
    max_zoom: int
    style: dict

class GISService:
    """
    Central GIS service for ERIOP.
    
    Integrates with:
    - Municipal ArcGIS Enterprise
    - OpenStreetMap/Nominatim
    - ESRI services
    """
    
    def __init__(
        self,
        arcgis_config: dict,
        esri_api_key: Optional[str] = None
    ):
        self.arcgis_url = arcgis_config["url"]
        self.arcgis_token = arcgis_config.get("token")
        self.esri_key = esri_api_key
        
    async def geocode(
        self, 
        address: str,
        restrict_to_jurisdiction: Optional[str] = None
    ) -> List[GeocodedAddress]:
        """
        Geocode address to coordinates.
        
        Tries local municipal geocoder first, falls back to ESRI.
        
        Args:
            address: Address string to geocode
            restrict_to_jurisdiction: Limit results to jurisdiction
            
        Returns:
            List of geocoding candidates, ordered by confidence
        """
        # Try municipal ArcGIS first
        results = await self._geocode_arcgis(address)
        
        if not results:
            # Fall back to ESRI World Geocoder
            results = await self._geocode_esri(address)
            
        # Filter by jurisdiction if specified
        if restrict_to_jurisdiction and results:
            results = [
                r for r in results
                if await self._in_jurisdiction(
                    r.coordinates, 
                    restrict_to_jurisdiction
                )
            ]
            
        return results
        
    async def reverse_geocode(
        self, 
        lat: float, 
        lon: float
    ) -> Optional[GeocodedAddress]:
        """
        Reverse geocode coordinates to address.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Geocoded address or None if not found
        """
        pass
        
    async def get_jurisdiction(
        self, 
        lat: float, 
        lon: float,
        jurisdiction_type: Optional[str] = None
    ) -> List[Jurisdiction]:
        """
        Find jurisdictions containing a point.
        
        Args:
            lat: Latitude
            lon: Longitude
            jurisdiction_type: Filter by type (police, fire, ems)
            
        Returns:
            List of matching jurisdictions
        """
        # Query jurisdiction boundary layers
        layers = {
            "police": "police_districts",
            "fire": "fire_districts", 
            "ems": "ems_districts",
        }
        
        results = []
        
        for jtype, layer_name in layers.items():
            if jurisdiction_type and jtype != jurisdiction_type:
                continue
                
            jurisdiction = await self._query_boundary_layer(
                layer_name,
                lat,
                lon
            )
            if jurisdiction:
                results.append(jurisdiction)
                
        return results
        
    async def get_routing(
        self, 
        origin: tuple[float, float],
        destination: tuple[float, float],
        avoid_traffic: bool = True
    ) -> dict:
        """
        Calculate route between two points.
        
        Returns:
            Route geometry, distance, and estimated time
        """
        pass
        
    async def get_map_layers(
        self, 
        layer_type: Optional[str] = None
    ) -> List[MapLayer]:
        """
        Get available map layers.
        
        Args:
            layer_type: Filter by layer type
            
        Returns:
            List of map layer definitions
        """
        # Query ArcGIS for available layers
        pass
```

### 14.2 Deliverables

- [ ] Geocoding service with fallback chain
- [ ] Jurisdiction boundary lookup
- [ ] Map layer management API
- [ ] ArcGIS Enterprise connector
- [ ] Route calculation service
- [ ] GIS data caching layer

## Testing Requirements

### Integration Tests

```python
# tests/integration/test_alarm_integration.py
"""Integration tests for alarm system."""

import pytest
from unittest.mock import AsyncMock

@pytest.mark.integration
class TestAlarmIntegration:
    """Tests for alarm receiver and processing."""
    
    async def test_contact_id_decoding(self):
        """Test Contact ID signal decoding."""
        # Arrange
        raw_signal = b"1234180130001"  # Example Contact ID
        decoder = ContactIdDecoder()
        
        # Act
        signal = await decoder.decode(raw_signal)
        
        # Assert
        assert signal.account_number == "1234"
        assert signal.event_code == "130"  # Burglary
        
    async def test_alarm_creates_alert(self):
        """Test that valid alarm creates ERIOP alert."""
        # Arrange
        alert_service = AsyncMock()
        normalizer = AlarmNormalizer(
            account_repo=MockAccountRepo(),
            location_service=MockLocationService()
        )
        
        # Act
        alarm = await normalizer.normalize(sample_signal)
        await alert_generator.process(alarm)
        
        # Assert
        alert_service.create.assert_called_once()
        
    async def test_duplicate_alarm_handling(self):
        """Test duplicate alarms are properly handled."""
        pass
```

## Security Considerations

### Integration Authentication

All external integrations must:

1. **Use TLS 1.3** for all connections
2. **Authenticate** using API keys, OAuth 2.0, or certificates
3. **Log** all integration activity to audit trail
4. **Rate limit** incoming data to prevent DoS
5. **Validate** all incoming data before processing

### Credential Management

```python
# Integration credentials stored in secure vault
INTEGRATION_SECRETS = {
    "alarm_receiver": {
        "type": "api_key",
        "vault_path": "secret/integrations/alarm",
    },
    "axis_devices": {
        "type": "certificate",
        "vault_path": "secret/integrations/axis",
    },
    "cad_system": {
        "type": "oauth2",
        "vault_path": "secret/integrations/cad",
    },
    "arcgis": {
        "type": "token",
        "vault_path": "secret/integrations/arcgis",
    },
}
```

## Success Criteria

| Metric | Target |
|--------|--------|
| Alarm processing latency | < 2 seconds |
| Audio event latency | < 3 seconds |
| CAD sync latency | < 5 seconds |
| Geocoding accuracy | > 95% |
| Integration uptime | > 99.5% |
| Circuit breaker recovery | < 30 seconds |

## Dependencies

### External Systems (To Be Confirmed)

- [ ] Alarm monitoring company and protocols
- [ ] Axis device inventory and credentials
- [ ] CAD system vendor and API documentation
- [ ] Municipal ArcGIS Enterprise access
- [ ] Agency database access

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| CAD vendor delays | Develop with mock adapter first |
| Protocol variations | Build flexible decoder architecture |
| Network instability | Implement robust retry/circuit breaker |
| Data inconsistency | Conflict resolution with manual override |

---

**Next Phase:** [Phase 4 - User Interfaces](./PHASE_04_USER_INTERFACES.md)

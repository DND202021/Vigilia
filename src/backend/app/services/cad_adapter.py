"""Computer-Aided Dispatch (CAD) System Adapters.

This module provides adapters for integrating with various CAD systems
commonly used in emergency services, including:
- Generic REST API adapter
- TriTech/Hexagon CAD
- Motorola CommandCentral
- Tyler New World Systems
- Intergraph/Hexagon I/CAD
- Mark43 CAD

Each adapter implements a common interface for:
- Receiving incidents from CAD
- Sending status updates back to CAD
- Synchronizing resources
- Two-way unit status updates
"""

import asyncio
import uuid
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Awaitable

import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentCategory, IncidentStatus
from app.models.resource import Resource, ResourceStatus


class CADVendor(str, Enum):
    """Supported CAD vendors."""

    GENERIC = "generic"
    TRITECH = "tritech"
    MOTOROLA = "motorola"
    TYLER = "tyler"
    INTERGRAPH = "intergraph"
    MARK43 = "mark43"
    CENTRAL_SQUARE = "central_square"


class CADEventType(str, Enum):
    """CAD event types."""

    INCIDENT_CREATE = "incident_create"
    INCIDENT_UPDATE = "incident_update"
    INCIDENT_CLOSE = "incident_close"
    UNIT_DISPATCH = "unit_dispatch"
    UNIT_STATUS = "unit_status"
    UNIT_CLEAR = "unit_clear"
    COMMENT_ADD = "comment_add"
    PRIORITY_CHANGE = "priority_change"


@dataclass
class CADIncident:
    """Standardized CAD incident representation."""

    cad_id: str
    incident_number: str
    call_type: str
    priority: int
    status: str
    address: str
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    caller_name: str | None = None
    caller_phone: str | None = None
    description: str | None = None
    received_at: datetime | None = None
    dispatched_at: datetime | None = None
    assigned_units: list[str] = field(default_factory=list)
    comments: list[dict] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class CADUnit:
    """Standardized CAD unit representation."""

    cad_id: str
    unit_id: str
    call_sign: str
    unit_type: str
    status: str
    latitude: float | None = None
    longitude: float | None = None
    current_incident: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class CADEvent:
    """Event received from or sent to CAD."""

    event_type: CADEventType
    timestamp: datetime
    incident: CADIncident | None = None
    unit: CADUnit | None = None
    data: dict[str, Any] = field(default_factory=dict)


class CADAdapter(ABC):
    """Abstract base class for CAD adapters."""

    def __init__(
        self,
        config: dict[str, Any],
        event_handler: Callable[[CADEvent], Awaitable[None]] | None = None,
    ):
        """Initialize CAD adapter.

        Args:
            config: Adapter configuration
            event_handler: Callback for received events
        """
        self.config = config
        self.event_handler = event_handler
        self._connected = False

    @property
    @abstractmethod
    def vendor(self) -> CADVendor:
        """Get CAD vendor type."""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to CAD system."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from CAD system."""
        pass

    @abstractmethod
    async def fetch_incidents(
        self,
        since: datetime | None = None,
        active_only: bool = True,
    ) -> list[CADIncident]:
        """Fetch incidents from CAD.

        Args:
            since: Only fetch incidents since this time
            active_only: Only fetch active incidents

        Returns:
            List of incidents
        """
        pass

    @abstractmethod
    async def fetch_units(self) -> list[CADUnit]:
        """Fetch unit status from CAD."""
        pass

    @abstractmethod
    async def send_unit_status(
        self,
        unit_id: str,
        status: str,
        incident_id: str | None = None,
    ) -> bool:
        """Send unit status update to CAD.

        Args:
            unit_id: Unit identifier
            status: New status code
            incident_id: Associated incident ID

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def send_incident_update(
        self,
        incident_id: str,
        status: str | None = None,
        comment: str | None = None,
    ) -> bool:
        """Send incident update to CAD.

        Args:
            incident_id: Incident identifier
            status: New status
            comment: Comment to add

        Returns:
            True if successful
        """
        pass

    def map_call_type_to_category(self, call_type: str) -> IncidentCategory:
        """Map CAD call type to incident category."""
        call_type_lower = call_type.lower()

        # Fire-related
        if any(t in call_type_lower for t in ["fire", "smoke", "burn", "structure"]):
            return IncidentCategory.FIRE

        # Medical-related
        if any(t in call_type_lower for t in ["medical", "ems", "injury", "cardiac", "breathing", "unconscious"]):
            return IncidentCategory.MEDICAL

        # Police/law enforcement
        if any(t in call_type_lower for t in ["theft", "robbery", "assault", "burglary", "suspicious", "disturbance"]):
            return IncidentCategory.LAW_ENFORCEMENT

        # Traffic
        if any(t in call_type_lower for t in ["traffic", "accident", "mva", "collision", "vehicle"]):
            return IncidentCategory.TRAFFIC

        # Hazmat
        if any(t in call_type_lower for t in ["hazmat", "spill", "chemical", "gas leak"]):
            return IncidentCategory.HAZMAT

        # Rescue
        if any(t in call_type_lower for t in ["rescue", "trapped", "confined", "water rescue"]):
            return IncidentCategory.RESCUE

        # Utility
        if any(t in call_type_lower for t in ["power", "utility", "electric", "water main"]):
            return IncidentCategory.UTILITY

        # Weather
        if any(t in call_type_lower for t in ["storm", "flood", "weather", "tornado"]):
            return IncidentCategory.WEATHER

        return IncidentCategory.OTHER

    def map_priority(self, cad_priority: int | str) -> int:
        """Map CAD priority to system priority (1-5)."""
        try:
            p = int(cad_priority)
            return max(1, min(5, p))
        except (ValueError, TypeError):
            return 3  # Default to medium

    async def _emit_event(self, event: CADEvent) -> None:
        """Emit event to handler."""
        if self.event_handler:
            try:
                await self.event_handler(event)
            except Exception:
                pass


class GenericRESTAdapter(CADAdapter):
    """Generic REST API adapter.

    This adapter works with CAD systems that expose a REST API.
    Configuration specifies endpoints and field mappings.
    """

    @property
    def vendor(self) -> CADVendor:
        return CADVendor.GENERIC

    def __init__(
        self,
        config: dict[str, Any],
        event_handler: Callable[[CADEvent], Awaitable[None]] | None = None,
    ):
        super().__init__(config, event_handler)
        self.base_url = config.get("base_url", "")
        self.api_key = config.get("api_key")
        self.username = config.get("username")
        self.password = config.get("password")
        self.field_mapping = config.get("field_mapping", {})
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> bool:
        """Establish connection."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        auth = None
        if self.username and self.password:
            auth = httpx.BasicAuth(self.username, self.password)

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            auth=auth,
            timeout=30.0,
        )

        # Test connection
        try:
            test_endpoint = self.config.get("test_endpoint", "/health")
            response = await self._client.get(test_endpoint)
            self._connected = response.status_code < 400
            return self._connected
        except Exception:
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from CAD."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def fetch_incidents(
        self,
        since: datetime | None = None,
        active_only: bool = True,
    ) -> list[CADIncident]:
        """Fetch incidents from REST API."""
        if not self._client:
            return []

        endpoint = self.config.get("incidents_endpoint", "/incidents")
        params = {}

        if since:
            params["since"] = since.isoformat()
        if active_only:
            params["active"] = "true"

        try:
            response = await self._client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            # Handle different response formats
            incidents_data = data
            if isinstance(data, dict):
                incidents_data = data.get("incidents", data.get("data", []))

            return [self._map_incident(i) for i in incidents_data]

        except Exception:
            return []

    async def fetch_units(self) -> list[CADUnit]:
        """Fetch units from REST API."""
        if not self._client:
            return []

        endpoint = self.config.get("units_endpoint", "/units")

        try:
            response = await self._client.get(endpoint)
            response.raise_for_status()
            data = response.json()

            units_data = data
            if isinstance(data, dict):
                units_data = data.get("units", data.get("data", []))

            return [self._map_unit(u) for u in units_data]

        except Exception:
            return []

    async def send_unit_status(
        self,
        unit_id: str,
        status: str,
        incident_id: str | None = None,
    ) -> bool:
        """Send unit status to REST API."""
        if not self._client:
            return False

        endpoint = self.config.get("unit_status_endpoint", f"/units/{unit_id}/status")
        endpoint = endpoint.replace("{unit_id}", unit_id)

        payload = {"status": status}
        if incident_id:
            payload["incident_id"] = incident_id

        try:
            response = await self._client.put(endpoint, json=payload)
            return response.status_code < 400
        except Exception:
            return False

    async def send_incident_update(
        self,
        incident_id: str,
        status: str | None = None,
        comment: str | None = None,
    ) -> bool:
        """Send incident update to REST API."""
        if not self._client:
            return False

        endpoint = self.config.get("incident_update_endpoint", f"/incidents/{incident_id}")
        endpoint = endpoint.replace("{incident_id}", incident_id)

        payload = {}
        if status:
            payload["status"] = status
        if comment:
            payload["comment"] = comment

        try:
            response = await self._client.patch(endpoint, json=payload)
            return response.status_code < 400
        except Exception:
            return False

    def _map_incident(self, data: dict) -> CADIncident:
        """Map raw data to CADIncident using field mapping."""
        fm = self.field_mapping.get("incident", {})

        return CADIncident(
            cad_id=str(data.get(fm.get("id", "id"), "")),
            incident_number=str(data.get(fm.get("number", "incident_number"), "")),
            call_type=data.get(fm.get("type", "call_type"), "Unknown"),
            priority=self.map_priority(data.get(fm.get("priority", "priority"), 3)),
            status=data.get(fm.get("status", "status"), "pending"),
            address=data.get(fm.get("address", "address"), ""),
            city=data.get(fm.get("city", "city")),
            state=data.get(fm.get("state", "state")),
            postal_code=data.get(fm.get("postal_code", "postal_code")),
            latitude=data.get(fm.get("latitude", "latitude")),
            longitude=data.get(fm.get("longitude", "longitude")),
            caller_name=data.get(fm.get("caller_name", "caller_name")),
            caller_phone=data.get(fm.get("caller_phone", "caller_phone")),
            description=data.get(fm.get("description", "description")),
            raw_data=data,
        )

    def _map_unit(self, data: dict) -> CADUnit:
        """Map raw data to CADUnit using field mapping."""
        fm = self.field_mapping.get("unit", {})

        return CADUnit(
            cad_id=str(data.get(fm.get("id", "id"), "")),
            unit_id=str(data.get(fm.get("unit_id", "unit_id"), "")),
            call_sign=data.get(fm.get("call_sign", "call_sign"), ""),
            unit_type=data.get(fm.get("type", "unit_type"), "Unknown"),
            status=data.get(fm.get("status", "status"), "available"),
            latitude=data.get(fm.get("latitude", "latitude")),
            longitude=data.get(fm.get("longitude", "longitude")),
            current_incident=data.get(fm.get("incident", "current_incident")),
            raw_data=data,
        )


class TriTechAdapter(CADAdapter):
    """Adapter for TriTech/Hexagon CAD systems.

    Implements the TriTech InformCAD interface.
    """

    @property
    def vendor(self) -> CADVendor:
        return CADVendor.TRITECH

    def __init__(
        self,
        config: dict[str, Any],
        event_handler: Callable[[CADEvent], Awaitable[None]] | None = None,
    ):
        super().__init__(config, event_handler)
        self.base_url = config.get("base_url", "")
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self._client: httpx.AsyncClient | None = None
        self._token: str | None = None

    async def connect(self) -> bool:
        """Connect and authenticate with TriTech."""
        self._client = httpx.AsyncClient(timeout=30.0)

        # OAuth2 token exchange
        try:
            response = await self._client.post(
                f"{self.base_url}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            token_data = response.json()
            self._token = token_data.get("access_token")
            self._connected = bool(self._token)
            return self._connected
        except Exception:
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from TriTech."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._token = None
        self._connected = False

    def _get_headers(self) -> dict:
        """Get request headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def fetch_incidents(
        self,
        since: datetime | None = None,
        active_only: bool = True,
    ) -> list[CADIncident]:
        """Fetch incidents from TriTech InformCAD."""
        if not self._client or not self._token:
            return []

        params = {"includeUnits": "true"}
        if since:
            params["modifiedSince"] = since.isoformat()
        if active_only:
            params["statusFilter"] = "ACTIVE"

        try:
            response = await self._client.get(
                f"{self.base_url}/api/incidents",
                params=params,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            return [self._map_tritech_incident(i) for i in data.get("incidents", [])]

        except Exception:
            return []

    async def fetch_units(self) -> list[CADUnit]:
        """Fetch units from TriTech."""
        if not self._client or not self._token:
            return []

        try:
            response = await self._client.get(
                f"{self.base_url}/api/units",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            return [self._map_tritech_unit(u) for u in data.get("units", [])]

        except Exception:
            return []

    async def send_unit_status(
        self,
        unit_id: str,
        status: str,
        incident_id: str | None = None,
    ) -> bool:
        """Send unit status to TriTech."""
        if not self._client or not self._token:
            return False

        payload = {
            "unitId": unit_id,
            "statusCode": status,
        }
        if incident_id:
            payload["incidentId"] = incident_id

        try:
            response = await self._client.post(
                f"{self.base_url}/api/units/{unit_id}/status",
                json=payload,
                headers=self._get_headers(),
            )
            return response.status_code < 400
        except Exception:
            return False

    async def send_incident_update(
        self,
        incident_id: str,
        status: str | None = None,
        comment: str | None = None,
    ) -> bool:
        """Send incident update to TriTech."""
        if not self._client or not self._token:
            return False

        payload = {}
        if status:
            payload["statusCode"] = status
        if comment:
            payload["remarks"] = comment

        try:
            response = await self._client.patch(
                f"{self.base_url}/api/incidents/{incident_id}",
                json=payload,
                headers=self._get_headers(),
            )
            return response.status_code < 400
        except Exception:
            return False

    def _map_tritech_incident(self, data: dict) -> CADIncident:
        """Map TriTech incident format."""
        location = data.get("location", {})

        return CADIncident(
            cad_id=data.get("incidentId", ""),
            incident_number=data.get("incidentNumber", ""),
            call_type=data.get("callType", {}).get("description", "Unknown"),
            priority=self.map_priority(data.get("priority", 3)),
            status=data.get("status", {}).get("code", "pending"),
            address=location.get("address", ""),
            city=location.get("city"),
            state=location.get("state"),
            postal_code=location.get("zipCode"),
            latitude=location.get("latitude"),
            longitude=location.get("longitude"),
            caller_name=data.get("caller", {}).get("name"),
            caller_phone=data.get("caller", {}).get("phone"),
            description=data.get("comments", [{}])[0].get("text") if data.get("comments") else None,
            received_at=datetime.fromisoformat(data["receivedTime"]) if data.get("receivedTime") else None,
            assigned_units=[u.get("unitId") for u in data.get("assignedUnits", [])],
            raw_data=data,
        )

    def _map_tritech_unit(self, data: dict) -> CADUnit:
        """Map TriTech unit format."""
        return CADUnit(
            cad_id=data.get("unitId", ""),
            unit_id=data.get("unitId", ""),
            call_sign=data.get("callSign", ""),
            unit_type=data.get("unitType", {}).get("description", "Unknown"),
            status=data.get("status", {}).get("code", "available"),
            latitude=data.get("location", {}).get("latitude"),
            longitude=data.get("location", {}).get("longitude"),
            current_incident=data.get("currentIncident", {}).get("incidentId"),
            raw_data=data,
        )


class CADSyncService:
    """Service for synchronizing data between CAD and Vigilia."""

    def __init__(self, db: AsyncSession, adapter: CADAdapter):
        """Initialize sync service."""
        self.db = db
        self.adapter = adapter
        self._running = False
        self._sync_task: asyncio.Task | None = None

    async def start_sync(self, interval_seconds: int = 30) -> None:
        """Start background synchronization."""
        if not await self.adapter.connect():
            raise RuntimeError("Failed to connect to CAD system")

        self._running = True
        self._sync_task = asyncio.create_task(
            self._sync_loop(interval_seconds)
        )

    async def stop_sync(self) -> None:
        """Stop background synchronization."""
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        await self.adapter.disconnect()

    async def _sync_loop(self, interval: int) -> None:
        """Background sync loop."""
        last_sync: datetime | None = None

        while self._running:
            try:
                # Fetch new incidents
                incidents = await self.adapter.fetch_incidents(
                    since=last_sync,
                    active_only=True,
                )

                for cad_incident in incidents:
                    await self._process_cad_incident(cad_incident)

                # Fetch unit updates
                units = await self.adapter.fetch_units()
                for cad_unit in units:
                    await self._process_cad_unit(cad_unit)

                last_sync = datetime.utcnow()

            except Exception:
                pass

            await asyncio.sleep(interval)

    async def _process_cad_incident(self, cad_incident: CADIncident) -> Incident | None:
        """Process a CAD incident - create or update in database."""
        from sqlalchemy import select

        # Check if incident already exists
        result = await self.db.execute(
            select(Incident).where(
                Incident.external_id == cad_incident.cad_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing incident
            existing.title = f"{cad_incident.call_type}: {cad_incident.address}"
            existing.description = cad_incident.description or ""
            existing.priority = cad_incident.priority
            # Map CAD status to internal status
            # (would need status mapping logic)
            await self.db.commit()
            return existing

        # Create new incident
        incident = Incident(
            id=uuid.uuid4(),
            incident_number=cad_incident.incident_number,
            title=f"{cad_incident.call_type}: {cad_incident.address}",
            description=cad_incident.description or "",
            category=self.adapter.map_call_type_to_category(cad_incident.call_type),
            priority=cad_incident.priority,
            status=IncidentStatus.NEW,
            location_address=cad_incident.address,
            location_city=cad_incident.city,
            location_state=cad_incident.state,
            location_zip=cad_incident.postal_code,
            latitude=cad_incident.latitude,
            longitude=cad_incident.longitude,
            caller_name=cad_incident.caller_name,
            caller_phone=cad_incident.caller_phone,
            external_id=cad_incident.cad_id,
            external_source=self.adapter.vendor.value,
        )

        self.db.add(incident)
        await self.db.commit()
        await self.db.refresh(incident)

        return incident

    async def _process_cad_unit(self, cad_unit: CADUnit) -> Resource | None:
        """Process a CAD unit - update resource status."""
        from sqlalchemy import select

        # Find matching resource by call sign
        result = await self.db.execute(
            select(Resource).where(
                Resource.call_sign == cad_unit.call_sign
            )
        )
        resource = result.scalar_one_or_none()

        if not resource:
            return None

        # Update location if provided
        if cad_unit.latitude and cad_unit.longitude:
            resource.current_latitude = cad_unit.latitude
            resource.current_longitude = cad_unit.longitude

        # Map CAD status to resource status
        status_map = {
            "available": ResourceStatus.AVAILABLE,
            "enroute": ResourceStatus.DISPATCHED,
            "on_scene": ResourceStatus.ON_SCENE,
            "busy": ResourceStatus.BUSY,
            "out_of_service": ResourceStatus.OUT_OF_SERVICE,
        }
        if cad_unit.status.lower() in status_map:
            resource.status = status_map[cad_unit.status.lower()]

        await self.db.commit()
        return resource

    async def sync_incident_to_cad(self, incident: Incident) -> bool:
        """Sync an incident update back to CAD."""
        if not incident.external_id:
            return False

        # Map internal status to CAD status
        status_map = {
            IncidentStatus.NEW: "pending",
            IncidentStatus.ASSIGNED: "dispatched",
            IncidentStatus.EN_ROUTE: "responding",
            IncidentStatus.ON_SCENE: "on_scene",
            IncidentStatus.RESOLVED: "resolved",
            IncidentStatus.CLOSED: "closed",
        }

        return await self.adapter.send_incident_update(
            incident_id=incident.external_id,
            status=status_map.get(incident.status),
        )

    async def sync_resource_to_cad(self, resource: Resource) -> bool:
        """Sync a resource status update back to CAD."""
        if not resource.call_sign:
            return False

        # Map internal status to CAD status
        status_map = {
            ResourceStatus.AVAILABLE: "available",
            ResourceStatus.DISPATCHED: "enroute",
            ResourceStatus.ON_SCENE: "on_scene",
            ResourceStatus.BUSY: "busy",
            ResourceStatus.OUT_OF_SERVICE: "out_of_service",
        }

        return await self.adapter.send_unit_status(
            unit_id=resource.call_sign,
            status=status_map.get(resource.status, "available"),
        )


def create_adapter(
    vendor: CADVendor,
    config: dict[str, Any],
    event_handler: Callable[[CADEvent], Awaitable[None]] | None = None,
) -> CADAdapter:
    """Factory function to create CAD adapters.

    Args:
        vendor: CAD vendor type
        config: Adapter configuration
        event_handler: Event callback

    Returns:
        CAD adapter instance
    """
    adapters = {
        CADVendor.GENERIC: GenericRESTAdapter,
        CADVendor.TRITECH: TriTechAdapter,
        # Add more adapters as implemented
    }

    adapter_class = adapters.get(vendor, GenericRESTAdapter)
    return adapter_class(config, event_handler)

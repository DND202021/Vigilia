"""CAD System Integration Base Classes.

Provides abstract interfaces for CAD system integration,
supporting bidirectional sync of incidents and units.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, AsyncIterator, Any
import uuid

from app.integrations.base import IntegrationAdapter, IntegrationError, CircuitBreakerConfig


class CADAdapterError(IntegrationError):
    """CAD adapter specific errors."""
    pass


class CADIncidentStatus(str, Enum):
    """Standard CAD incident statuses."""
    PENDING = "pending"
    DISPATCHED = "dispatched"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    TRANSPORTING = "transporting"
    AT_HOSPITAL = "at_hospital"
    CLEARED = "cleared"
    CANCELLED = "cancelled"


class CADUnitStatus(str, Enum):
    """Standard CAD unit statuses."""
    AVAILABLE = "available"
    BUSY = "busy"
    DISPATCHED = "dispatched"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    TRANSPORTING = "transporting"
    AT_HOSPITAL = "at_hospital"
    OUT_OF_SERVICE = "out_of_service"


@dataclass
class CADIncident:
    """Incident data from CAD system."""
    cad_incident_id: str
    incident_type: str
    priority: int  # 1-5, 1 being highest
    status: CADIncidentStatus
    location_address: str
    location_coordinates: tuple[float, float] | None = None
    caller_name: str | None = None
    caller_phone: str | None = None
    narrative: str | None = None
    assigned_units: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    dispatched_at: datetime | None = None
    cleared_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CADUnit:
    """Unit/resource data from CAD system."""
    cad_unit_id: str
    unit_name: str
    unit_type: str  # police, fire, ems, etc.
    status: CADUnitStatus
    current_incident_id: str | None = None
    location: tuple[float, float] | None = None
    personnel: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    agency_id: str | None = None
    last_update: datetime | None = None


@dataclass
class CADMapping:
    """Mapping between ERIOP and CAD entity IDs."""
    entity_type: str  # "incident" or "unit"
    eriop_id: uuid.UUID
    cad_id: str
    cad_system: str
    created_at: datetime = field(default_factory=lambda: datetime.now())
    updated_at: datetime = field(default_factory=lambda: datetime.now())


class CADAdapter(IntegrationAdapter, ABC):
    """
    Abstract base class for CAD system adapters.

    Each CAD system (Hexagon, Tyler, Motorola, etc.) must
    implement this interface for integration with ERIOP.
    """

    def __init__(
        self,
        name: str,
        cad_system_name: str,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ):
        super().__init__(name, circuit_breaker_config)
        self.cad_system_name = cad_system_name

    # ============ Incident Operations ============

    @abstractmethod
    async def get_incident(
        self,
        cad_incident_id: str,
    ) -> CADIncident | None:
        """
        Retrieve single incident from CAD.

        Args:
            cad_incident_id: CAD system's incident ID

        Returns:
            CADIncident or None if not found
        """
        pass

    @abstractmethod
    async def get_active_incidents(self) -> list[CADIncident]:
        """
        Retrieve all active incidents from CAD.

        Returns:
            List of active CADIncident objects
        """
        pass

    @abstractmethod
    async def create_incident(
        self,
        incident: CADIncident,
    ) -> str:
        """
        Create new incident in CAD system.

        Args:
            incident: Incident data to create

        Returns:
            CAD system's incident ID
        """
        pass

    @abstractmethod
    async def update_incident(
        self,
        cad_incident_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """
        Update existing incident in CAD.

        Args:
            cad_incident_id: CAD incident ID
            updates: Dictionary of fields to update

        Returns:
            True if update successful
        """
        pass

    @abstractmethod
    async def add_incident_narrative(
        self,
        cad_incident_id: str,
        text: str,
        timestamp: datetime | None = None,
    ) -> bool:
        """
        Add narrative/notes to incident.

        Args:
            cad_incident_id: CAD incident ID
            text: Narrative text to add
            timestamp: Optional timestamp for the narrative

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def close_incident(
        self,
        cad_incident_id: str,
        disposition: str | None = None,
    ) -> bool:
        """
        Close/clear an incident.

        Args:
            cad_incident_id: CAD incident ID
            disposition: Optional disposition code

        Returns:
            True if successful
        """
        pass

    # ============ Unit Operations ============

    @abstractmethod
    async def get_unit(
        self,
        cad_unit_id: str,
    ) -> CADUnit | None:
        """
        Retrieve single unit from CAD.

        Args:
            cad_unit_id: CAD unit ID

        Returns:
            CADUnit or None if not found
        """
        pass

    @abstractmethod
    async def get_available_units(
        self,
        unit_type: str | None = None,
    ) -> list[CADUnit]:
        """
        Retrieve available units, optionally filtered by type.

        Args:
            unit_type: Optional filter (police, fire, ems)

        Returns:
            List of available CADUnit objects
        """
        pass

    @abstractmethod
    async def dispatch_unit(
        self,
        cad_unit_id: str,
        cad_incident_id: str,
    ) -> bool:
        """
        Dispatch unit to incident.

        Args:
            cad_unit_id: Unit to dispatch
            cad_incident_id: Incident to dispatch to

        Returns:
            True if dispatch successful
        """
        pass

    @abstractmethod
    async def update_unit_status(
        self,
        cad_unit_id: str,
        status: CADUnitStatus,
    ) -> bool:
        """
        Update unit status.

        Args:
            cad_unit_id: Unit ID
            status: New status

        Returns:
            True if update successful
        """
        pass

    # ============ Real-time Updates ============

    @abstractmethod
    async def subscribe_incidents(self) -> AsyncIterator[CADIncident]:
        """
        Subscribe to real-time incident updates.

        Yields:
            CADIncident objects as updates occur
        """
        pass

    @abstractmethod
    async def subscribe_units(self) -> AsyncIterator[CADUnit]:
        """
        Subscribe to real-time unit updates.

        Yields:
            CADUnit objects as updates occur
        """
        pass

    # ============ Status Mapping ============

    def map_status_to_cad(self, eriop_status: str) -> CADIncidentStatus:
        """Map ERIOP incident status to CAD status."""
        status_map = {
            "new": CADIncidentStatus.PENDING,
            "assigned": CADIncidentStatus.DISPATCHED,
            "en_route": CADIncidentStatus.EN_ROUTE,
            "on_scene": CADIncidentStatus.ON_SCENE,
            "resolved": CADIncidentStatus.CLEARED,
            "closed": CADIncidentStatus.CLEARED,
        }
        return status_map.get(eriop_status.lower(), CADIncidentStatus.PENDING)

    def map_status_from_cad(self, cad_status: CADIncidentStatus) -> str:
        """Map CAD incident status to ERIOP status."""
        status_map = {
            CADIncidentStatus.PENDING: "new",
            CADIncidentStatus.DISPATCHED: "assigned",
            CADIncidentStatus.EN_ROUTE: "en_route",
            CADIncidentStatus.ON_SCENE: "on_scene",
            CADIncidentStatus.TRANSPORTING: "on_scene",
            CADIncidentStatus.AT_HOSPITAL: "on_scene",
            CADIncidentStatus.CLEARED: "resolved",
            CADIncidentStatus.CANCELLED: "closed",
        }
        return status_map.get(cad_status, "new")

    def map_priority_to_cad(self, eriop_priority: int) -> int:
        """Map ERIOP priority (1-5) to CAD priority."""
        # Both use 1-5 scale with 1 being highest
        return max(1, min(5, eriop_priority))

    def map_priority_from_cad(self, cad_priority: int) -> int:
        """Map CAD priority to ERIOP priority."""
        return max(1, min(5, cad_priority))

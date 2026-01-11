"""Mock CAD adapter for testing and development."""

from datetime import datetime, timezone
from typing import AsyncIterator, Any
import asyncio
import uuid

from app.integrations.cad.base import (
    CADAdapter,
    CADIncident,
    CADUnit,
    CADIncidentStatus,
    CADUnitStatus,
    CADAdapterError,
)
from app.integrations.base import CircuitBreakerConfig


class MockCADAdapter(CADAdapter):
    """
    Mock CAD adapter for testing.

    Simulates a CAD system with in-memory storage.
    """

    def __init__(
        self,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
        simulate_latency: float = 0.1,
    ):
        super().__init__(
            name="mock_cad",
            cad_system_name="MockCAD",
            circuit_breaker_config=circuit_breaker_config,
        )
        self.simulate_latency = simulate_latency

        # In-memory storage
        self._incidents: dict[str, CADIncident] = {}
        self._units: dict[str, CADUnit] = {}

        # Event queues for subscriptions
        self._incident_queue: asyncio.Queue[CADIncident] = asyncio.Queue()
        self._unit_queue: asyncio.Queue[CADUnit] = asyncio.Queue()

        # Initialize mock data
        self._init_mock_data()

    def _init_mock_data(self):
        """Initialize mock units."""
        mock_units = [
            CADUnit(
                cad_unit_id="E1",
                unit_name="Engine 1",
                unit_type="fire",
                status=CADUnitStatus.AVAILABLE,
                location=(45.5017, -73.5673),
                capabilities=["fire", "rescue", "ems_basic"],
            ),
            CADUnit(
                cad_unit_id="E2",
                unit_name="Engine 2",
                unit_type="fire",
                status=CADUnitStatus.AVAILABLE,
                location=(45.5055, -73.5530),
                capabilities=["fire", "rescue"],
            ),
            CADUnit(
                cad_unit_id="L1",
                unit_name="Ladder 1",
                unit_type="fire",
                status=CADUnitStatus.AVAILABLE,
                location=(45.5017, -73.5673),
                capabilities=["fire", "rescue", "ladder"],
            ),
            CADUnit(
                cad_unit_id="M1",
                unit_name="Medic 1",
                unit_type="ems",
                status=CADUnitStatus.AVAILABLE,
                location=(45.4920, -73.5800),
                capabilities=["ems_als"],
            ),
            CADUnit(
                cad_unit_id="P1",
                unit_name="Patrol 1",
                unit_type="police",
                status=CADUnitStatus.AVAILABLE,
                location=(45.5100, -73.5700),
                capabilities=["patrol"],
            ),
        ]

        for unit in mock_units:
            self._units[unit.cad_unit_id] = unit

    async def connect(self) -> bool:
        """Connect to mock CAD."""
        await asyncio.sleep(self.simulate_latency)
        self._connected = True
        return True

    async def disconnect(self) -> None:
        """Disconnect from mock CAD."""
        self._connected = False

    async def health_check(self) -> dict[str, Any]:
        """Check mock CAD health."""
        return {
            "healthy": True,
            "incidents_count": len(self._incidents),
            "units_count": len(self._units),
        }

    # ============ Incident Operations ============

    async def get_incident(self, cad_incident_id: str) -> CADIncident | None:
        """Get incident by ID."""
        await asyncio.sleep(self.simulate_latency)
        return self._incidents.get(cad_incident_id)

    async def get_active_incidents(self) -> list[CADIncident]:
        """Get all active incidents."""
        await asyncio.sleep(self.simulate_latency)
        return [
            inc for inc in self._incidents.values()
            if inc.status not in [CADIncidentStatus.CLEARED, CADIncidentStatus.CANCELLED]
        ]

    async def create_incident(self, incident: CADIncident) -> str:
        """Create new incident."""
        await asyncio.sleep(self.simulate_latency)

        # Generate ID if not provided
        if not incident.cad_incident_id:
            incident.cad_incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"

        incident.created_at = datetime.now(timezone.utc)
        incident.updated_at = datetime.now(timezone.utc)

        self._incidents[incident.cad_incident_id] = incident

        # Notify subscribers
        await self._incident_queue.put(incident)

        return incident.cad_incident_id

    async def update_incident(
        self,
        cad_incident_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Update incident."""
        await asyncio.sleep(self.simulate_latency)

        incident = self._incidents.get(cad_incident_id)
        if not incident:
            return False

        for key, value in updates.items():
            if hasattr(incident, key):
                setattr(incident, key, value)

        incident.updated_at = datetime.now(timezone.utc)

        # Notify subscribers
        await self._incident_queue.put(incident)

        return True

    async def add_incident_narrative(
        self,
        cad_incident_id: str,
        text: str,
        timestamp: datetime | None = None,
    ) -> bool:
        """Add narrative to incident."""
        await asyncio.sleep(self.simulate_latency)

        incident = self._incidents.get(cad_incident_id)
        if not incident:
            return False

        ts = timestamp or datetime.now(timezone.utc)
        narrative_entry = f"[{ts.strftime('%H:%M:%S')}] {text}"

        if incident.narrative:
            incident.narrative += f"\n{narrative_entry}"
        else:
            incident.narrative = narrative_entry

        incident.updated_at = datetime.now(timezone.utc)

        return True

    async def close_incident(
        self,
        cad_incident_id: str,
        disposition: str | None = None,
    ) -> bool:
        """Close incident."""
        await asyncio.sleep(self.simulate_latency)

        incident = self._incidents.get(cad_incident_id)
        if not incident:
            return False

        incident.status = CADIncidentStatus.CLEARED
        incident.cleared_at = datetime.now(timezone.utc)
        incident.updated_at = datetime.now(timezone.utc)

        if disposition:
            incident.metadata["disposition"] = disposition

        # Release assigned units
        for unit_id in incident.assigned_units:
            unit = self._units.get(unit_id)
            if unit:
                unit.status = CADUnitStatus.AVAILABLE
                unit.current_incident_id = None
                await self._unit_queue.put(unit)

        incident.assigned_units = []

        # Notify subscribers
        await self._incident_queue.put(incident)

        return True

    # ============ Unit Operations ============

    async def get_unit(self, cad_unit_id: str) -> CADUnit | None:
        """Get unit by ID."""
        await asyncio.sleep(self.simulate_latency)
        return self._units.get(cad_unit_id)

    async def get_available_units(
        self,
        unit_type: str | None = None,
    ) -> list[CADUnit]:
        """Get available units."""
        await asyncio.sleep(self.simulate_latency)

        units = [
            u for u in self._units.values()
            if u.status == CADUnitStatus.AVAILABLE
        ]

        if unit_type:
            units = [u for u in units if u.unit_type == unit_type]

        return units

    async def dispatch_unit(
        self,
        cad_unit_id: str,
        cad_incident_id: str,
    ) -> bool:
        """Dispatch unit to incident."""
        await asyncio.sleep(self.simulate_latency)

        unit = self._units.get(cad_unit_id)
        incident = self._incidents.get(cad_incident_id)

        if not unit or not incident:
            return False

        if unit.status != CADUnitStatus.AVAILABLE:
            raise CADAdapterError(
                f"Unit {cad_unit_id} is not available",
                source=self.name,
            )

        # Update unit
        unit.status = CADUnitStatus.DISPATCHED
        unit.current_incident_id = cad_incident_id
        unit.last_update = datetime.now(timezone.utc)

        # Update incident
        if cad_unit_id not in incident.assigned_units:
            incident.assigned_units.append(cad_unit_id)

        if incident.status == CADIncidentStatus.PENDING:
            incident.status = CADIncidentStatus.DISPATCHED
            incident.dispatched_at = datetime.now(timezone.utc)

        incident.updated_at = datetime.now(timezone.utc)

        # Notify subscribers
        await self._unit_queue.put(unit)
        await self._incident_queue.put(incident)

        return True

    async def update_unit_status(
        self,
        cad_unit_id: str,
        status: CADUnitStatus,
    ) -> bool:
        """Update unit status."""
        await asyncio.sleep(self.simulate_latency)

        unit = self._units.get(cad_unit_id)
        if not unit:
            return False

        old_status = unit.status
        unit.status = status
        unit.last_update = datetime.now(timezone.utc)

        # If becoming available, clear incident assignment
        if status == CADUnitStatus.AVAILABLE:
            unit.current_incident_id = None

        # Notify subscribers
        await self._unit_queue.put(unit)

        return True

    # ============ Real-time Updates ============

    async def subscribe_incidents(self) -> AsyncIterator[CADIncident]:
        """Subscribe to incident updates."""
        while self._connected:
            try:
                incident = await asyncio.wait_for(
                    self._incident_queue.get(),
                    timeout=1.0,
                )
                yield incident
            except asyncio.TimeoutError:
                continue

    async def subscribe_units(self) -> AsyncIterator[CADUnit]:
        """Subscribe to unit updates."""
        while self._connected:
            try:
                unit = await asyncio.wait_for(
                    self._unit_queue.get(),
                    timeout=1.0,
                )
                yield unit
            except asyncio.TimeoutError:
                continue

    # ============ Test Helpers ============

    def add_mock_incident(self, incident: CADIncident):
        """Add incident directly for testing."""
        self._incidents[incident.cad_incident_id] = incident

    def add_mock_unit(self, unit: CADUnit):
        """Add unit directly for testing."""
        self._units[unit.cad_unit_id] = unit

    def clear_all(self):
        """Clear all mock data."""
        self._incidents.clear()
        self._units.clear()
        self._init_mock_data()

"""Incident Service for emergency event management."""

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.incident import Incident, IncidentStatus, IncidentPriority, IncidentCategory
from app.models.agency import Agency
from app.models.user import User


class IncidentError(Exception):
    """Incident related errors."""
    pass


class IncidentService:
    """Service for incident management operations."""

    def __init__(self, db: AsyncSession):
        """Initialize incident service with database session."""
        self.db = db

    async def create_incident(
        self,
        agency_id: uuid.UUID,
        category: IncidentCategory,
        title: str,
        latitude: float,
        longitude: float,
        priority: IncidentPriority = IncidentPriority.MEDIUM,
        description: str | None = None,
        address: str | None = None,
        building_info: str | None = None,
        source_alert_id: uuid.UUID | None = None,
        reported_by: User | None = None,
    ) -> Incident:
        """Create a new incident."""
        # Verify agency exists
        agency = await self._get_agency(agency_id)
        if agency is None:
            raise IncidentError(f"Agency {agency_id} not found")

        # Generate incident number
        incident_number = await self._generate_incident_number(agency)

        incident = Incident(
            id=uuid.uuid4(),
            incident_number=incident_number,
            agency_id=agency_id,
            category=category,
            priority=priority,
            status=IncidentStatus.NEW,
            title=title,
            description=description,
            latitude=latitude,
            longitude=longitude,
            address=address,
            building_info=building_info,
            reported_at=datetime.now(timezone.utc),
            source_alert_id=source_alert_id,
            assigned_units=[],
            timeline_events=[],
        )

        # Add initial timeline event
        incident.timeline_events = [
            self._create_timeline_event(
                event_type="created",
                description=f"Incident created: {title}",
                user=reported_by,
            )
        ]

        self.db.add(incident)
        await self.db.commit()
        await self.db.refresh(incident)

        return incident

    async def get_incident(self, incident_id: uuid.UUID) -> Incident | None:
        """Get incident by ID."""
        result = await self.db.execute(
            select(Incident).where(Incident.id == incident_id)
        )
        return result.scalar_one_or_none()

    async def get_incident_by_number(self, incident_number: str) -> Incident | None:
        """Get incident by incident number."""
        result = await self.db.execute(
            select(Incident).where(Incident.incident_number == incident_number)
        )
        return result.scalar_one_or_none()

    async def list_incidents(
        self,
        agency_id: uuid.UUID | None = None,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Incident]:
        """List incidents with optional filters."""
        query = select(Incident)

        conditions = []
        if agency_id:
            conditions.append(Incident.agency_id == agency_id)
        if status:
            conditions.append(Incident.status == status)
        if priority:
            conditions.append(Incident.priority == priority)
        if category:
            conditions.append(Incident.category == category)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Incident.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_incident(
        self,
        incident_id: uuid.UUID,
        updated_by: User,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        title: str | None = None,
        description: str | None = None,
    ) -> Incident:
        """Update an incident."""
        incident = await self.get_incident(incident_id)
        if incident is None:
            raise IncidentError(f"Incident {incident_id} not found")

        changes = []

        if status and status != incident.status:
            old_status = incident.status
            incident.status = status
            changes.append(f"Status changed from {old_status.value} to {status.value}")

            # Update status timestamps
            now = datetime.now(timezone.utc)
            if status == IncidentStatus.ASSIGNED:
                incident.dispatched_at = now
            elif status == IncidentStatus.ON_SCENE:
                incident.arrived_at = now
            elif status == IncidentStatus.RESOLVED:
                incident.resolved_at = now
            elif status == IncidentStatus.CLOSED:
                incident.closed_at = now

        if priority and priority != incident.priority:
            old_priority = incident.priority
            incident.priority = priority
            changes.append(f"Priority changed from {old_priority.value} to {priority.value}")

        if title and title != incident.title:
            incident.title = title
            changes.append(f"Title updated")

        if description is not None and description != incident.description:
            incident.description = description
            changes.append("Description updated")

        if changes:
            # Add timeline event for changes
            timeline_events = list(incident.timeline_events or [])
            timeline_events.append(
                self._create_timeline_event(
                    event_type="updated",
                    description="; ".join(changes),
                    user=updated_by,
                )
            )
            incident.timeline_events = timeline_events
            flag_modified(incident, "timeline_events")

        await self.db.commit()
        await self.db.refresh(incident)

        return incident

    async def assign_unit(
        self,
        incident_id: uuid.UUID,
        unit_id: uuid.UUID,
        assigned_by: User,
    ) -> Incident:
        """Assign a unit to an incident."""
        incident = await self.get_incident(incident_id)
        if incident is None:
            raise IncidentError(f"Incident {incident_id} not found")

        assigned_units = list(incident.assigned_units or [])
        unit_id_str = str(unit_id)

        if unit_id_str in assigned_units:
            raise IncidentError(f"Unit {unit_id} is already assigned to this incident")

        assigned_units.append(unit_id_str)
        incident.assigned_units = assigned_units
        flag_modified(incident, "assigned_units")

        # Update status to ASSIGNED if still NEW
        if incident.status == IncidentStatus.NEW:
            incident.status = IncidentStatus.ASSIGNED
            incident.dispatched_at = datetime.now(timezone.utc)

        # Add timeline event
        timeline_events = list(incident.timeline_events or [])
        timeline_events.append(
            self._create_timeline_event(
                event_type="unit_assigned",
                description=f"Unit {unit_id} assigned",
                user=assigned_by,
                metadata={"unit_id": unit_id_str},
            )
        )
        incident.timeline_events = timeline_events
        flag_modified(incident, "timeline_events")

        await self.db.commit()
        await self.db.refresh(incident)

        return incident

    async def unassign_unit(
        self,
        incident_id: uuid.UUID,
        unit_id: uuid.UUID,
        unassigned_by: User,
        reason: str | None = None,
    ) -> Incident:
        """Remove a unit from an incident."""
        incident = await self.get_incident(incident_id)
        if incident is None:
            raise IncidentError(f"Incident {incident_id} not found")

        assigned_units = list(incident.assigned_units or [])
        unit_id_str = str(unit_id)

        if unit_id_str not in assigned_units:
            raise IncidentError(f"Unit {unit_id} is not assigned to this incident")

        assigned_units.remove(unit_id_str)
        incident.assigned_units = assigned_units
        flag_modified(incident, "assigned_units")

        # Add timeline event
        timeline_events = list(incident.timeline_events or [])
        timeline_events.append(
            self._create_timeline_event(
                event_type="unit_unassigned",
                description=f"Unit {unit_id} unassigned" + (f": {reason}" if reason else ""),
                user=unassigned_by,
                metadata={"unit_id": unit_id_str, "reason": reason},
            )
        )
        incident.timeline_events = timeline_events
        flag_modified(incident, "timeline_events")

        await self.db.commit()
        await self.db.refresh(incident)

        return incident

    async def escalate_incident(
        self,
        incident_id: uuid.UUID,
        escalated_by: User,
        reason: str,
        new_priority: IncidentPriority | None = None,
    ) -> Incident:
        """Escalate an incident."""
        incident = await self.get_incident(incident_id)
        if incident is None:
            raise IncidentError(f"Incident {incident_id} not found")

        # Increase priority if not specified
        if new_priority is None:
            current_value = incident.priority.value
            if current_value > 1:
                new_priority = IncidentPriority(current_value - 1)
            else:
                new_priority = incident.priority

        old_priority = incident.priority
        incident.priority = new_priority

        # Add timeline event
        timeline_events = list(incident.timeline_events or [])
        timeline_events.append(
            self._create_timeline_event(
                event_type="escalated",
                description=f"Incident escalated from {old_priority.name} to {new_priority.name}: {reason}",
                user=escalated_by,
                metadata={"reason": reason, "old_priority": old_priority.value, "new_priority": new_priority.value},
            )
        )
        incident.timeline_events = timeline_events
        flag_modified(incident, "timeline_events")

        await self.db.commit()
        await self.db.refresh(incident)

        return incident

    async def close_incident(
        self,
        incident_id: uuid.UUID,
        closed_by: User,
        resolution_notes: str | None = None,
    ) -> Incident:
        """Close an incident."""
        incident = await self.get_incident(incident_id)
        if incident is None:
            raise IncidentError(f"Incident {incident_id} not found")

        if incident.status == IncidentStatus.CLOSED:
            raise IncidentError("Incident is already closed")

        incident.status = IncidentStatus.CLOSED
        incident.closed_at = datetime.now(timezone.utc)

        # Add timeline event
        timeline_events = list(incident.timeline_events or [])
        timeline_events.append(
            self._create_timeline_event(
                event_type="closed",
                description=f"Incident closed" + (f": {resolution_notes}" if resolution_notes else ""),
                user=closed_by,
                metadata={"resolution_notes": resolution_notes},
            )
        )
        incident.timeline_events = timeline_events
        flag_modified(incident, "timeline_events")

        await self.db.commit()
        await self.db.refresh(incident)

        return incident

    async def get_timeline(self, incident_id: uuid.UUID) -> list[dict[str, Any]]:
        """Get incident timeline."""
        incident = await self.get_incident(incident_id)
        if incident is None:
            raise IncidentError(f"Incident {incident_id} not found")

        return incident.timeline_events or []

    async def get_active_incidents_count(self, agency_id: uuid.UUID | None = None) -> int:
        """Get count of active (non-closed) incidents."""
        query = select(Incident).where(
            Incident.status != IncidentStatus.CLOSED
        )
        if agency_id:
            query = query.where(Incident.agency_id == agency_id)

        result = await self.db.execute(query)
        return len(list(result.scalars().all()))

    async def _get_agency(self, agency_id: uuid.UUID) -> Agency | None:
        """Get agency by ID."""
        result = await self.db.execute(
            select(Agency).where(Agency.id == agency_id)
        )
        return result.scalar_one_or_none()

    async def _generate_incident_number(self, agency: Agency) -> str:
        """Generate unique incident number for agency."""
        now = datetime.now(timezone.utc)
        date_prefix = now.strftime("%Y%m%d")

        # Count today's incidents for this agency
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(Incident).where(
                and_(
                    Incident.agency_id == agency.id,
                    Incident.created_at >= start_of_day,
                )
            )
        )
        count = len(list(result.scalars().all()))

        return f"{agency.code}-{date_prefix}-{count + 1:04d}"

    @staticmethod
    def _create_timeline_event(
        event_type: str,
        description: str,
        user: User | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a timeline event entry."""
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if user:
            event["user_id"] = str(user.id)
            event["user_name"] = user.full_name
        if metadata:
            event["metadata"] = metadata
        return event

"""Incident State Machine with validated transitions.

This module implements a state machine for incident lifecycle management
with validated transitions and side effects.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Awaitable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentStatus
from app.models.user import User
from app.services.audit_service import AuditService
from app.models.audit import AuditAction

logger = structlog.get_logger()


class TransitionError(Exception):
    """Raised when a state transition is invalid."""

    pass


# Valid state transitions: from_state -> [to_states]
VALID_TRANSITIONS: dict[IncidentStatus, list[IncidentStatus]] = {
    IncidentStatus.NEW: [
        IncidentStatus.ASSIGNED,
        IncidentStatus.CLOSED,  # False alarm / cancelled
    ],
    IncidentStatus.ASSIGNED: [
        IncidentStatus.EN_ROUTE,
        IncidentStatus.NEW,  # Reassignment
        IncidentStatus.CLOSED,  # Cancelled
    ],
    IncidentStatus.EN_ROUTE: [
        IncidentStatus.ON_SCENE,
        IncidentStatus.ASSIGNED,  # Unit cancelled, need reassignment
        IncidentStatus.CLOSED,  # Cancelled en route
    ],
    IncidentStatus.ON_SCENE: [
        IncidentStatus.RESOLVED,
        IncidentStatus.EN_ROUTE,  # Need additional units
    ],
    IncidentStatus.RESOLVED: [
        IncidentStatus.CLOSED,
        IncidentStatus.ON_SCENE,  # Reopened
    ],
    IncidentStatus.CLOSED: [],  # Terminal state
}


# Transition requirements: some transitions require specific conditions
@dataclass
class TransitionRequirement:
    """Requirements for a state transition."""

    required_fields: list[str] = None
    min_assigned_units: int = 0
    validator: Callable[[Incident], bool] | None = None
    error_message: str = "Transition requirements not met"


TRANSITION_REQUIREMENTS: dict[tuple[IncidentStatus, IncidentStatus], TransitionRequirement] = {
    (IncidentStatus.NEW, IncidentStatus.ASSIGNED): TransitionRequirement(
        min_assigned_units=1,
        error_message="At least one unit must be assigned",
    ),
    (IncidentStatus.ON_SCENE, IncidentStatus.RESOLVED): TransitionRequirement(
        required_fields=["resolution_notes"],
        error_message="Resolution notes are required to resolve incident",
    ),
}


class IncidentStateMachine:
    """State machine for incident lifecycle management."""

    def __init__(self, db: AsyncSession):
        """Initialize state machine with database session."""
        self.db = db
        self._audit_service = AuditService(db)

    def can_transition(
        self,
        incident: Incident,
        target_status: IncidentStatus,
    ) -> tuple[bool, str]:
        """Check if a transition is valid.

        Args:
            incident: The incident to check
            target_status: The desired target status

        Returns:
            Tuple of (is_valid, error_message)
        """
        current_status = incident.status

        # Check if transition is in valid transitions map
        valid_targets = VALID_TRANSITIONS.get(current_status, [])
        if target_status not in valid_targets:
            return False, f"Cannot transition from {current_status.value} to {target_status.value}"

        # Check transition requirements
        requirement = TRANSITION_REQUIREMENTS.get((current_status, target_status))
        if requirement:
            # Check required fields
            if requirement.required_fields:
                for field in requirement.required_fields:
                    if not getattr(incident, field, None):
                        return False, requirement.error_message

            # Check minimum assigned units
            if requirement.min_assigned_units > 0:
                assigned = len(incident.assigned_units or [])
                if assigned < requirement.min_assigned_units:
                    return False, requirement.error_message

            # Run custom validator
            if requirement.validator and not requirement.validator(incident):
                return False, requirement.error_message

        return True, ""

    async def transition(
        self,
        incident: Incident,
        target_status: IncidentStatus,
        user: User | None = None,
        notes: str | None = None,
    ) -> Incident:
        """Perform a state transition with validation and side effects.

        Args:
            incident: The incident to transition
            target_status: The desired target status
            user: The user performing the transition
            notes: Optional notes for the transition

        Returns:
            The updated incident

        Raises:
            TransitionError: If the transition is invalid
        """
        current_status = incident.status

        # Validate transition
        is_valid, error = self.can_transition(incident, target_status)
        if not is_valid:
            raise TransitionError(error)

        # Store old values for audit
        old_values = {"status": current_status.value}

        # Perform transition
        incident.status = target_status

        # Apply side effects
        await self._apply_side_effects(incident, current_status, target_status, notes)

        # Record timeline event
        self._add_timeline_event(
            incident,
            event_type="status_change",
            user=user,
            details=f"Status changed from {current_status.value} to {target_status.value}",
            notes=notes,
        )

        # Commit changes
        await self.db.commit()
        await self.db.refresh(incident)

        # Log audit trail
        await self._audit_service.log_entity_change(
            action=AuditAction.INCIDENT_UPDATED,
            entity_type="incident",
            entity_id=str(incident.id),
            user=user,
            old_values=old_values,
            new_values={"status": target_status.value},
            description=f"Incident status changed to {target_status.value}",
        )

        logger.info(
            "Incident status transitioned",
            incident_id=str(incident.id),
            from_status=current_status.value,
            to_status=target_status.value,
            user_id=str(user.id) if user else None,
        )

        return incident

    async def _apply_side_effects(
        self,
        incident: Incident,
        from_status: IncidentStatus,
        to_status: IncidentStatus,
        notes: str | None,
    ) -> None:
        """Apply side effects for a status transition."""
        now = datetime.now(timezone.utc)

        # Update timestamp fields based on transition
        if to_status == IncidentStatus.ASSIGNED and not incident.dispatched_at:
            incident.dispatched_at = now

        elif to_status == IncidentStatus.ON_SCENE and not incident.arrived_at:
            incident.arrived_at = now

        elif to_status == IncidentStatus.RESOLVED:
            incident.resolved_at = now
            if notes:
                # Store resolution notes in timeline
                pass  # Notes added via timeline event

        elif to_status == IncidentStatus.CLOSED:
            incident.closed_at = now

    def _add_timeline_event(
        self,
        incident: Incident,
        event_type: str,
        user: User | None,
        details: str,
        notes: str | None = None,
    ) -> None:
        """Add an event to the incident timeline."""
        if incident.timeline_events is None:
            incident.timeline_events = []

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "details": details,
        }

        if user:
            event["user_id"] = str(user.id)
            event["user_name"] = user.full_name

        if notes:
            event["notes"] = notes

        # Create new list to trigger SQLAlchemy change detection
        incident.timeline_events = incident.timeline_events + [event]

    def get_available_transitions(self, incident: Incident) -> list[IncidentStatus]:
        """Get list of valid transitions from current state."""
        return VALID_TRANSITIONS.get(incident.status, [])

    def get_transition_requirements(
        self,
        from_status: IncidentStatus,
        to_status: IncidentStatus,
    ) -> TransitionRequirement | None:
        """Get requirements for a specific transition."""
        return TRANSITION_REQUIREMENTS.get((from_status, to_status))

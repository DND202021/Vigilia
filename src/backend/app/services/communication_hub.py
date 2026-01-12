"""Communication Hub Service.

This service manages message templates and communication
for incidents, alerts, and notifications.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentCategory, IncidentPriority, IncidentStatus
from app.models.alert import Alert
from app.models.user import User

logger = structlog.get_logger()


class MessageChannel(str, Enum):
    """Available communication channels."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    RADIO = "radio"
    IN_APP = "in_app"


class MessagePriority(str, Enum):
    """Message priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class MessageTemplate:
    """Message template definition."""

    id: str
    name: str
    subject: str
    body: str
    channels: list[MessageChannel]
    variables: list[str]


@dataclass
class RenderedMessage:
    """A message with template variables filled in."""

    subject: str
    body: str
    channel: MessageChannel
    priority: MessagePriority
    metadata: dict[str, Any]


# Predefined message templates
TEMPLATES: dict[str, MessageTemplate] = {
    "incident_created": MessageTemplate(
        id="incident_created",
        name="New Incident Created",
        subject="New {category} Incident - {incident_number}",
        body="""A new incident has been created:

Incident: {incident_number}
Category: {category}
Priority: {priority}
Title: {title}

Location: {address}
Coordinates: {latitude}, {longitude}

Description:
{description}

Created at: {created_at}""",
        channels=[MessageChannel.EMAIL, MessageChannel.PUSH, MessageChannel.IN_APP],
        variables=["incident_number", "category", "priority", "title", "address",
                   "latitude", "longitude", "description", "created_at"],
    ),

    "incident_assigned": MessageTemplate(
        id="incident_assigned",
        name="Incident Assigned",
        subject="Assigned: {incident_number} - {title}",
        body="""You have been assigned to incident {incident_number}.

Title: {title}
Category: {category}
Priority: {priority}

Location: {address}

Report to the scene immediately.

Incident details available in the application.""",
        channels=[MessageChannel.PUSH, MessageChannel.SMS, MessageChannel.IN_APP],
        variables=["incident_number", "title", "category", "priority", "address"],
    ),

    "incident_escalated": MessageTemplate(
        id="incident_escalated",
        name="Incident Escalated",
        subject="ESCALATED: {incident_number} - Priority {old_priority} → {new_priority}",
        body="""Incident {incident_number} has been escalated.

Previous Priority: {old_priority}
New Priority: {new_priority}

Reason: {reason}

Title: {title}
Category: {category}

Immediate attention required.""",
        channels=[MessageChannel.PUSH, MessageChannel.SMS, MessageChannel.EMAIL],
        variables=["incident_number", "old_priority", "new_priority", "reason",
                   "title", "category"],
    ),

    "alert_received": MessageTemplate(
        id="alert_received",
        name="New Alert Received",
        subject="Alert: {alert_type} - {severity}",
        body="""New alert received from {source}.

Type: {alert_type}
Severity: {severity}
Title: {title}

Location: {address}
Zone: {zone}

Received at: {received_at}""",
        channels=[MessageChannel.PUSH, MessageChannel.IN_APP],
        variables=["alert_type", "severity", "title", "address", "zone",
                   "source", "received_at"],
    ),

    "resource_dispatch": MessageTemplate(
        id="resource_dispatch",
        name="Dispatch Order",
        subject="DISPATCH: {incident_number}",
        body="""DISPATCH ORDER

Unit: {unit_name} ({call_sign})
Incident: {incident_number}

Title: {title}
Category: {category}
Priority: {priority}

Location: {address}
{latitude}, {longitude}

Respond immediately.""",
        channels=[MessageChannel.RADIO, MessageChannel.PUSH, MessageChannel.SMS],
        variables=["unit_name", "call_sign", "incident_number", "title",
                   "category", "priority", "address", "latitude", "longitude"],
    ),

    "shift_change": MessageTemplate(
        id="shift_change",
        name="Shift Change Notification",
        subject="Shift Change Reminder",
        body="""Shift change notification:

Your shift {shift_type} at {shift_time}.

Please ensure proper handoff of any active incidents.

Current active incidents: {active_count}""",
        channels=[MessageChannel.EMAIL, MessageChannel.PUSH],
        variables=["shift_type", "shift_time", "active_count"],
    ),

    "custom": MessageTemplate(
        id="custom",
        name="Custom Message",
        subject="{subject}",
        body="{body}",
        channels=[MessageChannel.EMAIL, MessageChannel.PUSH, MessageChannel.SMS, MessageChannel.IN_APP],
        variables=["subject", "body"],
    ),
}


class CommunicationHub:
    """Service for managing communications and message templates."""

    def __init__(self, db: AsyncSession):
        """Initialize communication hub."""
        self.db = db
        self._templates = TEMPLATES

    def get_template(self, template_id: str) -> MessageTemplate | None:
        """Get a message template by ID."""
        return self._templates.get(template_id)

    def list_templates(self) -> list[MessageTemplate]:
        """List all available templates."""
        return list(self._templates.values())

    def render_template(
        self,
        template_id: str,
        variables: dict[str, Any],
        channel: MessageChannel | None = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> RenderedMessage | None:
        """Render a template with variables.

        Args:
            template_id: The template to render
            variables: Dictionary of variable values
            channel: Override channel (uses first template channel if None)
            priority: Message priority

        Returns:
            RenderedMessage or None if template not found
        """
        template = self.get_template(template_id)
        if not template:
            return None

        # Fill in variables
        subject = template.subject
        body = template.body

        for var in template.variables:
            placeholder = "{" + var + "}"
            value = str(variables.get(var, "N/A"))
            subject = subject.replace(placeholder, value)
            body = body.replace(placeholder, value)

        return RenderedMessage(
            subject=subject,
            body=body,
            channel=channel or template.channels[0],
            priority=priority,
            metadata={"template_id": template_id, "variables": variables},
        )

    async def create_incident_notification(
        self,
        incident: Incident,
        event_type: str = "created",
    ) -> list[RenderedMessage]:
        """Create notifications for an incident event.

        Args:
            incident: The incident to notify about
            event_type: Type of event (created, assigned, escalated, etc.)

        Returns:
            List of rendered messages for different channels
        """
        template_map = {
            "created": "incident_created",
            "assigned": "incident_assigned",
            "escalated": "incident_escalated",
        }

        template_id = template_map.get(event_type, "incident_created")
        template = self.get_template(template_id)

        if not template:
            return []

        # Build variables from incident
        priority_names = {1: "Critical", 2: "High", 3: "Medium", 4: "Low", 5: "Minimal"}
        variables = {
            "incident_number": incident.incident_number,
            "category": incident.category.value.title(),
            "priority": priority_names.get(incident.priority, str(incident.priority)),
            "title": incident.title,
            "description": incident.description or "No description provided",
            "address": incident.address or "Unknown location",
            "latitude": str(incident.latitude),
            "longitude": str(incident.longitude),
            "created_at": incident.created_at.isoformat() if incident.created_at else "N/A",
        }

        # Determine priority from incident priority
        if incident.priority <= 1:
            msg_priority = MessagePriority.CRITICAL
        elif incident.priority == 2:
            msg_priority = MessagePriority.HIGH
        else:
            msg_priority = MessagePriority.NORMAL

        # Render for each channel
        messages = []
        for channel in template.channels:
            msg = self.render_template(
                template_id,
                variables,
                channel=channel,
                priority=msg_priority,
            )
            if msg:
                messages.append(msg)

        return messages

    async def create_alert_notification(
        self,
        alert: Alert,
    ) -> list[RenderedMessage]:
        """Create notifications for a new alert."""
        template = self.get_template("alert_received")
        if not template:
            return []

        variables = {
            "alert_type": alert.alert_type.replace("_", " ").title(),
            "severity": alert.severity.value.title(),
            "title": alert.title,
            "address": alert.address or "Unknown location",
            "zone": alert.zone or "Unknown zone",
            "source": alert.source.value.replace("_", " ").title(),
            "received_at": alert.received_at.isoformat() if alert.received_at else "N/A",
        }

        # Determine priority from severity
        severity_priority = {
            "critical": MessagePriority.CRITICAL,
            "high": MessagePriority.HIGH,
            "medium": MessagePriority.NORMAL,
            "low": MessagePriority.LOW,
            "info": MessagePriority.LOW,
        }
        msg_priority = severity_priority.get(alert.severity.value, MessagePriority.NORMAL)

        messages = []
        for channel in template.channels:
            msg = self.render_template(
                "alert_received",
                variables,
                channel=channel,
                priority=msg_priority,
            )
            if msg:
                messages.append(msg)

        return messages

    async def send_custom_message(
        self,
        subject: str,
        body: str,
        channels: list[MessageChannel],
        priority: MessagePriority = MessagePriority.NORMAL,
        recipients: list[str] | None = None,
    ) -> list[RenderedMessage]:
        """Send a custom message.

        Args:
            subject: Message subject
            body: Message body
            channels: Channels to send on
            priority: Message priority
            recipients: Optional list of recipient IDs

        Returns:
            List of rendered messages
        """
        messages = []
        for channel in channels:
            msg = self.render_template(
                "custom",
                {"subject": subject, "body": body},
                channel=channel,
                priority=priority,
            )
            if msg:
                msg.metadata["recipients"] = recipients or []
                messages.append(msg)

        return messages

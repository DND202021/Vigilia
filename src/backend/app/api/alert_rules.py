"""Alert Rules API endpoints.

Provides endpoints for viewing alert rules from device profiles and
querying recent IoT telemetry alerts.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_active_user, get_db
from app.models.alert import Alert, AlertSeverity, AlertSource
from app.models.device import IoTDevice
from app.models.user import User

# Router for device-scoped alert rules (registered under /devices prefix)
device_alert_rules_router = APIRouter()

# Router for alert-rules endpoints (registered under /alert-rules prefix)
alert_rules_router = APIRouter()


# ==================== Schemas ====================


class AlertRuleResponse(BaseModel):
    """Single alert rule from a device profile."""

    name: str
    metric: str
    condition: str  # gt, lt, gte, lte, eq, ne, range
    threshold: Any  # numeric, string, bool, or {"min","max"}
    severity: str
    cooldown_seconds: int


class DeviceAlertRulesResponse(BaseModel):
    """Alert rules for a specific device via its profile."""

    device_id: str
    device_name: str
    profile_id: str | None
    profile_name: str | None
    rules: list[AlertRuleResponse]


class AlertRuleEvaluationResponse(BaseModel):
    """Recent alert from IoT telemetry evaluation."""

    id: str
    alert_id: str
    device_id: str
    device_name: str
    rule_name: str
    metric: str
    condition: str
    threshold: Any
    actual_value: Any
    severity: str
    created_at: str
    incident_created: bool


# ==================== Device Alert Rules ====================


@device_alert_rules_router.get(
    "/{device_id}/alert-rules",
    response_model=DeviceAlertRulesResponse,
    tags=["Alert Rules"],
)
async def get_device_alert_rules(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DeviceAlertRulesResponse:
    """Get alert rules for a device from its profile.

    Returns the alert rules defined in the device's profile.
    If the device has no profile or the profile has no rules,
    returns an empty rules list.
    """
    result = await db.execute(
        select(IoTDevice)
        .options(selectinload(IoTDevice.profile))
        .where(IoTDevice.id == device_id)
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    rules: list[AlertRuleResponse] = []
    profile_id = None
    profile_name = None

    if device.profile and device.profile.alert_rules:
        profile_id = str(device.profile.id)
        profile_name = device.profile.name
        for rule in device.profile.alert_rules:
            rules.append(
                AlertRuleResponse(
                    name=rule.get("name", ""),
                    metric=rule.get("metric", ""),
                    condition=rule.get("condition", "gt"),
                    threshold=rule.get("threshold", 0),
                    severity=rule.get("severity", "medium"),
                    cooldown_seconds=rule.get("cooldown_seconds", 300),
                )
            )
    elif device.profile:
        profile_id = str(device.profile.id)
        profile_name = device.profile.name

    return DeviceAlertRulesResponse(
        device_id=str(device.id),
        device_name=device.name,
        profile_id=profile_id,
        profile_name=profile_name,
        rules=rules,
    )


# ==================== Recent Alert Evaluations ====================


@alert_rules_router.get(
    "/recent",
    response_model=list[AlertRuleEvaluationResponse],
    tags=["Alert Rules"],
)
async def get_recent_alert_evaluations(
    limit: int = Query(default=50, ge=1, le=200),
    severity: str | None = Query(default=None),
    device_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AlertRuleEvaluationResponse]:
    """Get recent IoT telemetry alerts.

    Returns alerts with source=IOT_TELEMETRY ordered by received_at DESC.
    Supports optional filtering by severity and device_id.
    """
    query = (
        select(Alert)
        .options(selectinload(Alert.device))
        .where(Alert.source == AlertSource.IOT_TELEMETRY)
    )

    if severity:
        try:
            severity_enum = AlertSeverity(severity.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity: {severity}. Must be one of: critical, high, medium, low, info",
            )
        query = query.where(Alert.severity == severity_enum)

    if device_id:
        query = query.where(Alert.device_id == device_id)

    query = query.order_by(Alert.received_at.desc()).limit(limit)

    result = await db.execute(query)
    alerts = result.scalars().all()

    response = []
    for alert in alerts:
        raw = alert.raw_payload or {}
        device_name = raw.get("device_name") or (alert.device.name if alert.device else "Unknown")

        response.append(
            AlertRuleEvaluationResponse(
                id=str(alert.id),
                alert_id=str(alert.id),
                device_id=str(alert.device_id) if alert.device_id else "",
                device_name=device_name,
                rule_name=raw.get("rule_name", alert.title),
                metric=raw.get("metric", ""),
                condition=raw.get("condition", ""),
                threshold=raw.get("threshold"),
                actual_value=raw.get("actual_value"),
                severity=alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
                created_at=alert.received_at.isoformat() if alert.received_at else "",
                incident_created=bool(alert.incidents) if alert.incidents else False,
            )
        )

    return response

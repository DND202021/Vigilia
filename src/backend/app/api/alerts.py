"""Alert Management API endpoints."""

import uuid
from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.alert import Alert as AlertModel
from app.models.alert import AlertStatus as AlertStatusModel
from app.services.socketio import emit_alert_updated

router = APIRouter()


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert processing status."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AlertSource(str, Enum):
    """Source of the alert."""

    FUNDAMENTUM = "fundamentum"
    ALARM_SYSTEM = "alarm_system"
    AXIS_MICROPHONE = "axis_microphone"
    SECURITY_SYSTEM = "security_system"
    MANUAL = "manual"
    EXTERNAL_API = "external_api"


class AlertLocation(BaseModel):
    """Alert location information."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str | None = None
    zone: str | None = None


class AlertResponse(BaseModel):
    """Alert response schema."""

    id: str
    source: AlertSource
    source_id: str | None
    severity: AlertSeverity
    status: AlertStatus
    alert_type: str
    title: str
    description: str | None
    location: AlertLocation | None
    raw_payload: dict | None
    created_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    linked_incident_id: str | None


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert."""

    notes: str | None = None


class AlertDismiss(BaseModel):
    """Schema for dismissing an alert."""

    reason: str = Field(..., min_length=10, max_length=500)


class PaginatedAlertResponse(BaseModel):
    """Paginated alert response."""

    items: list[AlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


def alert_to_response(alert: AlertModel) -> AlertResponse:
    """Convert an alert model to response."""
    return AlertResponse(
        id=str(alert.id),
        source=AlertSource(alert.source.value),
        source_id=alert.source_id,
        severity=AlertSeverity(alert.severity.value),
        status=AlertStatus(alert.status.value),
        alert_type=alert.alert_type,
        title=alert.title,
        description=alert.description,
        location=AlertLocation(
            latitude=alert.latitude,
            longitude=alert.longitude,
            address=alert.address,
            zone=alert.zone,
        ) if alert.latitude and alert.longitude else None,
        raw_payload=alert.raw_payload,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=str(alert.acknowledged_by_id) if alert.acknowledged_by_id else None,
        linked_incident_id=str(alert.incidents[0].id) if alert.incidents else None,
    )


@router.get("", response_model=PaginatedAlertResponse)
async def list_alerts(
    status: AlertStatus | None = None,
    severity: AlertSeverity | None = None,
    alert_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedAlertResponse:
    """List alerts with optional filters and pagination."""
    query = select(AlertModel)

    if status:
        query = query.where(AlertModel.status == AlertStatusModel(status.value))
    if severity:
        query = query.where(AlertModel.severity == severity.value)
    if alert_type:
        query = query.where(AlertModel.alert_type == alert_type)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(AlertModel.created_at.desc())

    result = await db.execute(query)
    alerts = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedAlertResponse(
        items=[alert_to_response(alert) for alert in alerts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/pending", response_model=list[AlertResponse])
async def get_pending_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AlertResponse]:
    """Get all pending alerts that need attention."""
    query = select(AlertModel).where(
        AlertModel.status == AlertStatusModel.PENDING
    ).order_by(AlertModel.severity, AlertModel.created_at.desc())

    result = await db.execute(query)
    alerts = result.scalars().all()

    return [alert_to_response(alert) for alert in alerts]


@router.get("/unacknowledged", response_model=list[AlertResponse])
async def get_unacknowledged_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AlertResponse]:
    """Get all unacknowledged alerts (pending or processing)."""
    query = select(AlertModel).where(
        AlertModel.status.in_([AlertStatusModel.PENDING, AlertStatusModel.PROCESSING])
    ).order_by(AlertModel.severity, AlertModel.created_at.desc())

    result = await db.execute(query)
    alerts = result.scalars().all()

    return [alert_to_response(alert) for alert in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AlertResponse:
    """Get alert by ID."""
    try:
        alert_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid alert ID format",
        )

    query = select(AlertModel).where(AlertModel.id == alert_uuid)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    return alert_to_response(alert)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    data: AlertAcknowledge,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AlertResponse:
    """Acknowledge an alert."""
    try:
        alert_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid alert ID format",
        )

    query = select(AlertModel).where(AlertModel.id == alert_uuid)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    alert.status = AlertStatusModel.ACKNOWLEDGED
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by_id = current_user.id

    await db.commit()
    await db.refresh(alert)

    response = alert_to_response(alert)
    await emit_alert_updated(response.model_dump(mode="json"))

    return response


@router.post("/{alert_id}/dismiss", response_model=AlertResponse)
async def dismiss_alert(
    alert_id: str,
    data: AlertDismiss,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AlertResponse:
    """Dismiss an alert with reason."""
    try:
        alert_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid alert ID format",
        )

    query = select(AlertModel).where(AlertModel.id == alert_uuid)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    if alert.status == AlertStatusModel.DISMISSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert is already dismissed",
        )

    alert.status = AlertStatusModel.DISMISSED
    alert.dismissed_by_id = current_user.id
    alert.dismissal_reason = data.reason

    await db.commit()
    await db.refresh(alert)

    response = alert_to_response(alert)
    await emit_alert_updated(response.model_dump(mode="json"))

    return response


class CreateIncidentFromAlertRequest(BaseModel):
    """Request to create incident from alert."""

    title: str | None = None
    category: str | None = None
    priority: int | None = None


@router.post("/{alert_id}/create-incident")
async def create_incident_from_alert(
    alert_id: str,
    request: CreateIncidentFromAlertRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Create an incident from an alert."""
    from app.services.alert_to_incident import AlertToIncidentService
    from app.models.incident import IncidentCategory, IncidentPriority
    from app.api.incidents import incident_to_response

    try:
        alert_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid alert ID format",
        )

    # Check user has agency
    if not current_user.agency_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an agency to create incidents",
        )

    query = select(AlertModel).where(AlertModel.id == alert_uuid)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    # Check if alert already has an incident
    if alert.incidents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert already has a linked incident",
        )

    # Parse overrides if provided
    category_override = None
    priority_override = None

    if request:
        if request.category:
            try:
                category_override = IncidentCategory(request.category)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category: {request.category}",
                )

        if request.priority:
            try:
                priority_override = IncidentPriority(request.priority)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid priority: {request.priority}",
                )

    service = AlertToIncidentService(db)
    incident = await service.convert_to_incident(
        alert=alert,
        user=current_user,
        title_override=request.title if request else None,
        category_override=category_override,
        priority_override=priority_override,
    )

    return {
        "message": "Incident created from alert",
        "incident_id": str(incident.id),
        "incident_number": incident.incident_number,
    }

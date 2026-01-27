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
    # Sound anomaly fields
    device_id: str | None = None
    building_id: str | None = None
    floor_plan_id: str | None = None
    audio_clip_id: str | None = None
    confidence: float | None = None
    peak_level_db: float | None = None
    background_level_db: float | None = None
    risk_level: str | None = None
    occurrence_count: int = 1
    last_occurrence: datetime | None = None
    assigned_to_id: str | None = None


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
        device_id=str(alert.device_id) if alert.device_id else None,
        building_id=str(alert.building_id) if alert.building_id else None,
        floor_plan_id=str(alert.floor_plan_id) if alert.floor_plan_id else None,
        audio_clip_id=str(alert.audio_clip_id) if alert.audio_clip_id else None,
        confidence=alert.confidence,
        peak_level_db=alert.peak_level_db,
        background_level_db=alert.background_level_db,
        risk_level=alert.risk_level,
        occurrence_count=alert.occurrence_count,
        last_occurrence=alert.last_occurrence,
        assigned_to_id=str(alert.assigned_to_id) if alert.assigned_to_id else None,
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


class AlertAssign(BaseModel):
    """Schema for assigning alert to a user."""
    assigned_to_id: str


# ==================== Sound Anomaly Alert Endpoints ====================

@router.get("/sound-anomalies", response_model=PaginatedAlertResponse)
async def list_sound_anomaly_alerts(
    building_id: str | None = None,
    floor_plan_id: str | None = None,
    device_id: str | None = None,
    severity: AlertSeverity | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedAlertResponse:
    """List alerts specifically from sound anomaly detection (Axis microphones)."""
    query = select(AlertModel).where(
        AlertModel.source == AlertStatusModel("axis_microphone") if False
        else AlertModel.alert_type.in_([
            "gunshot", "explosion", "glass_break", "aggression", "scream", "car_alarm"
        ])
    )

    if building_id:
        query = query.where(AlertModel.building_id == uuid.UUID(building_id))
    if floor_plan_id:
        query = query.where(AlertModel.floor_plan_id == uuid.UUID(floor_plan_id))
    if device_id:
        query = query.where(AlertModel.device_id == uuid.UUID(device_id))
    if severity:
        query = query.where(AlertModel.severity == severity.value)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(AlertModel.created_at.desc())
    result = await db.execute(query)
    alerts = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedAlertResponse(
        items=[alert_to_response(alert) for alert in alerts],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.get("/alarms", response_model=PaginatedAlertResponse)
async def list_alarms(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedAlertResponse:
    """List critical alarms (high risk level sound events)."""
    query = select(AlertModel).where(
        AlertModel.severity.in_(["critical", "high"]),
        AlertModel.alert_type.in_(["gunshot", "explosion", "glass_break", "aggression"]),
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(AlertModel.created_at.desc())
    result = await db.execute(query)
    alerts = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedAlertResponse(
        items=[alert_to_response(alert) for alert in alerts],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.get("/noise-warnings", response_model=PaginatedAlertResponse)
async def list_noise_warnings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedAlertResponse:
    """List noise warning alerts (scream, car alarm)."""
    query = select(AlertModel).where(
        AlertModel.alert_type.in_(["scream", "car_alarm"]),
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(AlertModel.created_at.desc())
    result = await db.execute(query)
    alerts = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedAlertResponse(
        items=[alert_to_response(alert) for alert in alerts],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/{alert_id}/assign", response_model=AlertResponse)
async def assign_alert(
    alert_id: str,
    data: AlertAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AlertResponse:
    """Assign an alert to a user."""
    try:
        alert_uuid = uuid.UUID(alert_id)
        user_uuid = uuid.UUID(data.assigned_to_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")

    query = select(AlertModel).where(AlertModel.id == alert_uuid)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.assigned_to_id = user_uuid
    await db.commit()
    await db.refresh(alert)

    response = alert_to_response(alert)
    await emit_alert_updated(response.model_dump(mode="json"))
    return response


@router.get("/history/chart")
async def get_alert_history_chart(
    building_id: str | None = None,
    floor_plan_id: str | None = None,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get alert level history data for charting (daily counts by severity)."""
    from datetime import timedelta
    from sqlalchemy import cast, Date

    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = select(
        cast(AlertModel.created_at, Date).label("date"),
        AlertModel.severity,
        func.count(AlertModel.id).label("count"),
    ).where(AlertModel.created_at >= since)

    if building_id:
        query = query.where(AlertModel.building_id == uuid.UUID(building_id))
    if floor_plan_id:
        query = query.where(AlertModel.floor_plan_id == uuid.UUID(floor_plan_id))

    query = query.group_by(
        cast(AlertModel.created_at, Date), AlertModel.severity
    ).order_by(cast(AlertModel.created_at, Date))

    result = await db.execute(query)
    rows = result.all()

    chart_data = []
    for row in rows:
        chart_data.append({
            "date": row[0].isoformat() if row[0] else None,
            "severity": row[1].value if hasattr(row[1], 'value') else row[1],
            "count": row[2],
        })

    return {"data": chart_data, "days": days}


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

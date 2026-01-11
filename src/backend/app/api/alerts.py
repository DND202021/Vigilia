"""Alert Management API endpoints."""

from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.alert import Alert as AlertModel
from app.models.alert import AlertStatus as AlertStatusModel

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


@router.get("/", response_model=PaginatedAlertResponse)
async def list_alerts(
    status: AlertStatus | None = None,
    severity: AlertSeverity | None = None,
    source: AlertSource | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedAlertResponse:
    """List alerts with optional filters and pagination."""
    from sqlalchemy import func

    query = select(AlertModel)

    if status:
        query = query.where(AlertModel.status == AlertStatusModel(status.value))
    if severity:
        query = query.where(AlertModel.severity == severity.value)
    if source:
        query = query.where(AlertModel.source == source.value)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(AlertModel.created_at.desc())

    result = await db.execute(query)
    alerts = result.scalars().all()

    items = [
        AlertResponse(
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
        for alert in alerts
    ]

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedAlertResponse(
        items=items,
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

    return [
        AlertResponse(
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
        for alert in alerts
    ]


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str) -> AlertResponse:
    """Get alert by ID."""
    # TODO: Implement alert retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Alert retrieval not yet implemented",
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(alert_id: str, data: AlertAcknowledge) -> AlertResponse:
    """Acknowledge an alert."""
    # TODO: Implement alert acknowledgment
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Alert acknowledgment not yet implemented",
    )


@router.post("/{alert_id}/dismiss", response_model=AlertResponse)
async def dismiss_alert(alert_id: str, data: AlertDismiss) -> AlertResponse:
    """Dismiss an alert with reason."""
    # TODO: Implement alert dismissal
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Alert dismissal not yet implemented",
    )


@router.post("/{alert_id}/create-incident")
async def create_incident_from_alert(alert_id: str) -> dict[str, str]:
    """Create an incident from an alert."""
    # TODO: Implement incident creation from alert
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Incident creation from alert not yet implemented",
    )

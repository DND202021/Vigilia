"""Notification Delivery Status API endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user, Permission, has_permission
from app.models.user import User
from app.models.notification_delivery import NotificationDelivery, DeliveryStatus

router = APIRouter()


# ===========================
# Response Models
# ===========================

class DeliveryResponse(BaseModel):
    """Response model for a single notification delivery."""

    id: str
    alert_id: str
    user_id: str
    channel: str
    status: str
    external_id: str | None
    attempts: int
    sent_at: datetime | None
    delivered_at: datetime | None
    failed_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DeliveryStatsResponse(BaseModel):
    """Response model for delivery statistics aggregation."""

    total: int
    sent: int
    delivered: int
    failed: int
    pending: int


# ===========================
# API Endpoints
# ===========================

@router.get("/deliveries", response_model=list[DeliveryResponse])
async def list_deliveries(
    alert_id: str | None = Query(None, description="Filter by alert ID"),
    status: str | None = Query(None, description="Filter by delivery status"),
    channel: str | None = Query(None, description="Filter by delivery channel"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[DeliveryResponse]:
    """
    List notification delivery records with optional filtering.

    Requires ALERTS_MANAGE permission (admin/dispatcher access).
    """
    # Check permission
    if not has_permission(current_user, Permission.ALERTS_MANAGE):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to view delivery history",
        )

    # Build query
    query = select(NotificationDelivery).order_by(NotificationDelivery.created_at.desc())

    # Apply filters
    if alert_id:
        try:
            alert_uuid = UUID(alert_id)
            query = query.where(NotificationDelivery.alert_id == alert_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid alert_id format")

    if status:
        # Validate status value
        valid_statuses = [s.value for s in DeliveryStatus]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            )
        query = query.where(NotificationDelivery.status == status)

    if channel:
        query = query.where(NotificationDelivery.channel == channel)

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    deliveries = list(result.scalars().all())

    # Convert to response models
    return [
        DeliveryResponse(
            id=str(d.id),
            alert_id=str(d.alert_id),
            user_id=str(d.user_id),
            channel=d.channel,
            status=d.status,
            external_id=d.external_id,
            attempts=d.attempts,
            sent_at=d.sent_at,
            delivered_at=d.delivered_at,
            failed_at=d.failed_at,
            error_message=d.error_message,
            created_at=d.created_at,
        )
        for d in deliveries
    ]


@router.get("/deliveries/stats", response_model=DeliveryStatsResponse)
async def get_delivery_stats(
    alert_id: str | None = Query(None, description="Filter by alert ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DeliveryStatsResponse:
    """
    Get aggregate delivery statistics.

    Optionally filter by alert_id to get stats for a specific alert.
    Requires ALERTS_MANAGE permission.
    """
    # Check permission
    if not has_permission(current_user, Permission.ALERTS_MANAGE):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to view delivery statistics",
        )

    # Build base query
    base_query = select(NotificationDelivery)

    if alert_id:
        try:
            alert_uuid = UUID(alert_id)
            base_query = base_query.where(NotificationDelivery.alert_id == alert_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid alert_id format")

    # Get total count
    total_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # Get counts by status
    status_query = (
        select(
            NotificationDelivery.status,
            func.count(NotificationDelivery.id).label("count"),
        )
        .select_from(base_query.subquery())
        .group_by(NotificationDelivery.status)
    )
    status_result = await db.execute(status_query)
    status_counts = {row.status: row.count for row in status_result.all()}

    # Build response
    return DeliveryStatsResponse(
        total=total,
        sent=status_counts.get(DeliveryStatus.SENT.value, 0),
        delivered=status_counts.get(DeliveryStatus.DELIVERED.value, 0),
        failed=status_counts.get(DeliveryStatus.FAILED.value, 0),
        pending=status_counts.get(DeliveryStatus.PENDING.value, 0),
    )

"""Dashboard API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.incident import Incident, IncidentStatus
from app.models.alert import Alert, AlertStatus
from app.models.resource import Resource, ResourceStatus

router = APIRouter()


class DashboardStats(BaseModel):
    """Dashboard statistics response."""

    active_incidents: int
    pending_alerts: int
    available_resources: int
    total_resources: int


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DashboardStats:
    """Get dashboard statistics."""
    # Count active incidents
    active_statuses = [
        IncidentStatus.NEW,
        IncidentStatus.ASSIGNED,
        IncidentStatus.EN_ROUTE,
        IncidentStatus.ON_SCENE,
    ]
    active_incidents_query = select(func.count(Incident.id)).where(
        Incident.status.in_(active_statuses)
    )
    active_incidents_result = await db.execute(active_incidents_query)
    active_incidents = active_incidents_result.scalar() or 0

    # Count pending alerts
    pending_alerts_query = select(func.count(Alert.id)).where(
        Alert.status == AlertStatus.PENDING
    )
    pending_alerts_result = await db.execute(pending_alerts_query)
    pending_alerts = pending_alerts_result.scalar() or 0

    # Count available resources
    available_resources_query = select(func.count(Resource.id)).where(
        Resource.status == ResourceStatus.AVAILABLE
    )
    available_resources_result = await db.execute(available_resources_query)
    available_resources = available_resources_result.scalar() or 0

    # Count total resources
    total_resources_query = select(func.count(Resource.id))
    total_resources_result = await db.execute(total_resources_query)
    total_resources = total_resources_result.scalar() or 0

    return DashboardStats(
        active_incidents=active_incidents,
        pending_alerts=pending_alerts,
        available_resources=available_resources,
        total_resources=total_resources,
    )

"""Telemetry query REST API endpoints.

Provides endpoints for querying stored telemetry data with support for
raw, hourly, and daily aggregation levels.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.user import User
from app.services.telemetry_query_service import TelemetryQueryService

router = APIRouter(tags=["Telemetry"])


class TelemetryDataPoint(BaseModel):
    """Single raw telemetry data point."""

    time: str
    device_id: str
    metric_name: str
    value: float | int | str | bool | None


class TelemetryAggregatePoint(BaseModel):
    """Aggregated telemetry data point."""

    time: str
    metric_name: str
    avg: float | None
    min: float | None
    max: float | None
    count: int | None = None


class TelemetryQueryResponse(BaseModel):
    """Telemetry query response."""

    device_id: str
    aggregation: str
    count: int
    data: list[TelemetryDataPoint] | list[TelemetryAggregatePoint]


class AvailableMetricsResponse(BaseModel):
    """Available metrics for a device."""

    device_id: str
    metrics: list[str]


@router.get("/{device_id}/telemetry", response_model=TelemetryQueryResponse)
async def query_telemetry(
    device_id: UUID,
    metric_name: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    aggregation: str = Query(default="raw", pattern="^(raw|hourly|daily)$"),
    limit: int = Query(default=1000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Query telemetry data for a device.

    Supports raw, hourly, and daily aggregation levels.
    Hourly/daily aggregations require metric_name, start_time, and end_time.
    """
    service = TelemetryQueryService(db)

    if aggregation == "raw":
        data = await service.query_raw(
            device_id, metric_name, start_time, end_time, limit, offset
        )
    elif aggregation in ("hourly", "daily"):
        if not metric_name or not start_time or not end_time:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="metric_name, start_time, and end_time are required for aggregate queries",
            )
        if aggregation == "hourly":
            data = await service.query_hourly(device_id, metric_name, start_time, end_time)
        else:
            data = await service.query_daily(device_id, metric_name, start_time, end_time)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid aggregation level. Use: raw, hourly, daily",
        )

    return TelemetryQueryResponse(
        device_id=str(device_id),
        aggregation=aggregation,
        count=len(data),
        data=data,
    )


@router.get("/{device_id}/telemetry/metrics", response_model=AvailableMetricsResponse)
async def get_available_metrics(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get available metric names for a device."""
    service = TelemetryQueryService(db)
    metrics = await service.get_available_metrics(device_id)
    return AvailableMetricsResponse(device_id=str(device_id), metrics=metrics)

"""HTTP telemetry ingestion endpoint.

Provides an HTTP POST endpoint for device telemetry ingestion
as an alternative to MQTT. Uses the same TelemetryIngestionService
for validation and Redis Stream buffering.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db, get_redis
from app.models.user import User
from app.services.telemetry_ingestion_service import (
    TelemetryIngestionService,
    TelemetryIngestionError,
)

router = APIRouter(tags=["Telemetry"])


class TelemetryIngestRequest(BaseModel):
    """Telemetry payload from device via HTTP."""

    metrics: dict[str, float | int | str | bool]
    timestamp: str | None = None
    message_id: str | None = None


class TelemetryIngestResponse(BaseModel):
    """Response for telemetry ingestion."""

    status: str
    device_id: str


@router.post(
    "/{device_id}/telemetry",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_telemetry(
    device_id: UUID,
    payload: TelemetryIngestRequest,
    db: AsyncSession = Depends(get_db),
    redis_client=Depends(get_redis),
    current_user: User = Depends(get_current_active_user),
):
    """Ingest telemetry from HTTP POST (webhook-style push).

    Validates telemetry against device profile and buffers to Redis Stream
    for async batch processing. Returns 202 Accepted since telemetry is
    buffered, not immediately stored.
    """
    telemetry = {
        "device_id": str(device_id),
        "metrics": payload.metrics,
        "device_timestamp": payload.timestamp,
        "server_timestamp": datetime.now(timezone.utc).isoformat(),
        "message_id": payload.message_id,
    }

    try:
        service = TelemetryIngestionService(db, redis_client)
        await service.validate_and_buffer(telemetry)
        return TelemetryIngestResponse(status="accepted", device_id=str(device_id))
    except TelemetryIngestionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

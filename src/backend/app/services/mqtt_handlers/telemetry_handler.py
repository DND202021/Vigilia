"""MQTT telemetry handler for device telemetry ingestion.

Receives telemetry from MQTT topic agency/{agency_id}/device/{device_id}/telemetry,
builds a dual-timestamp telemetry dict, validates via TelemetryIngestionService,
and buffers to Redis Streams for async batch processing.
"""

import uuid
from datetime import datetime, timezone

import structlog

from app.core.deps import async_session_factory, get_redis
from app.services.telemetry_ingestion_service import (
    TelemetryIngestionService,
    TelemetryIngestionError,
)

logger = structlog.get_logger()


async def handle_device_telemetry(topic: str, payload: dict) -> None:
    """Handle device telemetry messages from MQTT.

    Topic format: agency/{agency_id}/device/{device_id}/telemetry

    Payload should contain:
    - metrics: dict of {metric_name: value} pairs
    - timestamp (optional): ISO 8601 device-provided timestamp
    - message_id (optional): unique ID for QoS 1 deduplication

    Args:
        topic: MQTT topic string.
        payload: JSON payload dictionary.
    """
    try:
        # Parse topic: agency/{agency_id}/device/{device_id}/telemetry
        parts = topic.split("/")

        if len(parts) != 5 or parts[0] != "agency" or parts[2] != "device" or parts[4] != "telemetry":
            logger.warning("Invalid telemetry topic format", topic=topic)
            return

        agency_id_str = parts[1]
        device_id_str = parts[3]

        # Validate UUID format
        try:
            uuid.UUID(agency_id_str)
            uuid.UUID(device_id_str)
        except (ValueError, AttributeError):
            logger.warning(
                "Invalid UUID format in telemetry topic",
                topic=topic,
                agency_id=agency_id_str,
                device_id=device_id_str,
            )
            return

        # Build telemetry dict with dual timestamps
        telemetry = {
            "device_id": device_id_str,
            "metrics": payload.get("metrics", {}),
            "device_timestamp": payload.get("timestamp"),
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
            "message_id": payload.get("message_id"),
        }

        # Get DB session and Redis client (outside request context)
        async with async_session_factory() as db:
            redis_client = await get_redis()
            service = TelemetryIngestionService(db, redis_client)

            await service.validate_and_buffer(telemetry)

    except TelemetryIngestionError as e:
        logger.warning(
            "Telemetry validation failed",
            topic=topic,
            device_id=device_id_str if 'device_id_str' in dir() else "unknown",
            error=str(e),
        )
    except Exception as e:
        logger.error(
            "Telemetry handler error",
            topic=topic,
            error=str(e),
            exc_info=True,
        )

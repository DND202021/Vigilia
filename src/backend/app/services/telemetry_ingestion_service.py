"""Telemetry ingestion service for validating and buffering device telemetry.

Accepts telemetry from MQTT and HTTP sources, validates against device profile
schemas, applies dual-timestamp strategy, handles QoS 1 deduplication, and
buffers validated telemetry to Redis Streams for downstream batch processing.
"""

import json
import uuid
from datetime import datetime, timezone

import structlog
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import IoTDevice
from app.models.device_profile import DeviceProfile

logger = structlog.get_logger()

STREAM_NAME = "telemetry:stream"
STREAM_MAXLEN = 100000
DEDUP_TTL_SECONDS = 60


class TelemetryIngestionError(Exception):
    """Telemetry ingestion validation or processing error."""
    pass


class TelemetryIngestionService:
    """Buffers telemetry to Redis Streams from MQTT/HTTP.

    Validates telemetry metrics against the device's profile telemetry_schema,
    deduplicates QoS 1 MQTT messages via message_id, and writes to a Redis Stream
    for async batch processing by the worker service.
    """

    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis):
        self.db = db
        self.redis = redis_client
        self._profile_cache: dict[str, DeviceProfile | None] = {}

    async def validate_and_buffer(self, telemetry: dict) -> None:
        """Validate telemetry and buffer to Redis Stream.

        Args:
            telemetry: Dict with keys: device_id, metrics, server_timestamp,
                       device_timestamp (optional), message_id (optional).

        Raises:
            TelemetryIngestionError: If validation fails.
        """
        device_id = telemetry["device_id"]

        # QoS 1 deduplication via message_id
        message_id = telemetry.get("message_id")
        if message_id:
            cache_key = f"telemetry:dedup:{message_id}"
            was_set = await self.redis.set(cache_key, "1", nx=True, ex=DEDUP_TTL_SECONDS)
            if not was_set:
                logger.debug("Duplicate telemetry message ignored", message_id=message_id, device_id=device_id)
                return

        # Fetch device profile for validation
        device_profile = await self._get_device_profile(device_id)

        if device_profile and device_profile.telemetry_schema:
            validated_metrics = self._validate_metrics(telemetry.get("metrics", {}), device_profile.telemetry_schema)
            telemetry["metrics"] = validated_metrics
        elif not device_profile:
            logger.warning("Device has no profile, accepting all telemetry", device_id=device_id)

        # Buffer to Redis Stream
        await self.redis.xadd(
            STREAM_NAME,
            {
                "device_id": device_id,
                "payload": json.dumps(telemetry),
            },
            maxlen=STREAM_MAXLEN,
        )
        logger.debug("Telemetry buffered", device_id=device_id)

    def _validate_metrics(self, metrics: dict, telemetry_schema: list) -> dict:
        """Validate metrics against device profile telemetry schema.

        Args:
            metrics: Dict of {metric_name: value} pairs.
            telemetry_schema: List of schema items like
                [{"name": "temperature", "type": "numeric", ...}].

        Returns:
            Validated metrics dict.

        Raises:
            TelemetryIngestionError: If metric key is unknown or type mismatches.
        """
        schema_lookup = {item["name"]: item["type"] for item in telemetry_schema}
        validated = {}

        for key, value in metrics.items():
            if key not in schema_lookup:
                raise TelemetryIngestionError(f"Unknown metric key: {key}")

            expected_type = schema_lookup[key]

            # CRITICAL: Check bool BEFORE numeric because isinstance(True, int) is True
            if expected_type == "boolean":
                if not isinstance(value, bool):
                    raise TelemetryIngestionError(
                        f"Metric {key} expected boolean, got {type(value).__name__}"
                    )
            elif expected_type == "numeric":
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise TelemetryIngestionError(
                        f"Metric {key} expected numeric, got {type(value).__name__}"
                    )
            elif expected_type == "string":
                if not isinstance(value, str):
                    raise TelemetryIngestionError(
                        f"Metric {key} expected string, got {type(value).__name__}"
                    )

            validated[key] = value

        return validated

    async def _get_device_profile(self, device_id: str) -> DeviceProfile | None:
        """Get device profile for a device, with in-memory cache.

        Args:
            device_id: Device UUID as string.

        Returns:
            DeviceProfile or None if device has no profile.
        """
        if device_id in self._profile_cache:
            return self._profile_cache[device_id]

        result = await self.db.execute(
            select(IoTDevice).where(IoTDevice.id == uuid.UUID(device_id))
        )
        device = result.scalar_one_or_none()

        if not device or not device.profile_id:
            self._profile_cache[device_id] = None
            return None

        result = await self.db.execute(
            select(DeviceProfile).where(DeviceProfile.id == device.profile_id)
        )
        profile = result.scalar_one_or_none()
        self._profile_cache[device_id] = profile
        return profile

"""MQTT handler for device config/reported messages.

Receives reported config from MQTT topic agency/{agency_id}/device/{device_id}/config/reported,
validates the payload, and delegates to DeviceTwinService for state update.
"""

import uuid

import structlog

from app.core.deps import async_session_factory

logger = structlog.get_logger()


async def handle_device_config_reported(topic: str, payload: dict) -> None:
    """Handle device reported config messages from MQTT.

    Topic format: agency/{agency_id}/device/{device_id}/config/reported

    Payload should contain:
    - config: dict of current device configuration
    - version (optional): device's version counter for stale detection
    """
    try:
        # Parse topic: agency/{agency_id}/device/{device_id}/config/reported
        parts = topic.split("/")

        if (
            len(parts) != 6
            or parts[0] != "agency"
            or parts[2] != "device"
            or parts[4] != "config"
            or parts[5] != "reported"
        ):
            logger.warning("Invalid config/reported topic format", topic=topic)
            return

        device_id_str = parts[3]

        # Validate UUID format
        try:
            device_id = uuid.UUID(device_id_str)
        except (ValueError, AttributeError):
            logger.warning(
                "Invalid device_id UUID in config/reported topic",
                topic=topic,
                device_id=device_id_str,
            )
            return

        # Extract config from payload
        reported_config = payload.get("config")
        if not isinstance(reported_config, dict):
            logger.warning(
                "Invalid config format (expected dict)",
                topic=topic,
                device_id=device_id_str,
            )
            return

        # Extract optional version
        reported_version = payload.get("version")

        # Update twin via service (outside request context)
        async with async_session_factory() as db:
            # Lazy import to avoid circular imports
            from app.main import get_mqtt_service
            from app.services.device_twin_service import DeviceTwinService

            mqtt_service = await get_mqtt_service()
            service = DeviceTwinService(db, mqtt_service)

            await service.update_reported_config(
                device_id=device_id,
                reported_config=reported_config,
                reported_version=reported_version,
            )

    except Exception as e:
        logger.error(
            "Config reported handler error",
            topic=topic,
            error=str(e),
            exc_info=True,
        )

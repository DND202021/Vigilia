"""MQTT device registration handler for auto-activation.

When a provisioned device first connects to MQTT and publishes to its registration
topic (agency/{agency_id}/device/{device_id}/register), this handler updates the
device status from pending to active and records metadata from the registration payload.
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import async_session_factory
from app.models.device import IoTDevice
from app.models.building import Building

logger = structlog.get_logger()


async def handle_device_registration(topic: str, payload: dict) -> None:
    """Handle device registration messages for auto-activation.

    Topic format: agency/{agency_id}/device/{device_id}/register

    Payload should contain device metadata:
    - serial_number (optional)
    - firmware_version (optional)
    - mac_address (optional)

    Actions:
    1. Parse agency_id and device_id from topic
    2. Verify device exists and agency matches
    3. Update provisioning_status from pending to active
    4. Update device metadata from payload
    5. Set status to online and record last_seen timestamp

    This handler is idempotent - re-registration of already-active devices
    is a no-op (logs info and returns).

    Args:
        topic: MQTT topic string
        payload: JSON payload dictionary
    """
    try:
        # Parse topic: agency/{agency_id}/device/{device_id}/register
        parts = topic.split("/")

        if len(parts) != 5 or parts[0] != "agency" or parts[2] != "device" or parts[4] != "register":
            logger.warning("invalid registration topic format", topic=topic)
            return

        agency_id_str = parts[1]
        device_id_str = parts[3]

        # Validate UUID format
        try:
            agency_id = uuid.UUID(agency_id_str)
            device_id = uuid.UUID(device_id_str)
        except (ValueError, AttributeError):
            logger.warning(
                "invalid UUID format in registration topic",
                topic=topic,
                agency_id=agency_id_str,
                device_id=device_id_str,
            )
            return

        # Get database session (outside request context, use factory directly)
        async with async_session_factory() as db:
            # Query device with building to verify agency ownership
            result = await db.execute(
                select(IoTDevice, Building)
                .join(Building, IoTDevice.building_id == Building.id)
                .where(IoTDevice.id == device_id)
            )
            row = result.one_or_none()

            if not row:
                logger.warning(
                    "device not found for registration",
                    device_id=device_id_str,
                    topic=topic,
                )
                return

            device, building = row

            # Verify agency ownership
            if building.agency_id != agency_id:
                logger.warning(
                    "agency mismatch for device registration",
                    device_id=device_id_str,
                    expected_agency=str(agency_id),
                    actual_agency=str(building.agency_id),
                    topic=topic,
                )
                return

            # Check if device is already activated (idempotent)
            if device.provisioning_status != "pending":
                logger.info(
                    "device already activated or not pending",
                    device_id=device_id_str,
                    provisioning_status=device.provisioning_status,
                    topic=topic,
                )
                return

            # Auto-activate device
            device.provisioning_status = "active"
            device.status = "online"
            device.last_seen = datetime.now(timezone.utc)

            # Update device metadata from payload
            if "serial_number" in payload:
                device.serial_number = payload["serial_number"]
            if "firmware_version" in payload:
                device.firmware_version = payload["firmware_version"]
            if "mac_address" in payload:
                device.mac_address = payload["mac_address"]

            # Commit transaction
            await db.commit()

            logger.info(
                "device auto-activated",
                device_id=device_id_str,
                agency_id=agency_id_str,
                serial_number=device.serial_number,
                firmware_version=device.firmware_version,
                topic=topic,
            )

    except Exception as e:
        logger.error(
            "registration handler error",
            topic=topic,
            error=str(e),
            exc_info=True,
        )

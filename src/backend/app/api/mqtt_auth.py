"""MQTT authentication webhook endpoints for Mosquitto broker integration.

This module provides HTTP authentication endpoints for the mosquitto-go-auth plugin.
The plugin sends form-encoded POST requests and expects HTTP status codes:
- 200 = allow
- 401 = authentication failure
- 403 = authorization failure

See: https://github.com/iegomez/mosquitto-go-auth
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Response
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.models.device_credentials import DeviceCredentials
from app.models.device import IoTDevice
from app.models.building import Building

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()


@router.post("/mqtt/auth")
async def authenticate_device(
    username: str = Form(...),
    password: str = Form(...),
    clientid: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Authenticate device credentials (mosquitto-go-auth getuser endpoint).

    Called by Mosquitto via mosquitto-go-auth HTTP backend when a client connects.

    Args:
        username: Device username (format: "device_{device_id}" or "vigilia-backend")
        password: Access token or empty for certificate auth
        clientid: MQTT client ID
        db: Database session

    Returns:
        Response with status code 200 (allow) or 401 (deny)
    """
    try:
        # Internal service account
        if username == "vigilia-backend":
            # TODO: Validate against settings.mqtt_vigilia_internal_password
            # For now, accept any password for vigilia-backend (will be secured in future)
            logger.info("vigilia-backend authenticated", clientid=clientid)
            return Response(status_code=200)

        # Health check account (for monitoring)
        if username == "health-check":
            logger.debug("health-check authenticated", clientid=clientid)
            return Response(status_code=200)

        # Device authentication
        # Username format: device_{device_id}
        if not username.startswith("device_"):
            logger.warning("invalid username format", username=username, clientid=clientid)
            return Response(status_code=401)

        try:
            device_id_str = username.replace("device_", "")
            # Validate UUID format (will raise ValueError if invalid)
            import uuid
            device_id = uuid.UUID(device_id_str)
        except (ValueError, AttributeError):
            logger.warning("invalid device_id in username", username=username, clientid=clientid)
            return Response(status_code=401)

        # Query device credentials
        result = await db.execute(
            select(DeviceCredentials).where(DeviceCredentials.device_id == device_id)
        )
        credential = result.scalar_one_or_none()

        if not credential:
            logger.warning("device credentials not found", device_id=device_id_str, clientid=clientid)
            return Response(status_code=401)

        if not credential.is_active:
            logger.warning("device credentials revoked", device_id=device_id_str, clientid=clientid)
            return Response(status_code=401)

        # Authenticate based on credential type
        authenticated = False

        if credential.credential_type == "access_token" and credential.access_token_hash:
            # Verify password against access token hash
            if password and pwd_context.verify(password, credential.access_token_hash):
                authenticated = True
                logger.info("device authenticated via access token", device_id=device_id_str, clientid=clientid)

        elif credential.credential_type == "x509" and credential.certificate_cn:
            # For X.509 auth, password should be empty and username should match CN
            if not password and username == credential.certificate_cn:
                authenticated = True
                logger.info("device authenticated via certificate", device_id=device_id_str, clientid=clientid)

        if not authenticated:
            logger.warning("device authentication failed", device_id=device_id_str, clientid=clientid)
            return Response(status_code=401)

        # Update last_used_at timestamp
        credential.last_used_at = datetime.now(timezone.utc)
        await db.commit()

        return Response(status_code=200)

    except Exception as e:
        logger.error("authentication error", error=str(e), username=username, clientid=clientid)
        return Response(status_code=401)


@router.post("/mqtt/acl")
async def check_acl(
    username: str = Form(...),
    topic: str = Form(...),
    clientid: str = Form(...),
    acc: int = Form(...),  # 1=read, 2=write, 3=read+write
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Check topic access control (mosquitto-go-auth aclcheck endpoint).

    Called by Mosquitto to authorize topic subscriptions and publishes.
    Enforces agency-level isolation.

    Args:
        username: Device username
        topic: MQTT topic (format: "agency/{agency_id}/device/{device_id}/...")
        clientid: MQTT client ID
        acc: Access type (1=read, 2=write, 3=read+write)
        db: Database session

    Returns:
        Response with status code 200 (allow) or 403 (deny)
    """
    try:
        # Internal service account has full access
        if username == "vigilia-backend":
            logger.debug("vigilia-backend granted topic access", topic=topic, acc=acc)
            return Response(status_code=200)

        # Health check account can only read $SYS topics
        if username == "health-check":
            if topic.startswith("$SYS/"):
                logger.debug("health-check granted $SYS topic access", topic=topic)
                return Response(status_code=200)
            else:
                logger.warning("health-check denied non-$SYS topic", topic=topic)
                return Response(status_code=403)

        # Device ACL validation
        # Extract device_id from username
        if not username.startswith("device_"):
            logger.warning("invalid username format for ACL", username=username, topic=topic)
            return Response(status_code=403)

        try:
            device_id_str = username.replace("device_", "")
            import uuid
            device_id = uuid.UUID(device_id_str)
        except (ValueError, AttributeError):
            logger.warning("invalid device_id for ACL", username=username, topic=topic)
            return Response(status_code=403)

        # Query device to get agency_id via building
        result = await db.execute(
            select(IoTDevice, Building)
            .join(Building, IoTDevice.building_id == Building.id)
            .where(IoTDevice.id == device_id)
        )
        row = result.one_or_none()

        if not row:
            logger.warning("device not found for ACL", device_id=device_id_str, topic=topic)
            return Response(status_code=403)

        device, building = row
        agency_id = building.agency_id

        # Expected topic pattern: agency/{agency_id}/device/{device_id}/*
        expected_prefix = f"agency/{agency_id}/device/{device_id}/"

        if not topic.startswith(expected_prefix):
            logger.warning(
                "topic does not match device agency/id",
                device_id=device_id_str,
                agency_id=str(agency_id),
                topic=topic,
                expected_prefix=expected_prefix,
            )
            return Response(status_code=403)

        logger.info(
            "device granted topic access",
            device_id=device_id_str,
            agency_id=str(agency_id),
            topic=topic,
            acc=acc,
        )
        return Response(status_code=200)

    except Exception as e:
        logger.error("ACL check error", error=str(e), username=username, topic=topic)
        return Response(status_code=403)


@router.post("/mqtt/superuser")
async def check_superuser(
    username: str = Form(...),
    clientid: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Check if user is a superuser (mosquitto-go-auth superuser endpoint).

    Called by Mosquitto to check if client has superuser privileges.
    Only vigilia-backend internal service account is superuser.

    Args:
        username: Username to check
        clientid: MQTT client ID
        db: Database session

    Returns:
        Response with status code 200 (is superuser) or 401 (not superuser)
    """
    try:
        if username == "vigilia-backend":
            logger.debug("vigilia-backend confirmed as superuser", clientid=clientid)
            return Response(status_code=200)

        logger.debug("non-superuser check", username=username, clientid=clientid)
        return Response(status_code=401)

    except Exception as e:
        logger.error("superuser check error", error=str(e), username=username, clientid=clientid)
        return Response(status_code=401)

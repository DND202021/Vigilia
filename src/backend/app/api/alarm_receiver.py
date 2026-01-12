"""Alarm Receiver API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user, require_permission, Permission
from app.models.user import User
from app.services.alarm_receiver import (
    AlarmReceiverService,
    AlarmProtocol,
    AlarmAccount,
    AlarmEventType,
)

router = APIRouter()


class AlarmMessageRequest(BaseModel):
    """Request to process an alarm message."""

    message: str = Field(..., min_length=1, description="Raw alarm message")
    protocol: str | None = Field(None, description="Protocol hint (contact_id, sia)")


class AlarmAccountCreate(BaseModel):
    """Create alarm account request."""

    account_code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    address: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    agency_id: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    notes: str | None = None
    active: bool = True


class AlarmAccountResponse(BaseModel):
    """Alarm account response."""

    account_code: str
    name: str
    address: str | None
    latitude: float | None
    longitude: float | None
    agency_id: str | None
    contact_name: str | None
    contact_phone: str | None
    notes: str | None
    active: bool


class ParsedAlarmResponse(BaseModel):
    """Parsed alarm response."""

    protocol: str
    account_code: str
    event_code: str
    event_type: str
    event_description: str
    qualifier: str
    is_alarm: bool
    is_restore: bool
    zone: str | None
    user: str | None
    partition: str | None


class AlarmAlertResponse(BaseModel):
    """Alert created from alarm."""

    id: str
    title: str
    description: str
    severity: str
    status: str
    created_at: datetime


# In-memory account storage (would be DB in production)
_alarm_accounts: dict[str, AlarmAccount] = {}


def _get_event_description(event_type: AlarmEventType) -> str:
    """Get human-readable description for event type."""
    descriptions = {
        AlarmEventType.FIRE_ALARM: "Fire alarm activated",
        AlarmEventType.SMOKE_ALARM: "Smoke detector activated",
        AlarmEventType.HEAT_ALARM: "Heat detector activated",
        AlarmEventType.MEDICAL_ALARM: "Medical emergency alarm",
        AlarmEventType.PANIC_ALARM: "Panic alarm activated",
        AlarmEventType.DURESS: "Duress code entered",
        AlarmEventType.BURGLARY: "Burglary alarm activated",
        AlarmEventType.PERIMETER: "Perimeter sensor triggered",
        AlarmEventType.INTERIOR: "Interior motion detected",
        AlarmEventType.TAMPER: "Device tamper detected",
        AlarmEventType.AC_LOSS: "AC power failure",
        AlarmEventType.LOW_BATTERY: "Low battery condition",
        AlarmEventType.OPENING: "System disarmed",
        AlarmEventType.CLOSING: "System armed",
        AlarmEventType.PERIODIC_TEST: "Automated test signal",
    }
    return descriptions.get(event_type, f"Alarm event {event_type.value}")


@router.post("/receive", response_model=AlarmAlertResponse | None)
async def receive_alarm(
    request_data: AlarmMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AlarmAlertResponse | None:
    """Receive and process an alarm message.

    This endpoint accepts alarm signals in Contact ID or SIA format
    and creates alerts in the system.

    Note: This endpoint may be called by alarm panels directly,
    so authentication is optional but can be configured.
    """
    service = AlarmReceiverService(db)

    # Register known accounts
    for account in _alarm_accounts.values():
        service.register_account(account)

    # Parse protocol
    protocol = None
    if request_data.protocol:
        try:
            protocol = AlarmProtocol(request_data.protocol.lower())
        except ValueError:
            pass

    # Get source IP
    source_ip = request.client.host if request.client else None

    # Process alarm
    alert = await service.process_alarm(
        message=request_data.message,
        protocol=protocol,
        source_ip=source_ip,
    )

    if not alert:
        return None

    return AlarmAlertResponse(
        id=str(alert.id),
        title=alert.title,
        description=alert.description,
        severity=alert.severity.value,
        status=alert.status.value,
        created_at=alert.created_at,
    )


@router.post("/parse", response_model=ParsedAlarmResponse)
async def parse_alarm_message(
    request_data: AlarmMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParsedAlarmResponse:
    """Parse an alarm message without creating an alert.

    Useful for testing and debugging alarm formats.
    """
    service = AlarmReceiverService(db)

    protocol = None
    if request_data.protocol:
        try:
            protocol = AlarmProtocol(request_data.protocol.lower())
        except ValueError:
            pass

    event = service.parse_message(request_data.message, protocol)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not parse alarm message. Supported formats: Contact ID, SIA",
        )

    return ParsedAlarmResponse(
        protocol=event.protocol.value,
        account_code=event.account_code,
        event_code=event.event_code,
        event_type=event.event_type.value,
        event_description=_get_event_description(event.event_type),
        qualifier=event.qualifier,
        is_alarm=event.is_alarm,
        is_restore=event.is_restore,
        zone=event.zone,
        user=event.user,
        partition=event.partition,
    )


@router.post("/accounts", response_model=AlarmAccountResponse)
async def create_alarm_account(
    account: AlarmAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> AlarmAccountResponse:
    """Create or update an alarm account.

    Alarm accounts map account codes from panels to locations,
    contacts, and agencies in the system.
    """
    if account.account_code in _alarm_accounts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account {account.account_code} already exists",
        )

    agency_uuid = None
    if account.agency_id:
        try:
            agency_uuid = uuid.UUID(account.agency_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid agency ID format",
            )

    alarm_account = AlarmAccount(
        account_code=account.account_code,
        name=account.name,
        address=account.address,
        latitude=account.latitude,
        longitude=account.longitude,
        agency_id=agency_uuid,
        contact_name=account.contact_name,
        contact_phone=account.contact_phone,
        notes=account.notes,
        active=account.active,
    )

    _alarm_accounts[account.account_code] = alarm_account

    return AlarmAccountResponse(
        account_code=alarm_account.account_code,
        name=alarm_account.name,
        address=alarm_account.address,
        latitude=alarm_account.latitude,
        longitude=alarm_account.longitude,
        agency_id=str(alarm_account.agency_id) if alarm_account.agency_id else None,
        contact_name=alarm_account.contact_name,
        contact_phone=alarm_account.contact_phone,
        notes=alarm_account.notes,
        active=alarm_account.active,
    )


@router.get("/accounts", response_model=list[AlarmAccountResponse])
async def list_alarm_accounts(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AlarmAccountResponse]:
    """List all alarm accounts."""
    accounts = list(_alarm_accounts.values())

    if active_only:
        accounts = [a for a in accounts if a.active]

    return [
        AlarmAccountResponse(
            account_code=a.account_code,
            name=a.name,
            address=a.address,
            latitude=a.latitude,
            longitude=a.longitude,
            agency_id=str(a.agency_id) if a.agency_id else None,
            contact_name=a.contact_name,
            contact_phone=a.contact_phone,
            notes=a.notes,
            active=a.active,
        )
        for a in accounts
    ]


@router.get("/accounts/{account_code}", response_model=AlarmAccountResponse)
async def get_alarm_account(
    account_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AlarmAccountResponse:
    """Get an alarm account by code."""
    account = _alarm_accounts.get(account_code)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_code} not found",
        )

    return AlarmAccountResponse(
        account_code=account.account_code,
        name=account.name,
        address=account.address,
        latitude=account.latitude,
        longitude=account.longitude,
        agency_id=str(account.agency_id) if account.agency_id else None,
        contact_name=account.contact_name,
        contact_phone=account.contact_phone,
        notes=account.notes,
        active=account.active,
    )


@router.put("/accounts/{account_code}", response_model=AlarmAccountResponse)
async def update_alarm_account(
    account_code: str,
    update: AlarmAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> AlarmAccountResponse:
    """Update an alarm account."""
    if account_code not in _alarm_accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_code} not found",
        )

    agency_uuid = None
    if update.agency_id:
        try:
            agency_uuid = uuid.UUID(update.agency_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid agency ID format",
            )

    alarm_account = AlarmAccount(
        account_code=update.account_code,
        name=update.name,
        address=update.address,
        latitude=update.latitude,
        longitude=update.longitude,
        agency_id=agency_uuid,
        contact_name=update.contact_name,
        contact_phone=update.contact_phone,
        notes=update.notes,
        active=update.active,
    )

    # Handle code change
    if update.account_code != account_code:
        del _alarm_accounts[account_code]

    _alarm_accounts[update.account_code] = alarm_account

    return AlarmAccountResponse(
        account_code=alarm_account.account_code,
        name=alarm_account.name,
        address=alarm_account.address,
        latitude=alarm_account.latitude,
        longitude=alarm_account.longitude,
        agency_id=str(alarm_account.agency_id) if alarm_account.agency_id else None,
        contact_name=alarm_account.contact_name,
        contact_phone=alarm_account.contact_phone,
        notes=alarm_account.notes,
        active=alarm_account.active,
    )


@router.delete("/accounts/{account_code}")
async def delete_alarm_account(
    account_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Delete an alarm account."""
    if account_code not in _alarm_accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_code} not found",
        )

    del _alarm_accounts[account_code]

    return {"message": f"Account {account_code} deleted"}


@router.get("/event-codes")
async def list_event_codes(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """List all known alarm event codes.

    Returns Contact ID event codes with descriptions.
    """
    codes = {}
    for event_type in AlarmEventType:
        if event_type != AlarmEventType.UNKNOWN:
            codes[event_type.value] = {
                "name": event_type.name,
                "description": _get_event_description(event_type),
            }

    return {
        "protocol": "contact_id",
        "event_codes": codes,
    }

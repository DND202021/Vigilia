"""Notification Preferences API endpoints."""

import uuid
from datetime import time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.notification_preference import NotificationPreference

router = APIRouter()


# ==================== Schemas ====================

class NotificationPreferenceResponse(BaseModel):
    """Notification preference response."""
    id: str
    user_id: str
    call_enabled: bool
    sms_enabled: bool
    email_enabled: bool
    push_enabled: bool
    building_ids: list[str]
    min_severity: int
    quiet_start: str | None = None
    quiet_end: str | None = None
    quiet_override_critical: bool


class NotificationPreferenceUpdate(BaseModel):
    """Update notification preferences."""
    call_enabled: bool | None = None
    sms_enabled: bool | None = None
    email_enabled: bool | None = None
    push_enabled: bool | None = None
    building_ids: list[str] | None = None
    min_severity: int | None = None
    quiet_start: str | None = None
    quiet_end: str | None = None
    quiet_override_critical: bool | None = None


# ==================== Helpers ====================

def pref_to_response(pref: NotificationPreference) -> NotificationPreferenceResponse:
    """Convert notification preference model to response."""
    building_ids = pref.building_ids or []
    return NotificationPreferenceResponse(
        id=str(pref.id),
        user_id=str(pref.user_id),
        call_enabled=pref.call_enabled,
        sms_enabled=pref.sms_enabled,
        email_enabled=pref.email_enabled,
        push_enabled=pref.push_enabled,
        building_ids=[str(bid) for bid in building_ids],
        min_severity=pref.min_severity,
        quiet_start=pref.quiet_start.isoformat() if pref.quiet_start else None,
        quiet_end=pref.quiet_end.isoformat() if pref.quiet_end else None,
        quiet_override_critical=pref.quiet_override_critical,
    )


# ==================== Endpoints ====================

@router.get("/users/{user_id}/notification-preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> NotificationPreferenceResponse:
    """Get notification preferences for a user."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_uuid)
    )
    pref = result.scalar_one_or_none()

    if not pref:
        # Create default preferences
        pref = NotificationPreference(
            id=uuid.uuid4(),
            user_id=user_uuid,
        )
        db.add(pref)
        await db.commit()
        await db.refresh(pref)

    return pref_to_response(pref)


@router.put("/users/{user_id}/notification-preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    user_id: str,
    data: NotificationPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> NotificationPreferenceResponse:
    """Update notification preferences for a user."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_uuid)
    )
    pref = result.scalar_one_or_none()

    if not pref:
        pref = NotificationPreference(id=uuid.uuid4(), user_id=user_uuid)
        db.add(pref)

    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key == "quiet_start" and value:
            setattr(pref, key, time.fromisoformat(value))
        elif key == "quiet_end" and value:
            setattr(pref, key, time.fromisoformat(value))
        elif key == "building_ids" and value is not None:
            setattr(pref, key, value)
        elif value is not None:
            setattr(pref, key, value)

    await db.commit()
    await db.refresh(pref)

    return pref_to_response(pref)


@router.get("/buildings/{building_id}/notification-contacts")
async def get_building_notification_contacts(
    building_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict]:
    """List users configured to receive alerts for a specific building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid building ID")

    # Get all notification preferences
    result = await db.execute(select(NotificationPreference))
    all_prefs = list(result.scalars().all())

    contacts = []
    for pref in all_prefs:
        # Include if building_ids is empty (means all buildings) or contains this building
        building_ids = pref.building_ids or []
        if not building_ids or str(building_uuid) in [str(b) for b in building_ids]:
            has_any_channel = pref.call_enabled or pref.sms_enabled or pref.email_enabled or pref.push_enabled
            if has_any_channel:
                contacts.append({
                    "user_id": str(pref.user_id),
                    "call_enabled": pref.call_enabled,
                    "sms_enabled": pref.sms_enabled,
                    "email_enabled": pref.email_enabled,
                    "push_enabled": pref.push_enabled,
                })

    return contacts

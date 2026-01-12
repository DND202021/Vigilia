"""Push Notifications API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.services.push_notifications import (
    PushNotificationService,
    NotificationPayload,
    NotificationType,
)

router = APIRouter()


class SubscriptionRequest(BaseModel):
    """WebPush subscription request."""

    endpoint: str
    keys: dict


class NotificationResponse(BaseModel):
    """Notification response."""

    id: str
    notification_type: str
    title: str
    body: str
    icon: str | None
    url: str | None
    status: str
    created_at: datetime
    sent_at: datetime | None
    delivered_at: datetime | None
    clicked_at: datetime | None


class SendNotificationRequest(BaseModel):
    """Request to send a notification."""

    user_ids: list[str]
    title: str
    body: str
    icon: str | None = None
    url: str | None = None
    notification_type: str = "system"
    require_interaction: bool = False


@router.post("/subscribe")
async def subscribe_push(
    request: SubscriptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Register a push subscription for the current user."""
    service = PushNotificationService(db)

    subscription = await service.register_subscription(
        user=current_user,
        subscription_info={
            "endpoint": request.endpoint,
            "keys": request.keys,
        },
    )

    return {
        "message": "Subscription registered",
        "subscription_id": str(subscription.id),
    }


@router.post("/unsubscribe")
async def unsubscribe_push(
    endpoint: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Unregister a push subscription."""
    service = PushNotificationService(db)

    success = await service.unregister_subscription(
        user=current_user,
        endpoint=endpoint,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    return {"message": "Subscription removed"}


@router.get("", response_model=list[NotificationResponse])
async def get_notifications(
    limit: int = Query(50, ge=1, le=100),
    include_read: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[NotificationResponse]:
    """Get notifications for the current user."""
    service = PushNotificationService(db)

    notifications = await service.get_user_notifications(
        user_id=current_user.id,
        limit=limit,
        include_read=include_read,
    )

    return [
        NotificationResponse(
            id=str(n.id),
            notification_type=n.notification_type,
            title=n.title,
            body=n.body,
            icon=n.icon,
            url=n.url,
            status=n.status,
            created_at=n.created_at,
            sent_at=n.sent_at,
            delivered_at=n.delivered_at,
            clicked_at=n.clicked_at,
        )
        for n in notifications
    ]


@router.post("/{notification_id}/delivered")
async def mark_notification_delivered(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Mark a notification as delivered."""
    try:
        notif_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notification ID",
        )

    service = PushNotificationService(db)
    success = await service.mark_delivered(notif_uuid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return {"message": "Notification marked as delivered"}


@router.post("/{notification_id}/clicked")
async def mark_notification_clicked(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Mark a notification as clicked."""
    try:
        notif_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notification ID",
        )

    service = PushNotificationService(db)
    success = await service.mark_clicked(notif_uuid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return {"message": "Notification marked as clicked"}


@router.post("/send")
async def send_notification(
    request: SendNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Send a notification to specified users (admin only)."""
    # Check permission
    from app.core.deps import Permission, has_permission
    if not has_permission(current_user, Permission.SYSTEM_CONFIG):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    service = PushNotificationService(db)

    # Parse user IDs
    user_ids = []
    for uid in request.user_ids:
        try:
            user_ids.append(uuid.UUID(uid))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user ID: {uid}",
            )

    # Parse notification type
    try:
        notif_type = NotificationType(request.notification_type)
    except ValueError:
        notif_type = NotificationType.SYSTEM

    payload = NotificationPayload(
        title=request.title,
        body=request.body,
        icon=request.icon,
        url=request.url,
        require_interaction=request.require_interaction,
    )

    notifications = await service.send_to_multiple_users(
        user_ids=user_ids,
        payload=payload,
        notification_type=notif_type,
    )

    return {
        "message": f"Sent {len(notifications)} notifications",
        "notification_ids": [str(n.id) for n in notifications],
    }

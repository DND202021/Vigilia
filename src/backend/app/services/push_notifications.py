"""Push Notification Service.

This service handles push notifications via WebPush API and
integrates with the Communication Hub for message delivery.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from sqlalchemy import select, String, Boolean, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.user import User

logger = structlog.get_logger()


class NotificationStatus(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CLICKED = "clicked"


class NotificationType(str, Enum):
    """Type of notification."""

    ALERT = "alert"
    INCIDENT = "incident"
    ASSIGNMENT = "assignment"
    MESSAGE = "message"
    SYSTEM = "system"


class PushSubscription(Base, TimestampMixin):
    """User push subscription for WebPush."""

    __tablename__ = "push_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh_key: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_key: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Notification(Base, TimestampMixin):
    """Notification record for tracking delivery."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=NotificationStatus.PENDING.value,
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


@dataclass
class NotificationPayload:
    """Push notification payload."""

    title: str
    body: str
    icon: str | None = None
    badge: str | None = None
    url: str | None = None
    tag: str | None = None
    data: dict | None = None
    actions: list[dict] | None = None
    require_interaction: bool = False
    silent: bool = False


class PushNotificationService:
    """Service for managing push notifications."""

    def __init__(self, db: AsyncSession):
        """Initialize push notification service."""
        self.db = db

    async def register_subscription(
        self,
        user: User,
        subscription_info: dict,
        user_agent: str | None = None,
    ) -> PushSubscription:
        """Register a push subscription for a user.

        Args:
            user: The user to register subscription for
            subscription_info: WebPush subscription object
            user_agent: Browser user agent

        Returns:
            The created subscription
        """
        endpoint = subscription_info.get("endpoint")
        keys = subscription_info.get("keys", {})

        if not endpoint:
            raise ValueError("Subscription endpoint is required")

        # Check for existing subscription with same endpoint
        existing = await self.db.execute(
            select(PushSubscription).where(
                PushSubscription.endpoint == endpoint,
                PushSubscription.is_active == True,
            )
        )
        existing_sub = existing.scalar_one_or_none()

        if existing_sub:
            # Update existing subscription
            existing_sub.p256dh_key = keys.get("p256dh", "")
            existing_sub.auth_key = keys.get("auth", "")
            existing_sub.user_agent = user_agent
            existing_sub.user_id = user.id
            await self.db.commit()
            return existing_sub

        # Create new subscription
        subscription = PushSubscription(
            user_id=user.id,
            endpoint=endpoint,
            p256dh_key=keys.get("p256dh", ""),
            auth_key=keys.get("auth", ""),
            user_agent=user_agent,
            is_active=True,
        )

        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)

        logger.info(
            "Registered push subscription",
            user_id=str(user.id),
            subscription_id=str(subscription.id),
        )

        return subscription

    async def unregister_subscription(
        self,
        user: User,
        endpoint: str,
    ) -> bool:
        """Unregister a push subscription.

        Args:
            user: The user to unregister subscription for
            endpoint: The subscription endpoint

        Returns:
            True if subscription was found and deactivated
        """
        result = await self.db.execute(
            select(PushSubscription).where(
                PushSubscription.user_id == user.id,
                PushSubscription.endpoint == endpoint,
                PushSubscription.is_active == True,
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.is_active = False
            await self.db.commit()
            return True

        return False

    async def get_user_subscriptions(self, user_id: uuid.UUID) -> list[PushSubscription]:
        """Get all active subscriptions for a user."""
        result = await self.db.execute(
            select(PushSubscription).where(
                PushSubscription.user_id == user_id,
                PushSubscription.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def send_notification(
        self,
        user_id: uuid.UUID,
        payload: NotificationPayload,
        notification_type: NotificationType = NotificationType.SYSTEM,
    ) -> Notification:
        """Send a push notification to a user.

        Args:
            user_id: The user to send notification to
            payload: The notification payload
            notification_type: Type of notification

        Returns:
            The notification record
        """
        # Create notification record
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type.value,
            title=payload.title,
            body=payload.body,
            icon=payload.icon,
            url=payload.url,
            data=payload.data,
            status=NotificationStatus.PENDING.value,
        )

        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        # Get user's subscriptions
        subscriptions = await self.get_user_subscriptions(user_id)

        if not subscriptions:
            notification.status = NotificationStatus.FAILED.value
            notification.error_message = "No active subscriptions"
            await self.db.commit()
            return notification

        # Build WebPush payload
        webpush_payload = {
            "title": payload.title,
            "body": payload.body,
            "icon": payload.icon or "/icon-192.png",
            "badge": payload.badge or "/badge-72.png",
            "tag": payload.tag or str(notification.id),
            "data": {
                "url": payload.url,
                "notification_id": str(notification.id),
                **(payload.data or {}),
            },
            "requireInteraction": payload.require_interaction,
            "silent": payload.silent,
        }

        if payload.actions:
            webpush_payload["actions"] = payload.actions

        # Send to each subscription
        # Note: In production, use pywebpush library for actual delivery
        success_count = 0
        for sub in subscriptions:
            try:
                # Placeholder for actual WebPush send
                # In production:
                # from pywebpush import webpush, WebPushException
                # webpush(
                #     subscription_info={
                #         "endpoint": sub.endpoint,
                #         "keys": {"p256dh": sub.p256dh_key, "auth": sub.auth_key}
                #     },
                #     data=json.dumps(webpush_payload),
                #     vapid_private_key=settings.vapid_private_key,
                #     vapid_claims={"sub": f"mailto:{settings.vapid_email}"}
                # )
                success_count += 1
                logger.debug(
                    "Would send push notification",
                    subscription_id=str(sub.id),
                    endpoint=sub.endpoint[:50],
                )
            except Exception as e:
                logger.error(
                    "Failed to send push notification",
                    subscription_id=str(sub.id),
                    error=str(e),
                )

        # Update notification status
        notification.status = NotificationStatus.SENT.value
        notification.sent_at = datetime.now(timezone.utc)
        await self.db.commit()

        logger.info(
            "Sent push notification",
            notification_id=str(notification.id),
            user_id=str(user_id),
            subscriptions_count=len(subscriptions),
            success_count=success_count,
        )

        return notification

    async def send_to_multiple_users(
        self,
        user_ids: list[uuid.UUID],
        payload: NotificationPayload,
        notification_type: NotificationType = NotificationType.SYSTEM,
    ) -> list[Notification]:
        """Send a notification to multiple users."""
        notifications = []
        for user_id in user_ids:
            notification = await self.send_notification(
                user_id=user_id,
                payload=payload,
                notification_type=notification_type,
            )
            notifications.append(notification)
        return notifications

    async def mark_delivered(self, notification_id: uuid.UUID) -> bool:
        """Mark a notification as delivered."""
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalar_one_or_none()

        if notification:
            notification.status = NotificationStatus.DELIVERED.value
            notification.delivered_at = datetime.now(timezone.utc)
            await self.db.commit()
            return True

        return False

    async def mark_clicked(self, notification_id: uuid.UUID) -> bool:
        """Mark a notification as clicked."""
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalar_one_or_none()

        if notification:
            notification.status = NotificationStatus.CLICKED.value
            notification.clicked_at = datetime.now(timezone.utc)
            await self.db.commit()
            return True

        return False

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        include_read: bool = True,
    ) -> list[Notification]:
        """Get notifications for a user."""
        query = select(Notification).where(Notification.user_id == user_id)

        if not include_read:
            query = query.where(
                Notification.status.in_([
                    NotificationStatus.PENDING.value,
                    NotificationStatus.SENT.value,
                    NotificationStatus.DELIVERED.value,
                ])
            )

        query = query.order_by(Notification.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

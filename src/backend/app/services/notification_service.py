"""Notification delivery service for alert-triggered notifications.

Supports multiple channels: email, SMS, phone call, and push notifications.
Integrates with the alert pipeline to send notifications based on user preferences.
"""

import logging
from datetime import datetime, timezone, time as dt_time
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.alert import Alert, AlertSeverity
from app.models.notification_preference import NotificationPreference
from app.models.user import User

logger = logging.getLogger(__name__)

# Severity to numeric level mapping (lower = more severe)
SEVERITY_LEVELS = {
    AlertSeverity.CRITICAL: 1,
    AlertSeverity.HIGH: 2,
    AlertSeverity.MEDIUM: 3,
    AlertSeverity.LOW: 4,
    AlertSeverity.INFO: 5,
}


class NotificationDeliveryResult:
    """Result of a notification delivery attempt."""

    def __init__(
        self,
        user_id: UUID,
        channel: str,
        success: bool,
        message: str = "",
        external_id: str | None = None,
    ):
        self.user_id = user_id
        self.channel = channel
        self.success = success
        self.message = message
        self.external_id = external_id
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": str(self.user_id),
            "channel": self.channel,
            "success": self.success,
            "message": self.message,
            "external_id": self.external_id,
            "timestamp": self.timestamp.isoformat(),
        }


class NotificationService:
    """
    Multi-channel notification delivery service.

    Determines which users should receive notifications for a given alert
    based on their preferences (channels, building scope, severity filter,
    quiet hours) and delivers via configured channels.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self._delivery_log: list[dict[str, Any]] = []
        self._stats = {
            "notifications_sent": 0,
            "notifications_failed": 0,
            "users_notified": 0,
        }

    async def notify_for_alert(self, alert: Alert) -> list[NotificationDeliveryResult]:
        """
        Send notifications for a new alert to all eligible users.

        1. Find users with notification preferences matching this alert
        2. Filter by building scope, severity, and quiet hours
        3. Deliver via each user's enabled channels
        """
        results: list[NotificationDeliveryResult] = []

        alert_severity_level = SEVERITY_LEVELS.get(alert.severity, 5)

        async with self.session_factory() as db:
            # Get all notification preferences
            prefs_result = await db.execute(
                select(NotificationPreference, User).join(
                    User, NotificationPreference.user_id == User.id
                ).where(User.is_active.is_(True))
            )
            rows = prefs_result.all()

            for pref, user in rows:
                # Check severity filter
                if alert_severity_level > pref.min_severity:
                    continue

                # Check building scope
                if pref.building_ids and alert.building_id:
                    if str(alert.building_id) not in [str(bid) for bid in pref.building_ids]:
                        continue

                # Check quiet hours
                if self._is_quiet_hours(pref):
                    # During quiet hours, only deliver if critical override
                    is_critical = alert.severity == AlertSeverity.CRITICAL
                    if not (is_critical and pref.quiet_override_critical):
                        continue

                # Deliver via each enabled channel
                user_results = await self._deliver_to_user(
                    user=user,
                    pref=pref,
                    alert=alert,
                )
                results.extend(user_results)

                if any(r.success for r in user_results):
                    self._stats["users_notified"] += 1

        # Log all delivery attempts
        for result in results:
            self._delivery_log.append(result.to_dict())
            if result.success:
                self._stats["notifications_sent"] += 1
            else:
                self._stats["notifications_failed"] += 1

        return results

    async def _deliver_to_user(
        self,
        user: User,
        pref: NotificationPreference,
        alert: Alert,
    ) -> list[NotificationDeliveryResult]:
        """Deliver alert notification to a single user via their enabled channels."""
        results = []

        if pref.email_enabled and user.email:
            result = await self._send_email(user, alert)
            results.append(result)

        if pref.sms_enabled and hasattr(user, 'phone') and user.phone:
            result = await self._send_sms(user, alert)
            results.append(result)

        if pref.call_enabled and hasattr(user, 'phone') and user.phone:
            result = await self._send_call(user, alert)
            results.append(result)

        if pref.push_enabled:
            result = await self._send_push(user, alert)
            results.append(result)

        return results

    async def _send_email(self, user: User, alert: Alert) -> NotificationDeliveryResult:
        """Send email notification. Placeholder for SMTP/SendGrid integration."""
        try:
            # TODO: Integrate with SMTP or SendGrid
            # For now, log the attempt
            logger.info(
                f"Email notification: {alert.title} -> {user.email}",
                extra={
                    "user_id": str(user.id),
                    "alert_id": str(alert.id),
                    "channel": "email",
                },
            )
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="email",
                success=True,
                message=f"Email queued to {user.email}",
            )
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="email",
                success=False,
                message=str(e),
            )

    async def _send_sms(self, user: User, alert: Alert) -> NotificationDeliveryResult:
        """Send SMS notification. Placeholder for Twilio integration."""
        try:
            phone = getattr(user, 'phone', None)
            # TODO: Integrate with Twilio SMS
            logger.info(
                f"SMS notification: {alert.title} -> {phone}",
                extra={
                    "user_id": str(user.id),
                    "alert_id": str(alert.id),
                    "channel": "sms",
                },
            )
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="sms",
                success=True,
                message=f"SMS queued to {phone}",
            )
        except Exception as e:
            logger.error(f"SMS notification failed: {e}")
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="sms",
                success=False,
                message=str(e),
            )

    async def _send_call(self, user: User, alert: Alert) -> NotificationDeliveryResult:
        """Send voice call notification. Placeholder for Twilio Voice integration."""
        try:
            phone = getattr(user, 'phone', None)
            # TODO: Integrate with Twilio Voice
            logger.info(
                f"Call notification: {alert.title} -> {phone}",
                extra={
                    "user_id": str(user.id),
                    "alert_id": str(alert.id),
                    "channel": "call",
                },
            )
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="call",
                success=True,
                message=f"Call queued to {phone}",
            )
        except Exception as e:
            logger.error(f"Call notification failed: {e}")
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="call",
                success=False,
                message=str(e),
            )

    async def _send_push(self, user: User, alert: Alert) -> NotificationDeliveryResult:
        """Send push notification. Placeholder for WebPush/FCM integration."""
        try:
            # TODO: Integrate with WebPush or Firebase Cloud Messaging
            logger.info(
                f"Push notification: {alert.title} -> user {user.id}",
                extra={
                    "user_id": str(user.id),
                    "alert_id": str(alert.id),
                    "channel": "push",
                },
            )
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="push",
                success=True,
                message="Push notification queued",
            )
        except Exception as e:
            logger.error(f"Push notification failed: {e}")
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="push",
                success=False,
                message=str(e),
            )

    def _is_quiet_hours(self, pref: NotificationPreference) -> bool:
        """Check if current time is within user's quiet hours."""
        if not pref.quiet_start or not pref.quiet_end:
            return False

        now = datetime.now(timezone.utc).time()
        start = pref.quiet_start
        end = pref.quiet_end

        if start <= end:
            # Normal range (e.g., 22:00 to 06:00 NOT crossing midnight)
            return start <= now <= end
        else:
            # Crosses midnight (e.g., 22:00 to 06:00)
            return now >= start or now <= end

    def get_delivery_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent notification delivery log entries."""
        return self._delivery_log[-limit:]

    def get_stats(self) -> dict[str, int]:
        """Get notification service statistics."""
        return self._stats.copy()

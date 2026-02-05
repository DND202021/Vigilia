"""Notification delivery service for alert-triggered notifications.

Supports multiple channels: email, SMS, phone call, and push notifications.
Integrates with the alert pipeline to send notifications based on user preferences.
"""

import structlog
from datetime import datetime, timezone, time as dt_time
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.alert import Alert, AlertSeverity
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.models.notification_delivery import NotificationDelivery, DeliveryStatus, DeliveryChannel
from app.services.delivery.email_delivery import EmailDeliveryService
from app.services.delivery.sms_delivery import SMSDeliveryService
from app.services.delivery.push_delivery import PushDeliveryService
from app.services.delivery.retry_manager import NotificationRetryManager
from app.services.push_notifications import PushSubscription

logger = structlog.get_logger()

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

        # Initialize delivery services (graceful if not configured)
        self.email_service = EmailDeliveryService()
        self.sms_service = SMSDeliveryService()
        self.push_service = PushDeliveryService()
        self.retry_manager = NotificationRetryManager()

    async def _create_delivery_record(
        self,
        db: AsyncSession,
        alert_id: UUID,
        user_id: UUID,
        channel: str,
        status: str,
        external_id: str | None = None,
        error_message: str | None = None,
        attempts: int = 1,
    ) -> NotificationDelivery:
        """Create a NotificationDelivery record in the database.

        Args:
            db: Database session
            alert_id: Alert ID
            user_id: User ID
            channel: Delivery channel (email, sms, push, call)
            status: Delivery status (sent, failed, etc.)
            external_id: External service ID (SendGrid message ID, Twilio SID, etc.)
            error_message: Error message if delivery failed
            attempts: Number of delivery attempts

        Returns:
            Created NotificationDelivery record
        """
        delivery = NotificationDelivery(
            alert_id=alert_id,
            user_id=user_id,
            channel=channel,
            status=status,
            external_id=external_id,
            error_message=error_message,
            attempts=attempts,
            sent_at=datetime.now(timezone.utc) if status == DeliveryStatus.SENT.value else None,
            failed_at=datetime.now(timezone.utc) if status == DeliveryStatus.FAILED.value else None,
            last_attempt_at=datetime.now(timezone.utc),
        )
        db.add(delivery)
        await db.flush()
        return delivery

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
                    db=db,
                    user=user,
                    pref=pref,
                    alert=alert,
                )
                results.extend(user_results)

                if any(r.success for r in user_results):
                    self._stats["users_notified"] += 1

            # Commit all NotificationDelivery records
            await db.commit()

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
        db: AsyncSession,
        user: User,
        pref: NotificationPreference,
        alert: Alert,
    ) -> list[NotificationDeliveryResult]:
        """Deliver alert notification to a single user via their enabled channels."""
        results = []

        if pref.email_enabled and user.email:
            result = await self._send_email(db, user, alert)
            results.append(result)

        if pref.sms_enabled and hasattr(user, 'phone') and user.phone:
            result = await self._send_sms(db, user, alert)
            results.append(result)

        if pref.call_enabled and hasattr(user, 'phone') and user.phone:
            result = await self._send_call(user, alert)
            results.append(result)

        if pref.push_enabled:
            result = await self._send_push(db, user, alert)
            results.append(result)

        return results

    async def _send_email(
        self, db: AsyncSession, user: User, alert: Alert
    ) -> NotificationDeliveryResult:
        """Send email notification via SendGrid."""
        if self.email_service.client is None:
            logger.debug(
                "Email not configured, skipping",
                user_id=str(user.id),
                alert_id=str(alert.id),
            )
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="email",
                success=False,
                message="Email not configured",
            )

        try:
            # Execute with retry logic
            success, message, external_id = await self.retry_manager.execute_with_retry(
                self.email_service.send_alert_email,
                user.email,
                alert.title,
                alert.description or "",
                alert.severity.value,
            )

            # Create delivery record
            status = DeliveryStatus.SENT.value if success else DeliveryStatus.FAILED.value
            await self._create_delivery_record(
                db=db,
                alert_id=alert.id,
                user_id=user.id,
                channel=DeliveryChannel.EMAIL.value,
                status=status,
                external_id=external_id,
                error_message=None if success else message,
                attempts=1,  # Retry manager handles attempt count internally
            )

            return NotificationDeliveryResult(
                user_id=user.id,
                channel="email",
                success=success,
                message=message,
                external_id=external_id,
            )

        except Exception as e:
            # All retries exhausted
            logger.error(
                "Email delivery failed after retries",
                user_id=str(user.id),
                alert_id=str(alert.id),
                error=str(e),
            )

            await self._create_delivery_record(
                db=db,
                alert_id=alert.id,
                user_id=user.id,
                channel=DeliveryChannel.EMAIL.value,
                status=DeliveryStatus.FAILED.value,
                error_message=str(e),
                attempts=self.retry_manager.MAX_TRIES,
            )

            return NotificationDeliveryResult(
                user_id=user.id,
                channel="email",
                success=False,
                message=str(e),
            )

    async def _send_sms(
        self, db: AsyncSession, user: User, alert: Alert
    ) -> NotificationDeliveryResult:
        """Send SMS notification via Twilio."""
        phone = getattr(user, "phone", None)

        if self.sms_service.client is None:
            logger.debug(
                "SMS not configured, skipping",
                user_id=str(user.id),
                alert_id=str(alert.id),
            )
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="sms",
                success=False,
                message="SMS not configured",
            )

        if not phone:
            logger.debug(
                "User has no phone number, skipping SMS",
                user_id=str(user.id),
                alert_id=str(alert.id),
            )
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="sms",
                success=False,
                message="No phone number",
            )

        try:
            # Execute with retry logic
            success, message, external_id = await self.retry_manager.execute_with_retry(
                self.sms_service.send_alert_sms,
                phone,
                alert.title,
                alert.severity.value,
            )

            # Create delivery record
            status = DeliveryStatus.SENT.value if success else DeliveryStatus.FAILED.value
            await self._create_delivery_record(
                db=db,
                alert_id=alert.id,
                user_id=user.id,
                channel=DeliveryChannel.SMS.value,
                status=status,
                external_id=external_id,
                error_message=None if success else message,
                attempts=1,
            )

            return NotificationDeliveryResult(
                user_id=user.id,
                channel="sms",
                success=success,
                message=message,
                external_id=external_id,
            )

        except Exception as e:
            # All retries exhausted
            logger.error(
                "SMS delivery failed after retries",
                user_id=str(user.id),
                alert_id=str(alert.id),
                error=str(e),
            )

            await self._create_delivery_record(
                db=db,
                alert_id=alert.id,
                user_id=user.id,
                channel=DeliveryChannel.SMS.value,
                status=DeliveryStatus.FAILED.value,
                error_message=str(e),
                attempts=self.retry_manager.MAX_TRIES,
            )

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

    async def _send_push(
        self, db: AsyncSession, user: User, alert: Alert
    ) -> NotificationDeliveryResult:
        """Send push notification via WebPush."""
        if not self.push_service.enabled:
            logger.debug(
                "WebPush not configured, skipping",
                user_id=str(user.id),
                alert_id=str(alert.id),
            )
            return NotificationDeliveryResult(
                user_id=user.id,
                channel="push",
                success=False,
                message="WebPush not configured",
            )

        try:
            # Query active push subscriptions for user
            result = await db.execute(
                select(PushSubscription).where(
                    PushSubscription.user_id == user.id,
                    PushSubscription.is_active == True,
                )
            )
            subscriptions = list(result.scalars().all())

            if not subscriptions:
                logger.debug(
                    "User has no active push subscriptions",
                    user_id=str(user.id),
                    alert_id=str(alert.id),
                )
                return NotificationDeliveryResult(
                    user_id=user.id,
                    channel="push",
                    success=False,
                    message="No active subscriptions",
                )

            # Send to each subscription
            success_count = 0
            failed_count = 0
            last_error = None

            for subscription in subscriptions:
                subscription_info = {
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh_key,
                        "auth": subscription.auth_key,
                    },
                }

                try:
                    # Execute with retry logic
                    success, message, _ = await self.retry_manager.execute_with_retry(
                        self.push_service.send_alert_push,
                        subscription_info,
                        alert.title,
                        alert.description or "",
                        alert.severity.value,
                        str(alert.id),
                        None,  # url
                    )

                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        last_error = message

                        # Handle expired subscription
                        if message == "subscription_expired":
                            subscription.is_active = False
                            logger.info(
                                "Deactivated expired push subscription",
                                subscription_id=str(subscription.id),
                                user_id=str(user.id),
                            )

                except Exception as e:
                    failed_count += 1
                    last_error = str(e)
                    logger.error(
                        "Push delivery failed",
                        subscription_id=str(subscription.id),
                        error=str(e),
                    )

            # Create delivery record for overall push attempt
            overall_success = success_count > 0
            status = DeliveryStatus.SENT.value if overall_success else DeliveryStatus.FAILED.value
            error_msg = None if overall_success else last_error

            await self._create_delivery_record(
                db=db,
                alert_id=alert.id,
                user_id=user.id,
                channel=DeliveryChannel.PUSH.value,
                status=status,
                error_message=error_msg,
                attempts=1,
            )

            return NotificationDeliveryResult(
                user_id=user.id,
                channel="push",
                success=overall_success,
                message=f"Sent to {success_count}/{len(subscriptions)} subscriptions",
            )

        except Exception as e:
            # All retries exhausted or other error
            logger.error(
                "Push notification failed",
                user_id=str(user.id),
                alert_id=str(alert.id),
                error=str(e),
            )

            await self._create_delivery_record(
                db=db,
                alert_id=alert.id,
                user_id=user.id,
                channel=DeliveryChannel.PUSH.value,
                status=DeliveryStatus.FAILED.value,
                error_message=str(e),
                attempts=self.retry_manager.MAX_TRIES,
            )

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

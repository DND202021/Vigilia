"""Push notification delivery service using pywebpush."""

import asyncio
import json

import structlog
from pywebpush import webpush, WebPushException

from app.core.config import settings

logger = structlog.get_logger()


class PushDeliveryService:
    """Sends push notifications via WebPush API with VAPID authentication."""

    def __init__(self):
        """Initialize WebPush service if VAPID keys are configured."""
        if settings.vapid_private_key:
            self.enabled = True
            self.private_key = settings.vapid_private_key
            self.public_key = settings.vapid_public_key
            self.mailto = settings.vapid_mailto
            logger.info("WebPush service initialized", mailto=self.mailto)
        else:
            self.enabled = False
            logger.warning("VAPID keys not configured - push notifications disabled")

    async def send_alert_push(
        self,
        subscription_info: dict,
        alert_title: str,
        alert_body: str,
        severity: str,
        alert_id: str,
        url: str | None = None,
    ) -> tuple[bool, str, str | None]:
        """Send alert push notification via WebPush.

        Args:
            subscription_info: WebPush subscription with endpoint, keys.p256dh, keys.auth
            alert_title: Alert title
            alert_body: Alert description/body
            severity: Alert severity level
            alert_id: Alert ID for notification tag
            url: Optional URL to open when notification is clicked

        Returns:
            Tuple of (success, message, external_id)
            - success: True if push was accepted
            - message: Status message or "subscription_expired" for 410 errors
            - external_id: None (WebPush doesn't return external IDs)
        """
        if not self.enabled:
            logger.debug("WebPush not configured, skipping push")
            return (False, "WebPush not configured", None)

        try:
            # Build push notification payload
            payload = {
                "title": alert_title,
                "body": alert_body,
                "icon": "/icon-192.png",
                "badge": "/badge-72.png",
                "tag": alert_id,  # Prevents duplicate notifications for same alert
                "data": {
                    "url": url,
                    "alert_id": alert_id,
                    "severity": severity,
                },
            }

            # Send via pywebpush (synchronous, wrap in thread)
            await asyncio.to_thread(
                webpush,
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=self.private_key,
                vapid_claims={"sub": self.mailto},
                content_encoding="aes128gcm",  # RFC 8188 standard
            )

            logger.info(
                "Push notification sent successfully",
                alert_id=alert_id,
                severity=severity,
                endpoint=subscription_info.get("endpoint", "")[:50],
            )

            return (True, "Push sent", None)

        except WebPushException as e:
            error_str = str(e)

            # Check for 410 Gone (subscription expired)
            if "410" in error_str or "Gone" in error_str:
                logger.info(
                    "Push subscription expired",
                    alert_id=alert_id,
                    endpoint=subscription_info.get("endpoint", "")[:50],
                )
                return (False, "subscription_expired", None)

            logger.error(
                "Push notification failed",
                alert_id=alert_id,
                severity=severity,
                error=error_str,
            )
            return (False, error_str, None)

        except Exception as e:
            logger.error(
                "Push notification failed",
                alert_id=alert_id,
                severity=severity,
                error=str(e),
            )
            return (False, str(e), None)

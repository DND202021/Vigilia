"""SMS delivery service using Twilio API."""

import re

import structlog
from twilio.rest import Client
from twilio.http.async_http_client import AsyncTwilioHttpClient

from app.core.config import settings

logger = structlog.get_logger()


class SMSDeliveryService:
    """Sends alert SMS via Twilio API."""

    def __init__(self):
        """Initialize Twilio client if credentials are configured."""
        if (
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_from_number
        ):
            # Use async HTTP client for non-blocking operation
            http_client = AsyncTwilioHttpClient()
            self.client = Client(
                settings.twilio_account_sid,
                settings.twilio_auth_token,
                http_client=http_client,
            )
            self.from_number = settings.twilio_from_number
            logger.info("Twilio client initialized", from_number=self.from_number)
        else:
            self.client = None
            logger.warning("Twilio not configured - SMS delivery disabled")

    async def send_alert_sms(
        self,
        to_phone: str,
        alert_title: str,
        severity: str,
    ) -> tuple[bool, str, str | None]:
        """Send alert notification via SMS.

        Args:
            to_phone: Recipient phone number (will be normalized to E.164)
            alert_title: Alert title
            severity: Alert severity level

        Returns:
            Tuple of (success, message, external_id)
            - success: True if SMS was accepted
            - message: Status message
            - external_id: Twilio message SID
        """
        if self.client is None:
            logger.debug("Twilio not configured, skipping SMS", to_phone=to_phone)
            return (False, "Twilio not configured", None)

        try:
            # Normalize phone number to E.164 format
            normalized_phone = self._normalize_phone(to_phone)

            # Build SMS body (keep under 160 chars for single segment)
            sms_body = f"[{severity.upper()}] {alert_title}"
            if len(sms_body) > 160:
                # Truncate title to fit in 160 chars with severity prefix
                max_title_len = 160 - len(f"[{severity.upper()}] ") - 3  # -3 for "..."
                sms_body = f"[{severity.upper()}] {alert_title[:max_title_len]}..."

            # Send SMS via Twilio async client
            message = await self.client.messages.create_async(
                body=sms_body,
                from_=self.from_number,
                to=normalized_phone,
            )

            logger.info(
                "SMS sent successfully",
                to_phone=normalized_phone,
                severity=severity,
                message_sid=message.sid,
                status=message.status,
            )

            return (True, f"SMS sent: {message.status}", message.sid)

        except Exception as e:
            logger.error(
                "SMS delivery failed",
                to_phone=to_phone,
                severity=severity,
                error=str(e),
            )
            return (False, str(e), None)

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format.

        Removes spaces, dashes, parentheses. If doesn't start with '+',
        assumes US number and prepends '+1'.

        Args:
            phone: Phone number in various formats

        Returns:
            E.164 formatted phone number (e.g., +15551234567)
        """
        # Remove common formatting characters
        cleaned = re.sub(r"[\s\-\(\)]", "", phone)

        # Add +1 for US numbers if no country code present
        if not cleaned.startswith("+"):
            cleaned = f"+1{cleaned}"

        return cleaned

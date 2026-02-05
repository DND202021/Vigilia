"""Email delivery service using SendGrid API."""

import asyncio
from datetime import datetime, timezone

import structlog
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.core.config import settings

logger = structlog.get_logger()


class EmailDeliveryService:
    """Sends alert emails via SendGrid API."""

    def __init__(self):
        """Initialize SendGrid client if credentials are configured."""
        if settings.sendgrid_api_key:
            self.client = SendGridAPIClient(settings.sendgrid_api_key)
            self.from_email = settings.sendgrid_from_email
            logger.info("SendGrid client initialized", from_email=self.from_email)
        else:
            self.client = None
            logger.warning("SendGrid not configured - email delivery disabled")

    async def send_alert_email(
        self,
        to_email: str,
        alert_title: str,
        alert_description: str,
        severity: str,
    ) -> tuple[bool, str, str | None]:
        """Send alert notification via email.

        Args:
            to_email: Recipient email address
            alert_title: Alert title
            alert_description: Alert description/details
            severity: Alert severity level

        Returns:
            Tuple of (success, message, external_id)
            - success: True if email was accepted
            - message: Status message
            - external_id: SendGrid message ID (X-Message-Id header)
        """
        if self.client is None:
            logger.debug("SendGrid not configured, skipping email", to_email=to_email)
            return (False, "SendGrid not configured", None)

        try:
            # Build HTML email content
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            severity_color = self._get_severity_color(severity)

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: {severity_color}; color: white; padding: 15px; border-radius: 5px 5px 0 0; }}
                    .severity-badge {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; }}
                    .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; }}
                    .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2 style="margin: 0;">
                            <span class="severity-badge">[{severity.upper()}]</span>
                            {alert_title}
                        </h2>
                    </div>
                    <div class="content">
                        <p><strong>Description:</strong></p>
                        <p>{alert_description or 'No additional details provided.'}</p>
                        <p><strong>Time:</strong> {timestamp}</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated alert from ERIOP Emergency Response Platform.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Create SendGrid message
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=f"[{severity.upper()}] {alert_title}",
                html_content=html_content,
            )

            # Send via SendGrid (synchronous API, wrap in thread)
            response = await asyncio.to_thread(self.client.send, message)

            # Extract message ID from response headers
            message_id = None
            if hasattr(response, "headers") and "X-Message-Id" in response.headers:
                message_id = response.headers["X-Message-Id"]

            logger.info(
                "Email sent successfully",
                to_email=to_email,
                severity=severity,
                message_id=message_id,
                status_code=response.status_code,
            )

            return (True, "Email accepted", message_id)

        except Exception as e:
            logger.error(
                "Email delivery failed",
                to_email=to_email,
                severity=severity,
                error=str(e),
            )
            return (False, str(e), None)

    def _get_severity_color(self, severity: str) -> str:
        """Get color code for severity level."""
        severity_colors = {
            "critical": "#dc3545",  # Red
            "high": "#fd7e14",      # Orange
            "medium": "#ffc107",    # Yellow
            "low": "#28a745",       # Green
            "info": "#17a2b8",      # Cyan
        }
        return severity_colors.get(severity.lower(), "#6c757d")  # Default gray

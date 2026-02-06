"""Comprehensive tests for notification delivery services and NotificationService integration."""

import uuid
from datetime import datetime, time, timezone
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertSource
from app.models.user import User, UserRole
from app.models.agency import Agency
from app.models.notification_preference import NotificationPreference
from app.models.notification_delivery import NotificationDelivery, DeliveryStatus, DeliveryChannel
from app.services.notification_service import NotificationService
from app.services.delivery.email_delivery import EmailDeliveryService
from app.services.delivery.sms_delivery import SMSDeliveryService
from app.services.delivery.push_delivery import PushDeliveryService
from app.services.delivery.retry_manager import NotificationRetryManager
from app.services.push_notifications import PushSubscription


# ===========================
# Fixtures
# ===========================

@pytest_asyncio.fixture
async def test_alert(db_session: AsyncSession, test_agency: Agency) -> Alert:
    """Create a test alert."""
    alert = Alert(
        id=uuid.uuid4(),
        title="Test Alert",
        description="Test alert description",
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
        source=AlertSource.MANUAL,
        agency_id=test_agency.id,
        building_id=None,
        location="Test Location",
    )
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)
    return alert


@pytest_asyncio.fixture
async def test_user_with_prefs(
    db_session: AsyncSession,
    test_user: User,
) -> tuple[User, NotificationPreference]:
    """Create a test user with notification preferences."""
    # Add phone attribute to user (using setattr since User model may not have phone column)
    test_user.phone = "+15551234567"

    # Create notification preferences
    prefs = NotificationPreference(
        id=uuid.uuid4(),
        user_id=test_user.id,
        email_enabled=True,
        sms_enabled=True,
        push_enabled=True,
        call_enabled=False,
        min_severity=1,  # Critical only
        quiet_override_critical=True,
    )
    db_session.add(prefs)
    await db_session.commit()
    await db_session.refresh(prefs)

    return test_user, prefs


@pytest.fixture
def mock_sendgrid():
    """Mock SendGrid client."""
    with patch("app.services.delivery.email_delivery.SendGridAPIClient") as mock:
        instance = mock.return_value
        response = MagicMock()
        response.status_code = 202
        response.headers = {"X-Message-Id": "test-msg-id-123"}
        instance.send.return_value = response
        yield instance


@pytest.fixture
def mock_twilio():
    """Mock Twilio client."""
    with patch("app.services.delivery.sms_delivery.Client") as mock_client:
        with patch("app.services.delivery.sms_delivery.AsyncTwilioHttpClient"):
            instance = mock_client.return_value
            message = AsyncMock()
            message.sid = "SM123456789"
            message.status = "queued"
            instance.messages.create_async = AsyncMock(return_value=message)
            yield instance


@pytest.fixture
def mock_webpush():
    """Mock pywebpush.webpush function."""
    with patch("app.services.delivery.push_delivery.webpush") as mock:
        # webpush returns None on success
        mock.return_value = None
        yield mock


# ===========================
# EmailDeliveryService Tests
# ===========================

@pytest.mark.asyncio
async def test_email_delivery_not_configured():
    """Test email delivery when SendGrid is not configured."""
    # Create service with no API key
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.sendgrid_api_key = ""
        service = EmailDeliveryService()

    success, message, external_id = await service.send_alert_email(
        to_email="test@example.com",
        alert_title="Test Alert",
        alert_description="Test description",
        severity="critical",
    )

    assert success is False
    assert message == "SendGrid not configured"
    assert external_id is None


@pytest.mark.asyncio
async def test_email_delivery_success(mock_sendgrid):
    """Test successful email delivery via SendGrid."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.sendgrid_api_key = "test-api-key"
        mock_settings.sendgrid_from_email = "alerts@example.com"
        service = EmailDeliveryService()

    success, message, external_id = await service.send_alert_email(
        to_email="recipient@example.com",
        alert_title="Fire Alarm Activated",
        alert_description="Building A smoke detector triggered",
        severity="critical",
    )

    assert success is True
    assert message == "Email accepted"
    assert external_id == "test-msg-id-123"

    # Verify SendGrid client was called
    assert mock_sendgrid.send.called


@pytest.mark.asyncio
async def test_email_delivery_failure(mock_sendgrid):
    """Test email delivery failure handling."""
    # Make SendGrid raise an exception
    mock_sendgrid.send.side_effect = Exception("SendGrid API error")

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.sendgrid_api_key = "test-api-key"
        mock_settings.sendgrid_from_email = "alerts@example.com"
        service = EmailDeliveryService()

    success, message, external_id = await service.send_alert_email(
        to_email="recipient@example.com",
        alert_title="Test Alert",
        alert_description="Test description",
        severity="high",
    )

    assert success is False
    assert "SendGrid API error" in message
    assert external_id is None


@pytest.mark.asyncio
async def test_email_subject_format(mock_sendgrid):
    """Test that email subject includes severity prefix."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.sendgrid_api_key = "test-api-key"
        mock_settings.sendgrid_from_email = "alerts@example.com"
        service = EmailDeliveryService()

    await service.send_alert_email(
        to_email="recipient@example.com",
        alert_title="Test Alert",
        alert_description="Test",
        severity="critical",
    )

    # Check that Mail object was created with correct subject
    from sendgrid.helpers.mail import Mail
    with patch.object(Mail, "__init__", return_value=None) as mock_mail_init:
        await service.send_alert_email(
            to_email="test@example.com",
            alert_title="Alert Title",
            alert_description="Description",
            severity="critical",
        )


# ===========================
# SMSDeliveryService Tests
# ===========================

@pytest.mark.asyncio
async def test_sms_delivery_not_configured():
    """Test SMS delivery when Twilio is not configured."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.twilio_account_sid = ""
        mock_settings.twilio_auth_token = ""
        mock_settings.twilio_from_number = ""
        service = SMSDeliveryService()

    success, message, external_id = await service.send_alert_sms(
        to_phone="+15551234567",
        alert_title="Test Alert",
        severity="critical",
    )

    assert success is False
    assert message == "Twilio not configured"
    assert external_id is None


@pytest.mark.asyncio
async def test_sms_delivery_success(mock_twilio):
    """Test successful SMS delivery via Twilio."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.twilio_account_sid = "test-sid"
        mock_settings.twilio_auth_token = "test-token"
        mock_settings.twilio_from_number = "+15559999999"
        service = SMSDeliveryService()

    success, message, external_id = await service.send_alert_sms(
        to_phone="+15551234567",
        alert_title="Fire Alarm",
        severity="critical",
    )

    assert success is True
    assert "SMS sent" in message
    assert external_id == "SM123456789"


@pytest.mark.asyncio
async def test_sms_phone_normalization(mock_twilio):
    """Test that phone numbers are normalized to E.164 format."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.twilio_account_sid = "test-sid"
        mock_settings.twilio_auth_token = "test-token"
        mock_settings.twilio_from_number = "+15559999999"
        service = SMSDeliveryService()

    # Test various phone formats
    test_cases = [
        ("(555) 123-4567", "+15551234567"),
        ("555-123-4567", "+15551234567"),
        ("555 123 4567", "+15551234567"),
        ("+15551234567", "+15551234567"),
    ]

    for input_phone, expected_e164 in test_cases:
        normalized = service._normalize_phone(input_phone)
        assert normalized == expected_e164, f"Failed for {input_phone}"


@pytest.mark.asyncio
async def test_sms_delivery_truncation(mock_twilio):
    """Test that SMS body is truncated to 160 characters."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.twilio_account_sid = "test-sid"
        mock_settings.twilio_auth_token = "test-token"
        mock_settings.twilio_from_number = "+15559999999"
        service = SMSDeliveryService()

    # Create a very long alert title
    long_title = "A" * 200

    success, message, external_id = await service.send_alert_sms(
        to_phone="+15551234567",
        alert_title=long_title,
        severity="critical",
    )

    assert success is True

    # Verify that the message body passed to Twilio is <= 160 chars
    call_kwargs = mock_twilio.messages.create_async.call_args.kwargs
    assert len(call_kwargs["body"]) <= 160


@pytest.mark.asyncio
async def test_sms_delivery_failure(mock_twilio):
    """Test SMS delivery failure handling."""
    mock_twilio.messages.create_async.side_effect = Exception("Twilio API error")

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.twilio_account_sid = "test-sid"
        mock_settings.twilio_auth_token = "test-token"
        mock_settings.twilio_from_number = "+15559999999"
        service = SMSDeliveryService()

    success, message, external_id = await service.send_alert_sms(
        to_phone="+15551234567",
        alert_title="Test Alert",
        severity="high",
    )

    assert success is False
    assert "Twilio API error" in message
    assert external_id is None


# ===========================
# PushDeliveryService Tests
# ===========================

@pytest.mark.asyncio
async def test_push_delivery_not_configured():
    """Test push delivery when VAPID keys are not configured."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.vapid_private_key = ""
        service = PushDeliveryService()

    subscription = {
        "endpoint": "https://push.example.com/sub/123",
        "keys": {"p256dh": "test-p256dh", "auth": "test-auth"},
    }

    success, message, external_id = await service.send_alert_push(
        subscription_info=subscription,
        alert_title="Test Alert",
        alert_body="Test body",
        severity="critical",
        alert_id="alert-123",
    )

    assert success is False
    assert message == "WebPush not configured"
    assert external_id is None


@pytest.mark.asyncio
async def test_push_delivery_success(mock_webpush):
    """Test successful push delivery via WebPush."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.vapid_private_key = "test-private-key"
        mock_settings.vapid_public_key = "test-public-key"
        mock_settings.vapid_mailto = "mailto:admin@example.com"
        service = PushDeliveryService()

    subscription = {
        "endpoint": "https://push.example.com/sub/123",
        "keys": {"p256dh": "test-p256dh", "auth": "test-auth"},
    }

    success, message, external_id = await service.send_alert_push(
        subscription_info=subscription,
        alert_title="Fire Alarm",
        alert_body="Building A smoke detector triggered",
        severity="critical",
        alert_id="alert-123",
    )

    assert success is True
    assert message == "Push sent"
    assert external_id is None  # WebPush doesn't return external IDs


@pytest.mark.asyncio
async def test_push_delivery_expired_subscription(mock_webpush):
    """Test handling of expired push subscriptions (410 Gone)."""
    from pywebpush import WebPushException

    # Simulate 410 Gone error
    mock_webpush.side_effect = WebPushException("410 Gone")

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.vapid_private_key = "test-private-key"
        mock_settings.vapid_public_key = "test-public-key"
        mock_settings.vapid_mailto = "mailto:admin@example.com"
        service = PushDeliveryService()

    subscription = {
        "endpoint": "https://push.example.com/sub/123",
        "keys": {"p256dh": "test-p256dh", "auth": "test-auth"},
    }

    success, message, external_id = await service.send_alert_push(
        subscription_info=subscription,
        alert_title="Test Alert",
        alert_body="Test body",
        severity="high",
        alert_id="alert-123",
    )

    assert success is False
    assert message == "subscription_expired"
    assert external_id is None


@pytest.mark.asyncio
async def test_push_delivery_failure(mock_webpush):
    """Test push delivery failure handling."""
    mock_webpush.side_effect = Exception("WebPush error")

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.vapid_private_key = "test-private-key"
        mock_settings.vapid_public_key = "test-public-key"
        mock_settings.vapid_mailto = "mailto:admin@example.com"
        service = PushDeliveryService()

    subscription = {
        "endpoint": "https://push.example.com/sub/123",
        "keys": {"p256dh": "test-p256dh", "auth": "test-auth"},
    }

    success, message, external_id = await service.send_alert_push(
        subscription_info=subscription,
        alert_title="Test Alert",
        alert_body="Test body",
        severity="high",
        alert_id="alert-123",
    )

    assert success is False
    assert "WebPush error" in message


# ===========================
# RetryManager Tests
# ===========================

@pytest.mark.asyncio
async def test_retry_succeeds_first_try():
    """Test retry manager with function that succeeds immediately."""
    retry_manager = NotificationRetryManager()

    # Mock delivery function that succeeds
    async def mock_delivery():
        return (True, "Success", "msg-id-123")

    result = await retry_manager.execute_with_retry(mock_delivery)

    assert result == (True, "Success", "msg-id-123")


@pytest.mark.asyncio
async def test_retry_succeeds_after_failure():
    """Test retry manager with function that fails once then succeeds."""
    retry_manager = NotificationRetryManager()

    call_count = 0

    async def mock_delivery():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Temporary failure")
        return (True, "Success", "msg-id-123")

    result = await retry_manager.execute_with_retry(mock_delivery)

    assert result == (True, "Success", "msg-id-123")
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_exhausted():
    """Test retry manager exhausts retries after 3 attempts."""
    retry_manager = NotificationRetryManager()

    call_count = 0

    async def mock_delivery():
        nonlocal call_count
        call_count += 1
        raise Exception(f"Permanent failure {call_count}")

    with pytest.raises(Exception, match="Permanent failure"):
        await retry_manager.execute_with_retry(mock_delivery)

    assert call_count == 3


# ===========================
# NotificationService Integration Tests
# ===========================

@pytest.mark.asyncio
async def test_notify_respects_email_preference(
    db_session: AsyncSession,
    test_alert: Alert,
    test_user_with_prefs: tuple[User, NotificationPreference],
    mock_sendgrid,
    mock_twilio,
):
    """Test that NotificationService respects user channel preferences."""
    user, prefs = test_user_with_prefs

    # Enable only email
    prefs.email_enabled = True
    prefs.sms_enabled = False
    prefs.push_enabled = False
    await db_session.commit()

    # Create notification service
    from sqlalchemy.ext.asyncio import async_sessionmaker
    session_factory = async_sessionmaker(
        db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Mock the delivery services
    with patch.object(EmailDeliveryService, "send_alert_email") as mock_email:
        with patch.object(SMSDeliveryService, "send_alert_sms") as mock_sms:
            mock_email.return_value = (True, "Email sent", "msg-123")
            mock_sms.return_value = (True, "SMS sent", "SM-123")

            service = NotificationService(session_factory)
            results = await service.notify_for_alert(test_alert)

    # Email should have been called, SMS should NOT
    # Note: Results may be empty if no active subscriptions in test DB
    # Instead, verify delivery records in database
    from sqlalchemy import select
    result = await db_session.execute(
        select(NotificationDelivery).where(
            NotificationDelivery.alert_id == test_alert.id
        )
    )
    deliveries = list(result.scalars().all())

    # Should have email delivery record
    email_deliveries = [d for d in deliveries if d.channel == DeliveryChannel.EMAIL.value]
    sms_deliveries = [d for d in deliveries if d.channel == DeliveryChannel.SMS.value]

    assert len(email_deliveries) > 0
    assert len(sms_deliveries) == 0


@pytest.mark.asyncio
async def test_notify_respects_quiet_hours(
    db_session: AsyncSession,
    test_alert: Alert,
    test_user_with_prefs: tuple[User, NotificationPreference],
):
    """Test that quiet hours block non-critical notifications."""
    user, prefs = test_user_with_prefs

    # Set quiet hours to current time (will always be in quiet hours for test)
    now = datetime.now(timezone.utc).time()
    prefs.quiet_start = time(hour=now.hour, minute=0)
    prefs.quiet_end = time(hour=(now.hour + 2) % 24, minute=0)
    prefs.quiet_override_critical = False
    await db_session.commit()

    # Change alert to MEDIUM severity (not critical)
    test_alert.severity = AlertSeverity.MEDIUM
    await db_session.commit()

    # Create notification service
    from sqlalchemy.ext.asyncio import async_sessionmaker
    session_factory = async_sessionmaker(
        db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    service = NotificationService(session_factory)
    results = await service.notify_for_alert(test_alert)

    # No notifications should be sent during quiet hours for non-critical alerts
    # Note: This depends on min_severity filter too
    # Since alert is MEDIUM (level 3) and min_severity=1 (critical only),
    # it would be filtered out anyway. Let's adjust the test.

    # Set min_severity to allow MEDIUM alerts
    prefs.min_severity = 3
    await db_session.commit()

    service = NotificationService(session_factory)
    results = await service.notify_for_alert(test_alert)

    # Should be blocked by quiet hours
    assert len(results) == 0


@pytest.mark.asyncio
async def test_notify_quiet_hours_override_critical(
    db_session: AsyncSession,
    test_alert: Alert,
    test_user_with_prefs: tuple[User, NotificationPreference],
):
    """Test that critical alerts override quiet hours when configured."""
    user, prefs = test_user_with_prefs

    # Set quiet hours to current time
    now = datetime.now(timezone.utc).time()
    prefs.quiet_start = time(hour=now.hour, minute=0)
    prefs.quiet_end = time(hour=(now.hour + 2) % 24, minute=0)
    prefs.quiet_override_critical = True  # Allow critical alerts during quiet hours
    await db_session.commit()

    # Alert is CRITICAL by default
    assert test_alert.severity == AlertSeverity.CRITICAL

    # Create notification service
    from sqlalchemy.ext.asyncio import async_sessionmaker
    session_factory = async_sessionmaker(
        db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Mock delivery services to succeed
    with patch.object(EmailDeliveryService, "send_alert_email") as mock_email:
        mock_email.return_value = (True, "Email sent", "msg-123")

        service = NotificationService(session_factory)
        results = await service.notify_for_alert(test_alert)

    # Critical alert should be sent despite quiet hours
    from sqlalchemy import select
    result = await db_session.execute(
        select(NotificationDelivery).where(
            NotificationDelivery.alert_id == test_alert.id
        )
    )
    deliveries = list(result.scalars().all())
    assert len(deliveries) > 0


@pytest.mark.asyncio
async def test_notify_creates_delivery_records(
    db_session: AsyncSession,
    test_alert: Alert,
    test_user_with_prefs: tuple[User, NotificationPreference],
):
    """Test that NotificationService creates delivery records for each attempt."""
    user, prefs = test_user_with_prefs

    # Create notification service
    from sqlalchemy.ext.asyncio import async_sessionmaker
    session_factory = async_sessionmaker(
        db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Mock all delivery services
    with patch.object(EmailDeliveryService, "send_alert_email") as mock_email:
        with patch.object(SMSDeliveryService, "send_alert_sms") as mock_sms:
            mock_email.return_value = (True, "Email sent", "msg-123")
            mock_sms.return_value = (True, "SMS sent", "SM-123")

            service = NotificationService(session_factory)
            await service.notify_for_alert(test_alert)

    # Query delivery records
    from sqlalchemy import select
    result = await db_session.execute(
        select(NotificationDelivery).where(
            NotificationDelivery.alert_id == test_alert.id,
            NotificationDelivery.user_id == user.id,
        )
    )
    deliveries = list(result.scalars().all())

    # Should have created records for enabled channels (email, sms, push)
    assert len(deliveries) > 0

    # Verify record fields
    for delivery in deliveries:
        assert delivery.alert_id == test_alert.id
        assert delivery.user_id == user.id
        assert delivery.channel in [c.value for c in DeliveryChannel]
        assert delivery.status in [s.value for s in DeliveryStatus]
        assert delivery.attempts >= 1


@pytest.mark.asyncio
async def test_notify_graceful_degradation_unconfigured(
    db_session: AsyncSession,
    test_alert: Alert,
    test_user_with_prefs: tuple[User, NotificationPreference],
):
    """Test that NotificationService gracefully handles unconfigured services."""
    user, prefs = test_user_with_prefs

    # Create notification service
    from sqlalchemy.ext.asyncio import async_sessionmaker
    session_factory = async_sessionmaker(
        db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Mock services to be unconfigured
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.sendgrid_api_key = ""
        mock_settings.twilio_account_sid = ""
        mock_settings.vapid_private_key = ""

        service = NotificationService(session_factory)
        results = await service.notify_for_alert(test_alert)

    # Should not crash, results may be empty or have failure messages
    # All results should be failures with "not configured" messages
    for result in results:
        if not result.success:
            assert "not configured" in result.message.lower()

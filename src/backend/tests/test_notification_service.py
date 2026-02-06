"""Tests for NotificationService."""

import uuid
import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agency import Agency
from app.models.user import User
from app.models.alert import Alert, AlertSeverity, AlertSource
from app.services.notification_service import NotificationService


@pytest.mark.asyncio
class TestNotificationService:
    """Test suite for NotificationService."""

    async def test_notify_user_basic(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test basic user notification."""
        service = NotificationService(db_session)

        # Mock the delivery services
        with patch.object(service, 'delivery_services', {}):
            result = await service.notify_user(
                user_id=test_user.id,
                title="Test Notification",
                body="This is a test",
                channels=["email"],
            )

            assert result is not None

    async def test_notify_alert_basic(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test alert notification."""
        alert = Alert(
            id=uuid.uuid4(),
            title="Test Alert",
            description="Test alert description",
            severity=AlertSeverity.CRITICAL,
            source=AlertSource.MANUAL,
            agency_id=test_agency.id,
        )
        db_session.add(alert)
        await db_session.commit()

        service = NotificationService(db_session)

        with patch.object(service, 'delivery_services', {}):
            result = await service.notify_alert(alert.id)

            assert result is not None

    async def test_create_notification_subscription(self, db_session: AsyncSession, test_user: User):
        """Test creating a notification subscription."""
        service = NotificationService(db_session)

        subscription = await service.create_subscription(
            user_id=test_user.id,
            channel="email",
            enabled=True,
        )

        assert subscription is not None
        assert subscription.user_id == test_user.id
        assert subscription.channel == "email"
        assert subscription.enabled is True

    async def test_get_user_subscriptions(self, db_session: AsyncSession, test_user: User):
        """Test retrieving user subscriptions."""
        service = NotificationService(db_session)

        await service.create_subscription(
            user_id=test_user.id,
            channel="email",
            enabled=True,
        )

        subscriptions = await service.get_user_subscriptions(test_user.id)

        assert len(subscriptions) >= 1

    async def test_update_subscription(self, db_session: AsyncSession, test_user: User):
        """Test updating a subscription."""
        service = NotificationService(db_session)

        subscription = await service.create_subscription(
            user_id=test_user.id,
            channel="email",
            enabled=True,
        )

        updated = await service.update_subscription(
            subscription.id,
            enabled=False,
        )

        assert updated is not None
        assert updated.enabled is False

    async def test_delete_subscription(self, db_session: AsyncSession, test_user: User):
        """Test deleting a subscription."""
        service = NotificationService(db_session)

        subscription = await service.create_subscription(
            user_id=test_user.id,
            channel="email",
            enabled=True,
        )

        result = await service.delete_subscription(subscription.id)

        assert result is True

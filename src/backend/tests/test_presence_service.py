"""Tests for Presence Service."""

import pytest
from datetime import datetime, timedelta
from time import sleep

from app.services.presence_service import PresenceService, UserPresence, get_presence_service


class TestPresenceService:
    """Tests for PresenceService."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear presence data before each test."""
        PresenceService.clear()
        yield
        PresenceService.clear()

    def test_track_user(self):
        """Test tracking a user joining a floor plan."""
        floor_plan_id = "fp-123"
        presence = PresenceService.track_user(
            floor_plan_id=floor_plan_id,
            user_id="user-1",
            user_name="John Doe",
            user_role="editor"
        )

        assert presence.user_id == "user-1"
        assert presence.user_name == "John Doe"
        assert presence.user_role == "editor"
        assert presence.is_editing is False
        assert presence.joined_at is not None

    def test_track_multiple_users(self):
        """Test tracking multiple users on same floor plan."""
        floor_plan_id = "fp-123"

        PresenceService.track_user(floor_plan_id, "user-1", "John Doe")
        PresenceService.track_user(floor_plan_id, "user-2", "Jane Smith")
        PresenceService.track_user(floor_plan_id, "user-3", "Bob Wilson")

        users = PresenceService.get_active_users(floor_plan_id)
        assert len(users) == 3
        user_ids = [u["user_id"] for u in users]
        assert "user-1" in user_ids
        assert "user-2" in user_ids
        assert "user-3" in user_ids

    def test_untrack_user(self):
        """Test removing a user from presence tracking."""
        floor_plan_id = "fp-123"

        PresenceService.track_user(floor_plan_id, "user-1", "John Doe")
        PresenceService.track_user(floor_plan_id, "user-2", "Jane Smith")

        result = PresenceService.untrack_user(floor_plan_id, "user-1")
        assert result is True

        users = PresenceService.get_active_users(floor_plan_id)
        assert len(users) == 1
        assert users[0]["user_id"] == "user-2"

    def test_untrack_nonexistent_user(self):
        """Test untracking a user that doesn't exist."""
        result = PresenceService.untrack_user("fp-123", "user-nonexistent")
        assert result is False

    def test_set_editing(self):
        """Test setting editing status."""
        floor_plan_id = "fp-123"

        PresenceService.track_user(floor_plan_id, "user-1", "John Doe")

        result = PresenceService.set_editing(floor_plan_id, "user-1", True)
        assert result is True

        presence = PresenceService.get_user_presence(floor_plan_id, "user-1")
        assert presence["is_editing"] is True

    def test_set_editing_nonexistent_user(self):
        """Test setting editing status for nonexistent user."""
        result = PresenceService.set_editing("fp-123", "user-nonexistent", True)
        assert result is False

    def test_heartbeat(self):
        """Test heartbeat updates timestamp."""
        floor_plan_id = "fp-123"

        PresenceService.track_user(floor_plan_id, "user-1", "John Doe")

        # Get initial heartbeat
        initial = PresenceService.get_user_presence(floor_plan_id, "user-1")
        initial_heartbeat = initial["last_heartbeat"]

        # Small delay
        sleep(0.01)

        # Update heartbeat
        result = PresenceService.heartbeat(floor_plan_id, "user-1")
        assert result is True

        # Check heartbeat updated
        updated = PresenceService.get_user_presence(floor_plan_id, "user-1")
        assert updated["last_heartbeat"] > initial_heartbeat

    def test_get_active_users_empty(self):
        """Test getting active users from empty floor plan."""
        users = PresenceService.get_active_users("fp-nonexistent")
        assert users == []

    def test_cleanup_stale(self):
        """Test cleanup of stale users."""
        floor_plan_id = "fp-123"

        # Track a user
        PresenceService.track_user(floor_plan_id, "user-1", "John Doe")

        # Manually set a very old heartbeat
        PresenceService._presence[floor_plan_id]["user-1"].last_heartbeat = (
            datetime.utcnow() - timedelta(seconds=30)
        ).isoformat()

        # Cleanup with 15 second timeout
        removed = PresenceService.cleanup_stale(floor_plan_id, timeout_seconds=15)
        assert removed == 1

        users = PresenceService.get_active_users(floor_plan_id)
        assert len(users) == 0

    def test_cleanup_keeps_active_users(self):
        """Test cleanup keeps users with recent heartbeat."""
        floor_plan_id = "fp-123"

        # Track users
        PresenceService.track_user(floor_plan_id, "user-1", "Active User")
        PresenceService.track_user(floor_plan_id, "user-2", "Stale User")

        # Make user-2 stale
        PresenceService._presence[floor_plan_id]["user-2"].last_heartbeat = (
            datetime.utcnow() - timedelta(seconds=30)
        ).isoformat()

        # Cleanup
        removed = PresenceService.cleanup_stale(floor_plan_id, timeout_seconds=15)
        assert removed == 1

        users = PresenceService.get_active_users(floor_plan_id)
        assert len(users) == 1
        assert users[0]["user_id"] == "user-1"

    def test_get_all_floor_plans_with_users(self):
        """Test getting map of floor plans to user counts."""
        PresenceService.track_user("fp-1", "user-1", "User 1")
        PresenceService.track_user("fp-1", "user-2", "User 2")
        PresenceService.track_user("fp-2", "user-3", "User 3")

        floor_plans = PresenceService.get_all_floor_plans_with_users()

        assert floor_plans["fp-1"] == 2
        assert floor_plans["fp-2"] == 1

    def test_user_presence_to_dict(self):
        """Test UserPresence serialization."""
        presence = UserPresence(
            user_id="user-1",
            user_name="John Doe",
            user_role="editor",
            is_editing=True
        )

        data = presence.to_dict()

        assert data["user_id"] == "user-1"
        assert data["user_name"] == "John Doe"
        assert data["user_role"] == "editor"
        assert data["is_editing"] is True
        assert "joined_at" in data
        assert "last_heartbeat" in data

    def test_multiple_floor_plans(self):
        """Test users on different floor plans."""
        PresenceService.track_user("fp-1", "user-1", "User 1")
        PresenceService.track_user("fp-2", "user-1", "User 1")  # Same user, different floor plan
        PresenceService.track_user("fp-2", "user-2", "User 2")

        fp1_users = PresenceService.get_active_users("fp-1")
        fp2_users = PresenceService.get_active_users("fp-2")

        assert len(fp1_users) == 1
        assert len(fp2_users) == 2

    def test_cleanup_all_stale(self):
        """Test cleaning up all stale users across floor plans."""
        PresenceService.track_user("fp-1", "user-1", "Active")
        PresenceService.track_user("fp-2", "user-2", "Stale")

        # Make user-2 stale
        PresenceService._presence["fp-2"]["user-2"].last_heartbeat = (
            datetime.utcnow() - timedelta(seconds=30)
        ).isoformat()

        total_removed = PresenceService.cleanup_all_stale(timeout_seconds=15)
        assert total_removed == 1

        assert len(PresenceService.get_active_users("fp-1")) == 1
        assert len(PresenceService.get_active_users("fp-2")) == 0

"""Presence Tracking Service for real-time floor plan collaboration."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class UserPresence:
    """Represents a user's presence on a floor plan."""
    user_id: str
    user_name: str
    user_role: Optional[str] = None
    is_editing: bool = False
    joined_at: str = None
    last_heartbeat: str = None

    def __post_init__(self):
        if self.joined_at is None:
            self.joined_at = datetime.utcnow().isoformat()
        if self.last_heartbeat is None:
            self.last_heartbeat = self.joined_at

    def to_dict(self) -> dict:
        return asdict(self)


class PresenceService:
    """
    Service for tracking user presence on floor plans.

    Tracks which users are currently viewing/editing each floor plan,
    manages heartbeats, and cleans up stale entries.
    """

    # In-memory storage: { floor_plan_id: { user_id: UserPresence } }
    _presence: Dict[str, Dict[str, UserPresence]] = {}

    # Heartbeat timeout in seconds
    HEARTBEAT_TIMEOUT = 15

    @classmethod
    def track_user(
        cls,
        floor_plan_id: str,
        user_id: str,
        user_name: str,
        user_role: Optional[str] = None
    ) -> UserPresence:
        """
        Track a user joining a floor plan.

        Args:
            floor_plan_id: The floor plan being viewed
            user_id: The user's ID
            user_name: The user's display name
            user_role: Optional role (e.g., 'admin', 'editor')

        Returns:
            UserPresence object
        """
        if floor_plan_id not in cls._presence:
            cls._presence[floor_plan_id] = {}

        presence = UserPresence(
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
        )
        cls._presence[floor_plan_id][user_id] = presence

        logger.info(f"User {user_name} ({user_id}) joined floor plan {floor_plan_id}")
        return presence

    @classmethod
    def untrack_user(cls, floor_plan_id: str, user_id: str) -> bool:
        """
        Remove a user from a floor plan's presence list.

        Args:
            floor_plan_id: The floor plan
            user_id: The user to remove

        Returns:
            True if user was removed, False if not found
        """
        if floor_plan_id in cls._presence:
            if user_id in cls._presence[floor_plan_id]:
                user = cls._presence[floor_plan_id].pop(user_id)
                logger.info(f"User {user.user_name} ({user_id}) left floor plan {floor_plan_id}")

                # Clean up empty floor plan entries
                if not cls._presence[floor_plan_id]:
                    del cls._presence[floor_plan_id]

                return True
        return False

    @classmethod
    def set_editing(cls, floor_plan_id: str, user_id: str, is_editing: bool) -> bool:
        """
        Update a user's editing status.

        Args:
            floor_plan_id: The floor plan
            user_id: The user
            is_editing: Whether the user is in edit mode

        Returns:
            True if updated, False if user not found
        """
        if floor_plan_id in cls._presence:
            if user_id in cls._presence[floor_plan_id]:
                cls._presence[floor_plan_id][user_id].is_editing = is_editing
                cls._presence[floor_plan_id][user_id].last_heartbeat = datetime.utcnow().isoformat()
                return True
        return False

    @classmethod
    def heartbeat(cls, floor_plan_id: str, user_id: str) -> bool:
        """
        Update a user's heartbeat timestamp.

        Args:
            floor_plan_id: The floor plan
            user_id: The user

        Returns:
            True if updated, False if user not found
        """
        if floor_plan_id in cls._presence:
            if user_id in cls._presence[floor_plan_id]:
                cls._presence[floor_plan_id][user_id].last_heartbeat = datetime.utcnow().isoformat()
                return True
        return False

    @classmethod
    def get_active_users(cls, floor_plan_id: str) -> List[dict]:
        """
        Get list of active users on a floor plan.

        Args:
            floor_plan_id: The floor plan

        Returns:
            List of UserPresence dicts
        """
        if floor_plan_id not in cls._presence:
            return []

        # Clean up stale entries first
        cls.cleanup_stale(floor_plan_id)

        return [
            presence.to_dict()
            for presence in cls._presence.get(floor_plan_id, {}).values()
        ]

    @classmethod
    def cleanup_stale(cls, floor_plan_id: str, timeout_seconds: int = None) -> int:
        """
        Remove users who haven't sent a heartbeat within the timeout.

        Args:
            floor_plan_id: The floor plan to clean
            timeout_seconds: Override default timeout

        Returns:
            Number of stale entries removed
        """
        if floor_plan_id not in cls._presence:
            return 0

        timeout = timeout_seconds or cls.HEARTBEAT_TIMEOUT
        cutoff = datetime.utcnow() - timedelta(seconds=timeout)
        cutoff_iso = cutoff.isoformat()

        stale_users = []
        for user_id, presence in cls._presence[floor_plan_id].items():
            if presence.last_heartbeat < cutoff_iso:
                stale_users.append(user_id)

        for user_id in stale_users:
            cls.untrack_user(floor_plan_id, user_id)
            logger.info(f"Cleaned up stale presence for user {user_id} on floor plan {floor_plan_id}")

        return len(stale_users)

    @classmethod
    def cleanup_all_stale(cls, timeout_seconds: int = None) -> int:
        """
        Remove stale users from all floor plans.

        Returns:
            Total number of stale entries removed
        """
        total = 0
        for floor_plan_id in list(cls._presence.keys()):
            total += cls.cleanup_stale(floor_plan_id, timeout_seconds)
        return total

    @classmethod
    def get_user_presence(cls, floor_plan_id: str, user_id: str) -> Optional[dict]:
        """
        Get a specific user's presence on a floor plan.

        Args:
            floor_plan_id: The floor plan
            user_id: The user

        Returns:
            UserPresence dict or None if not found
        """
        if floor_plan_id in cls._presence:
            presence = cls._presence[floor_plan_id].get(user_id)
            if presence:
                return presence.to_dict()
        return None

    @classmethod
    def get_all_floor_plans_with_users(cls) -> Dict[str, int]:
        """
        Get a map of floor plans to user counts.

        Returns:
            Dict mapping floor_plan_id to number of active users
        """
        return {
            fp_id: len(users)
            for fp_id, users in cls._presence.items()
            if users
        }

    @classmethod
    def clear(cls):
        """Clear all presence data. Useful for testing."""
        cls._presence.clear()


# Singleton instance
_presence_service: Optional[PresenceService] = None


def get_presence_service() -> PresenceService:
    """Get the presence service instance."""
    global _presence_service
    if _presence_service is None:
        _presence_service = PresenceService()
    return _presence_service

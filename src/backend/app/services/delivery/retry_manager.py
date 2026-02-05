"""Notification retry manager with exponential backoff."""

import backoff
import logging

logger = logging.getLogger(__name__)


class NotificationRetryManager:
    """Manages retry logic for notification delivery with exponential backoff."""

    MAX_TRIES = 3  # Per success criteria requirement

    @staticmethod
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        jitter=backoff.full_jitter,
        on_backoff=lambda details: logger.warning(
            "Notification retry attempt %d after %.2fs",
            details["tries"],
            details["wait"],
        ),
        on_giveup=lambda details: logger.error(
            "Notification delivery failed after %d attempts (%.2fs elapsed)",
            details["tries"],
            details["elapsed"],
        ),
    )
    async def execute_with_retry(delivery_func, *args, **kwargs):
        """Execute a delivery function with exponential backoff retry.

        Args:
            delivery_func: Async callable that performs the delivery
            *args, **kwargs: Arguments to pass to delivery_func

        Returns:
            Result from delivery_func (tuple of success, message, external_id)

        Raises:
            Last exception if all retries exhausted
        """
        return await delivery_func(*args, **kwargs)

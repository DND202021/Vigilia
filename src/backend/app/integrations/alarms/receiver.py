"""Alarm receiver service.

Handles incoming alarm signals, decodes them, and creates
ERIOP alerts.
"""

from datetime import datetime, timezone
from typing import Callable, Awaitable
import asyncio
import logging

from app.integrations.base import IntegrationAdapter, CircuitBreakerConfig, IntegrationError
from app.integrations.alarms.protocols import (
    AlarmProtocol,
    RawAlarmSignal,
    StandardizedAlarm,
)
from app.integrations.alarms.contact_id import ContactIdDecoder
from app.integrations.alarms.normalizer import AlarmNormalizer


logger = logging.getLogger(__name__)


class AlarmReceiverError(IntegrationError):
    """Alarm receiver specific errors."""
    pass


class AlarmReceiverService(IntegrationAdapter):
    """
    Service for receiving and processing alarm signals.

    Handles multiple protocols and provides a unified interface
    for alarm processing.
    """

    def __init__(
        self,
        account_repository=None,
        alert_service=None,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ):
        """
        Initialize alarm receiver.

        Args:
            account_repository: Repository for alarm account data
            alert_service: ERIOP alert service for creating alerts
            circuit_breaker_config: Circuit breaker configuration
        """
        super().__init__(
            name="alarm_receiver",
            circuit_breaker_config=circuit_breaker_config,
        )

        self.account_repo = account_repository
        self.alert_service = alert_service

        # Initialize decoders
        self.decoders = {
            AlarmProtocol.CONTACT_ID: ContactIdDecoder(),
        }

        # Initialize normalizer
        self.normalizer = AlarmNormalizer(
            account_repository=account_repository,
        )

        # Event handlers
        self._alarm_handlers: list[Callable[[StandardizedAlarm], Awaitable[None]]] = []

        # Statistics
        self._stats = {
            "signals_received": 0,
            "signals_processed": 0,
            "alerts_created": 0,
            "errors": 0,
            "duplicates_ignored": 0,
        }

        # Recent signals for deduplication
        self._recent_signals: dict[str, datetime] = {}
        self._dedup_window_seconds = 60

    async def connect(self) -> bool:
        """Initialize receiver (no external connection needed)."""
        self._connected = True
        logger.info("Alarm receiver initialized")
        return True

    async def disconnect(self) -> None:
        """Shutdown receiver."""
        self._connected = False
        logger.info("Alarm receiver shutdown")

    async def health_check(self) -> dict:
        """Check receiver health."""
        return {
            "status": "healthy" if self._connected else "disconnected",
            "decoders_available": list(self.decoders.keys()),
            "stats": self._stats.copy(),
        }

    def on_alarm(self, handler: Callable[[StandardizedAlarm], Awaitable[None]]):
        """
        Register handler for processed alarms.

        Args:
            handler: Async function to call with each processed alarm
        """
        self._alarm_handlers.append(handler)

    async def receive_signal(
        self,
        raw_data: bytes | str,
        protocol: AlarmProtocol = AlarmProtocol.CONTACT_ID,
    ) -> StandardizedAlarm | None:
        """
        Receive and process an alarm signal.

        Args:
            raw_data: Raw alarm signal data
            protocol: Protocol of the signal

        Returns:
            Processed StandardizedAlarm or None if duplicate/error
        """
        self._stats["signals_received"] += 1

        try:
            # Decode signal
            decoder = self.decoders.get(protocol)
            if not decoder:
                raise AlarmReceiverError(
                    f"No decoder for protocol: {protocol}",
                    source=self.name,
                    retryable=False,
                )

            signal = decoder.decode(raw_data)

            # Check for duplicates
            if await self._is_duplicate(signal):
                self._stats["duplicates_ignored"] += 1
                logger.debug(f"Duplicate signal ignored: {signal.account_number}/{signal.zone}")
                return None

            # Normalize signal
            alarm = await self.normalizer.normalize(signal)

            # Mark as recently seen
            await self._mark_seen(signal)

            # Process through handlers
            await self._dispatch_alarm(alarm)

            self._stats["signals_processed"] += 1

            return alarm

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Error processing alarm signal: {e}")
            raise AlarmReceiverError(
                f"Failed to process alarm: {e}",
                source=self.name,
                original_error=e,
            )

    async def process_and_create_alert(
        self,
        raw_data: bytes | str,
        protocol: AlarmProtocol = AlarmProtocol.CONTACT_ID,
    ) -> dict | None:
        """
        Process alarm signal and create ERIOP alert.

        Args:
            raw_data: Raw alarm signal data
            protocol: Protocol of the signal

        Returns:
            Created alert or None if not created
        """
        alarm = await self.receive_signal(raw_data, protocol)
        if not alarm:
            return None

        if not self.alert_service:
            logger.warning("No alert service configured")
            return None

        # Convert to alert format
        alert_data = self.normalizer.to_alert_data(alarm)

        # Skip test and info events for alert creation
        from app.models.alert import AlertSeverity
        if alert_data.get("severity") == AlertSeverity.INFO:
            logger.debug(f"Skipping alert creation for info event: {alarm.title}")
            return None

        # Create alert
        try:
            alert = await self.alert_service.ingest_alert(**alert_data)
            self._stats["alerts_created"] += 1
            logger.info(f"Created alert {alert.id} from alarm {alarm.source_id}")
            return alert
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return None

    async def _is_duplicate(self, signal: RawAlarmSignal) -> bool:
        """Check if signal is a duplicate within deduplication window."""
        key = self._signal_key(signal)
        last_seen = self._recent_signals.get(key)

        if last_seen:
            elapsed = (datetime.now(timezone.utc) - last_seen).total_seconds()
            if elapsed < self._dedup_window_seconds:
                return True

        return False

    async def _mark_seen(self, signal: RawAlarmSignal):
        """Mark signal as recently seen."""
        key = self._signal_key(signal)
        self._recent_signals[key] = datetime.now(timezone.utc)

        # Cleanup old entries
        await self._cleanup_recent_signals()

    def _signal_key(self, signal: RawAlarmSignal) -> str:
        """Generate unique key for signal deduplication."""
        return f"{signal.account_number}:{signal.event_code}:{signal.zone or ''}"

    async def _cleanup_recent_signals(self):
        """Remove expired entries from recent signals cache."""
        now = datetime.now(timezone.utc)
        expired = []

        for key, timestamp in self._recent_signals.items():
            if (now - timestamp).total_seconds() > self._dedup_window_seconds * 2:
                expired.append(key)

        for key in expired:
            del self._recent_signals[key]

    async def _dispatch_alarm(self, alarm: StandardizedAlarm):
        """Dispatch alarm to registered handlers."""
        for handler in self._alarm_handlers:
            try:
                await handler(alarm)
            except Exception as e:
                logger.error(f"Alarm handler error: {e}")

    def get_stats(self) -> dict:
        """Get receiver statistics."""
        return {
            **self.get_status(),
            "processing_stats": self._stats.copy(),
        }

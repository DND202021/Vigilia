"""Base classes for external integrations.

Provides common functionality for all integration adapters including:
- Circuit breaker pattern for fault tolerance
- Retry logic with exponential backoff
- Health monitoring
- Audit logging
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, TypeVar, Generic
import asyncio
import logging

logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    """Base exception for integration errors."""

    def __init__(
        self,
        message: str,
        source: str | None = None,
        retryable: bool = True,
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.source = source
        self.retryable = retryable
        self.original_error = original_error


class CircuitBreakerOpen(IntegrationError):
    """Raised when circuit breaker is open."""

    def __init__(self, source: str, retry_after: datetime):
        super().__init__(
            f"Circuit breaker open for {source}",
            source=source,
            retryable=False,
        )
        self.retry_after = retry_after


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5        # Failures before opening
    success_threshold: int = 3        # Successes to close from half-open
    timeout_seconds: int = 30         # Time before half-open attempt
    expected_exceptions: tuple = (IntegrationError,)


@dataclass
class CircuitBreakerState:
    """Internal state of circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault-tolerant integrations.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests fail fast
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state.state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state.state == CircuitState.OPEN

    async def __aenter__(self):
        """Enter circuit breaker context."""
        await self._check_state()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit circuit breaker context, record result."""
        if exc_type is None:
            await self._record_success()
        elif isinstance(exc_val, self.config.expected_exceptions):
            await self._record_failure(exc_val)
        return False  # Don't suppress exceptions

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of function call

        Raises:
            CircuitBreakerOpen: If circuit is open
            IntegrationError: If function fails
        """
        async with self:
            return await func(*args, **kwargs)

    async def _check_state(self):
        """Check and potentially transition state."""
        async with self._lock:
            if self._state.state == CircuitState.OPEN:
                # Check if timeout has elapsed
                if self._state.last_failure_time:
                    elapsed = datetime.now(timezone.utc) - self._state.last_failure_time
                    if elapsed >= timedelta(seconds=self.config.timeout_seconds):
                        # Transition to half-open
                        self._state.state = CircuitState.HALF_OPEN
                        self._state.success_count = 0
                        logger.info(f"Circuit {self.name} transitioning to half-open")
                    else:
                        # Still open
                        retry_after = self._state.last_failure_time + timedelta(
                            seconds=self.config.timeout_seconds
                        )
                        raise CircuitBreakerOpen(self.name, retry_after)

    async def _record_success(self):
        """Record successful call."""
        async with self._lock:
            self._state.last_success_time = datetime.now(timezone.utc)

            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1
                if self._state.success_count >= self.config.success_threshold:
                    # Recovery confirmed, close circuit
                    self._state.state = CircuitState.CLOSED
                    self._state.failure_count = 0
                    logger.info(f"Circuit {self.name} closed after recovery")
            elif self._state.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._state.failure_count = 0

    async def _record_failure(self, error: Exception):
        """Record failed call."""
        async with self._lock:
            self._state.last_failure_time = datetime.now(timezone.utc)
            self._state.failure_count += 1

            logger.warning(
                f"Circuit {self.name} failure #{self._state.failure_count}: {error}"
            )

            if self._state.state == CircuitState.HALF_OPEN:
                # Failure in half-open, reopen circuit
                self._state.state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name} reopened after half-open failure")
            elif self._state.state == CircuitState.CLOSED:
                if self._state.failure_count >= self.config.failure_threshold:
                    # Threshold exceeded, open circuit
                    self._state.state = CircuitState.OPEN
                    logger.warning(f"Circuit {self.name} opened after {self._state.failure_count} failures")

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "success_count": self._state.success_count,
            "last_failure": self._state.last_failure_time.isoformat() if self._state.last_failure_time else None,
            "last_success": self._state.last_success_time.isoformat() if self._state.last_success_time else None,
        }


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 5000
    exponential_base: float = 2.0
    jitter: bool = True


class RetryHandler:
    """
    Retry handler with exponential backoff.

    Provides automatic retries for transient failures with
    configurable backoff strategy.
    """

    def __init__(self, config: RetryConfig | None = None):
        self.config = config or RetryConfig()

    async def execute(
        self,
        func: Callable,
        *args,
        retryable_exceptions: tuple = (IntegrationError,),
        **kwargs,
    ) -> Any:
        """
        Execute function with retries.

        Args:
            func: Async function to call
            retryable_exceptions: Exceptions that trigger retry
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of function call

        Raises:
            Last exception if all retries exhausted
        """
        last_error = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except retryable_exceptions as e:
                last_error = e

                # Check if error is retryable
                if isinstance(e, IntegrationError) and not e.retryable:
                    raise

                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.info(
                        f"Retry {attempt + 1}/{self.config.max_retries} "
                        f"after {delay}ms: {e}"
                    )
                    await asyncio.sleep(delay / 1000)

        raise last_error

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next retry with exponential backoff."""
        import random

        delay = self.config.initial_delay_ms * (
            self.config.exponential_base ** attempt
        )
        delay = min(delay, self.config.max_delay_ms)

        if self.config.jitter:
            # Add random jitter (±25%)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


T = TypeVar('T')


class IntegrationAdapter(ABC, Generic[T]):
    """
    Base class for all integration adapters.

    Provides common functionality:
    - Connection management
    - Health checking
    - Circuit breaker integration
    - Retry handling
    - Audit logging
    """

    def __init__(
        self,
        name: str,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
        retry_config: RetryConfig | None = None,
    ):
        self.name = name
        self.circuit_breaker = CircuitBreaker(name, circuit_breaker_config)
        self.retry_handler = RetryHandler(retry_config)
        self._connected = False
        self._last_health_check: datetime | None = None
        self._health_status: dict[str, Any] = {}

    @property
    def is_connected(self) -> bool:
        """Check if adapter is connected."""
        return self._connected

    @property
    def is_healthy(self) -> bool:
        """Check if adapter is healthy."""
        return (
            self._connected
            and self.circuit_breaker.is_closed
            and self._health_status.get("healthy", False)
        )

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to external system.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to external system."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """
        Check health of external system.

        Returns:
            Health status dictionary with at least 'healthy' key
        """
        pass

    async def ensure_connected(self):
        """Ensure adapter is connected, reconnecting if needed."""
        if not self._connected:
            await self.connect()

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker with retries.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of function call
        """
        await self.ensure_connected()

        return await self.circuit_breaker.call(
            self.retry_handler.execute,
            func,
            *args,
            **kwargs,
        )

    async def update_health(self) -> dict[str, Any]:
        """Update and return health status."""
        try:
            self._health_status = await self.health_check()
            self._health_status["healthy"] = True
            self._health_status["checked_at"] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            self._health_status = {
                "healthy": False,
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

        self._last_health_check = datetime.now(timezone.utc)
        return self._health_status

    def get_status(self) -> dict[str, Any]:
        """Get adapter status including circuit breaker stats."""
        return {
            "name": self.name,
            "connected": self._connected,
            "healthy": self.is_healthy,
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "health_status": self._health_status,
            "last_health_check": (
                self._last_health_check.isoformat()
                if self._last_health_check else None
            ),
        }

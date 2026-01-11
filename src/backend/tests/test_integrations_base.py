"""Tests for integration base classes."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from app.integrations.base import (
    IntegrationError,
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
    CircuitBreakerConfig,
    RetryHandler,
    RetryConfig,
    IntegrationAdapter,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_initial_state_closed(self):
        """Circuit should start in closed state."""
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed
        assert not cb.is_open

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Successful calls should keep circuit closed."""
        cb = CircuitBreaker("test")

        async def success():
            return "ok"

        result = await cb.call(success)
        assert result == "ok"
        assert cb.is_closed

    @pytest.mark.asyncio
    async def test_failure_tracking(self):
        """Failures should be tracked."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        async def fail():
            raise IntegrationError("test error")

        # First two failures should not open circuit
        for _ in range(2):
            with pytest.raises(IntegrationError):
                await cb.call(fail)

        assert cb.is_closed
        assert cb._state.failure_count == 2

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self):
        """Circuit should open after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        async def fail():
            raise IntegrationError("test error")

        # Reach failure threshold
        for _ in range(3):
            with pytest.raises(IntegrationError):
                await cb.call(fail)

        assert cb.is_open
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_fails_fast(self):
        """Open circuit should fail fast without calling function."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=60)
        cb = CircuitBreaker("test", config)

        call_count = 0

        async def fail():
            nonlocal call_count
            call_count += 1
            raise IntegrationError("test error")

        # Open the circuit
        with pytest.raises(IntegrationError):
            await cb.call(fail)

        assert call_count == 1
        assert cb.is_open

        # Subsequent calls should fail fast
        with pytest.raises(CircuitBreakerOpen):
            await cb.call(fail)

        # Function was not called again
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self):
        """Circuit should transition to half-open after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=0,  # Immediate timeout for testing
        )
        cb = CircuitBreaker("test", config)

        async def fail():
            raise IntegrationError("test error")

        # Open the circuit
        with pytest.raises(IntegrationError):
            await cb.call(fail)

        assert cb.is_open

        # Set last failure to the past
        cb._state.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=1)

        # Check state should transition to half-open
        await cb._check_state()
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_closes_after_success_in_half_open(self):
        """Circuit should close after successes in half-open state."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0,
        )
        cb = CircuitBreaker("test", config)

        async def fail():
            raise IntegrationError("test error")

        async def success():
            return "ok"

        # Open the circuit
        with pytest.raises(IntegrationError):
            await cb.call(fail)

        # Force half-open
        cb._state.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        await cb._check_state()
        assert cb.state == CircuitState.HALF_OPEN

        # Successes should close circuit
        await cb.call(success)
        await cb.call(success)

        assert cb.is_closed

    @pytest.mark.asyncio
    async def test_reopens_on_failure_in_half_open(self):
        """Circuit should reopen on failure in half-open state."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=0,
        )
        cb = CircuitBreaker("test", config)

        async def fail():
            raise IntegrationError("test error")

        # Open and force to half-open
        with pytest.raises(IntegrationError):
            await cb.call(fail)

        cb._state.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        await cb._check_state()
        assert cb.state == CircuitState.HALF_OPEN

        # Failure should reopen
        with pytest.raises(IntegrationError):
            await cb.call(fail)

        assert cb.is_open

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Stats should reflect circuit state."""
        cb = CircuitBreaker("test-circuit")

        async def success():
            return "ok"

        await cb.call(success)
        stats = cb.get_stats()

        assert stats["name"] == "test-circuit"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert stats["last_success"] is not None


class TestRetryHandler:
    """Tests for RetryHandler."""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Successful call should not retry."""
        handler = RetryHandler()
        call_count = 0

        async def success():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await handler.execute(success)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """Should retry on retryable exceptions."""
        config = RetryConfig(max_retries=3, initial_delay_ms=1)
        handler = RetryHandler(config)
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise IntegrationError("test error")
            return "ok"

        result = await handler.execute(fail_then_succeed)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        """Should raise after max retries exhausted."""
        config = RetryConfig(max_retries=2, initial_delay_ms=1)
        handler = RetryHandler(config)
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise IntegrationError("test error")

        with pytest.raises(IntegrationError):
            await handler.execute(always_fail)

        assert call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable(self):
        """Should not retry non-retryable errors."""
        config = RetryConfig(max_retries=3, initial_delay_ms=1)
        handler = RetryHandler(config)
        call_count = 0

        async def non_retryable():
            nonlocal call_count
            call_count += 1
            raise IntegrationError("test", retryable=False)

        with pytest.raises(IntegrationError):
            await handler.execute(non_retryable)

        assert call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Delay should increase exponentially."""
        config = RetryConfig(
            max_retries=3,
            initial_delay_ms=100,
            exponential_base=2.0,
            jitter=False,
        )
        handler = RetryHandler(config)

        # Test delay calculation
        assert handler._calculate_delay(0) == 100
        assert handler._calculate_delay(1) == 200
        assert handler._calculate_delay(2) == 400

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Delay should not exceed max_delay_ms."""
        config = RetryConfig(
            initial_delay_ms=100,
            max_delay_ms=500,
            exponential_base=10.0,
            jitter=False,
        )
        handler = RetryHandler(config)

        # Should be capped at 500
        assert handler._calculate_delay(2) == 500


class MockAdapter(IntegrationAdapter):
    """Mock adapter for testing."""

    def __init__(self):
        super().__init__("mock_adapter")
        self._health_status = {"status": "ok"}

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health_check(self) -> dict:
        return self._health_status


class TestIntegrationAdapter:
    """Tests for IntegrationAdapter base class."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Adapter should track connection state."""
        adapter = MockAdapter()

        assert not adapter.is_connected
        await adapter.connect()
        assert adapter.is_connected
        await adapter.disconnect()
        assert not adapter.is_connected

    @pytest.mark.asyncio
    async def test_ensure_connected(self):
        """ensure_connected should auto-connect."""
        adapter = MockAdapter()

        assert not adapter.is_connected
        await adapter.ensure_connected()
        assert adapter.is_connected

    @pytest.mark.asyncio
    async def test_health_update(self):
        """update_health should refresh health status."""
        adapter = MockAdapter()
        await adapter.connect()

        health = await adapter.update_health()

        assert health["healthy"] is True
        assert "checked_at" in health

    @pytest.mark.asyncio
    async def test_get_status(self):
        """get_status should return comprehensive status."""
        adapter = MockAdapter()
        await adapter.connect()
        await adapter.update_health()

        status = adapter.get_status()

        assert status["name"] == "mock_adapter"
        assert status["connected"] is True
        assert status["healthy"] is True
        assert "circuit_breaker" in status
        assert "health_status" in status

    @pytest.mark.asyncio
    async def test_execute_through_circuit_breaker(self):
        """execute should use circuit breaker and retry."""
        adapter = MockAdapter()
        await adapter.connect()

        async def work():
            return "done"

        result = await adapter.execute(work)
        assert result == "done"

"""Tests for HealthService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.health_service import (
    HealthService,
    HealthStatus,
    ComponentHealth,
    SystemHealth,
)


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_health_status_values(self):
        """Test health status enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestComponentHealth:
    """Tests for ComponentHealth dataclass."""

    def test_component_health_creation(self):
        """Test creating ComponentHealth with required fields."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
        )
        assert health.name == "test"
        assert health.status == HealthStatus.HEALTHY
        assert health.message is None
        assert health.latency_ms is None

    def test_component_health_with_all_fields(self):
        """Test creating ComponentHealth with all fields."""
        health = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="PostgreSQL responding",
            latency_ms=5.25,
        )
        assert health.name == "database"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "PostgreSQL responding"
        assert health.latency_ms == 5.25


class TestSystemHealth:
    """Tests for SystemHealth dataclass."""

    def test_system_health_to_dict(self):
        """Test converting SystemHealth to dictionary."""
        components = [
            ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="OK",
                latency_ms=5.0,
            ),
            ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message="Slow",
                latency_ms=100.0,
            ),
        ]
        health = SystemHealth(
            status=HealthStatus.DEGRADED,
            version="0.1.0",
            components=components,
        )

        result = health.to_dict()

        assert result["status"] == "degraded"
        assert result["version"] == "0.1.0"
        assert len(result["components"]) == 2
        assert result["components"][0]["name"] == "database"
        assert result["components"][0]["status"] == "healthy"
        assert result["components"][1]["name"] == "redis"
        assert result["components"][1]["status"] == "degraded"


class TestHealthService:
    """Tests for HealthService."""

    @pytest.fixture
    def health_service(self):
        """Create health service instance."""
        return HealthService()

    @pytest.mark.asyncio
    async def test_check_database_healthy(self, health_service):
        """Test database health check when database is healthy."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        result = await health_service.check_database(mock_session)

        assert result.name == "database"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "PostgreSQL responding"
        assert result.latency_ms is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_database_unhealthy(self, health_service):
        """Test database health check when database fails."""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Connection refused")

        result = await health_service.check_database(mock_session)

        assert result.name == "database"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection failed" in result.message
        assert result.latency_ms is not None

    @pytest.mark.asyncio
    async def test_check_redis_healthy(self, health_service):
        """Test Redis health check when Redis is healthy."""
        with patch("app.services.health_service.redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_redis.from_url.return_value = mock_client

            with patch("app.core.metrics.set_redis_connected"):
                result = await health_service.check_redis()

        assert result.name == "redis"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Redis responding"
        assert result.latency_ms is not None

    @pytest.mark.asyncio
    async def test_check_redis_unhealthy(self, health_service):
        """Test Redis health check when Redis fails."""
        with patch("app.services.health_service.redis") as mock_redis:
            mock_redis.from_url.side_effect = Exception("Connection refused")

            with patch("app.core.metrics.set_redis_connected"):
                result = await health_service.check_redis()

        assert result.name == "redis"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection failed" in result.message

    @pytest.mark.asyncio
    async def test_check_db_pool_healthy(self, health_service):
        """Test database pool check when pool is healthy."""
        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_engine.pool = mock_pool

        with patch("app.core.metrics.set_db_pool_available"):
            result = await health_service.check_db_pool(mock_engine)

        assert result.name == "db_pool"
        assert result.status == HealthStatus.HEALTHY
        assert "size=10" in result.message
        assert "available=8" in result.message

    @pytest.mark.asyncio
    async def test_check_db_pool_degraded(self, health_service):
        """Test database pool check when pool is degraded."""
        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 0
        mock_pool.checkedout.return_value = 10
        mock_pool.overflow.return_value = 2  # Under 5, so degraded
        mock_engine.pool = mock_pool

        with patch("app.core.metrics.set_db_pool_available"):
            result = await health_service.check_db_pool(mock_engine)

        assert result.name == "db_pool"
        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_check_db_pool_unhealthy(self, health_service):
        """Test database pool check when pool is exhausted."""
        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 0
        mock_pool.checkedout.return_value = 10
        mock_pool.overflow.return_value = 6  # Over 5, so unhealthy
        mock_engine.pool = mock_pool

        with patch("app.core.metrics.set_db_pool_available"):
            result = await health_service.check_db_pool(mock_engine)

        assert result.name == "db_pool"
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_db_pool_error(self, health_service):
        """Test database pool check when pool check fails."""
        mock_engine = MagicMock()
        mock_engine.pool.size.side_effect = Exception("Pool error")

        result = await health_service.check_db_pool(mock_engine)

        assert result.name == "db_pool"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Pool check failed" in result.message

    @pytest.mark.asyncio
    async def test_get_readiness_all_healthy(self, health_service):
        """Test readiness check when all components are healthy."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_engine.pool = mock_pool

        with patch("app.services.health_service.redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_redis.from_url.return_value = mock_client

            with patch("app.core.metrics.set_redis_connected"):
                with patch("app.core.metrics.set_db_pool_available"):
                    result = await health_service.get_readiness(mock_session, mock_engine)

        assert result.status == HealthStatus.HEALTHY
        assert result.version == "0.1.0"
        assert len(result.components) == 3

    @pytest.mark.asyncio
    async def test_get_readiness_one_unhealthy(self, health_service):
        """Test readiness check when one component is unhealthy."""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("DB down")

        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_engine.pool = mock_pool

        with patch("app.services.health_service.redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_redis.from_url.return_value = mock_client

            with patch("app.core.metrics.set_redis_connected"):
                with patch("app.core.metrics.set_db_pool_available"):
                    result = await health_service.get_readiness(mock_session, mock_engine)

        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_get_readiness_one_degraded(self, health_service):
        """Test readiness check when one component is degraded."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 0  # No available connections
        mock_pool.checkedout.return_value = 10
        mock_pool.overflow.return_value = 2  # Degraded threshold
        mock_engine.pool = mock_pool

        with patch("app.services.health_service.redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_redis.from_url.return_value = mock_client

            with patch("app.core.metrics.set_redis_connected"):
                with patch("app.core.metrics.set_db_pool_available"):
                    result = await health_service.get_readiness(mock_session, mock_engine)

        assert result.status == HealthStatus.DEGRADED

    def test_get_liveness(self, health_service):
        """Test liveness check."""
        result = health_service.get_liveness()

        assert result.status == HealthStatus.HEALTHY
        assert result.version == "0.1.0"
        assert len(result.components) == 1
        assert result.components[0].name == "application"
        assert result.components[0].status == HealthStatus.HEALTHY
        assert result.components[0].message == "Application is running"

"""Health check service for ERIOP platform."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import redis.asyncio as redis
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = structlog.get_logger()


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    message: str | None = None
    latency_ms: float | None = None


@dataclass
class SystemHealth:
    """Overall system health status."""

    status: HealthStatus
    version: str
    components: list[ComponentHealth]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status.value,
            "version": self.version,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                }
                for c in self.components
            ],
        }


class HealthService:
    """Service for checking health of system components."""

    VERSION = "0.1.0"

    async def check_database(self, session: AsyncSession) -> ComponentHealth:
        """Check database connectivity and response time."""
        import time

        start = time.perf_counter()
        try:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            latency = (time.perf_counter() - start) * 1000

            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="PostgreSQL responding",
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.error("Database health check failed", error=str(e))
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection failed: {str(e)[:100]}",
                latency_ms=round(latency, 2),
            )

    async def check_redis(self) -> ComponentHealth:
        """Check Redis connectivity and response time."""
        import time

        start = time.perf_counter()
        try:
            client = redis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            latency = (time.perf_counter() - start) * 1000
            await client.close()

            # Update metrics
            from app.core.metrics import set_redis_connected

            set_redis_connected(True)

            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis responding",
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.error("Redis health check failed", error=str(e))

            # Update metrics
            from app.core.metrics import set_redis_connected

            set_redis_connected(False)

            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection failed: {str(e)[:100]}",
                latency_ms=round(latency, 2),
            )

    async def check_db_pool(self, engine) -> ComponentHealth:
        """Check database connection pool status."""
        try:
            pool = engine.pool
            pool_size = pool.size()
            checked_in = pool.checkedin()
            checked_out = pool.checkedout()
            overflow = pool.overflow()

            # Update metrics
            from app.core.metrics import set_db_pool_available

            set_db_pool_available(checked_in)

            status = HealthStatus.HEALTHY
            if checked_in == 0 and checked_out > 0:
                status = HealthStatus.DEGRADED if overflow < 5 else HealthStatus.UNHEALTHY

            return ComponentHealth(
                name="db_pool",
                status=status,
                message=f"size={pool_size}, available={checked_in}, in_use={checked_out}, overflow={overflow}",
            )
        except Exception as e:
            logger.error("DB pool health check failed", error=str(e))
            return ComponentHealth(
                name="db_pool",
                status=HealthStatus.UNHEALTHY,
                message=f"Pool check failed: {str(e)[:100]}",
            )

    async def get_readiness(self, session: AsyncSession, engine) -> SystemHealth:
        """Get full readiness status including all dependencies."""
        components = []

        # Check all components
        db_health = await self.check_database(session)
        components.append(db_health)

        redis_health = await self.check_redis()
        components.append(redis_health)

        pool_health = await self.check_db_pool(engine)
        components.append(pool_health)

        # Determine overall status
        statuses = [c.status for c in components]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return SystemHealth(
            status=overall_status,
            version=self.VERSION,
            components=components,
        )

    def get_liveness(self) -> SystemHealth:
        """Get basic liveness status (application is running)."""
        return SystemHealth(
            status=HealthStatus.HEALTHY,
            version=self.VERSION,
            components=[
                ComponentHealth(
                    name="application",
                    status=HealthStatus.HEALTHY,
                    message="Application is running",
                )
            ],
        )


# Singleton instance
health_service = HealthService()

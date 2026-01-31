"""Prometheus metrics instrumentation for ERIOP."""

from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_fastapi_instrumentator.metrics import Info

# Custom metrics for ERIOP

# WebSocket connections gauge
websocket_connections = Gauge(
    "eriop_websocket_connections_active",
    "Number of active WebSocket connections",
)

# Alert processing histogram
alert_processing_time = Histogram(
    "eriop_alert_processing_seconds",
    "Time spent processing alerts",
    ["source"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Incidents counter
incidents_total = Counter(
    "eriop_incidents_total",
    "Total number of incidents",
    ["category", "priority", "status"],
)

# Database pool gauge
db_pool_available = Gauge(
    "eriop_db_pool_available",
    "Number of available database connections in the pool",
)

# Redis connection gauge
redis_connected = Gauge(
    "eriop_redis_connected",
    "Whether the application is connected to Redis (1=connected, 0=disconnected)",
)


def setup_metrics(app) -> Instrumentator:
    """Set up Prometheus metrics instrumentation for FastAPI app."""
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/health/live", "/health/ready", "/metrics"],
        env_var_name="METRICS_ENABLED",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    # Add default metrics
    instrumentator.add(
        metrics.default(
            metric_namespace="",
            metric_subsystem="",
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            latency_highr_buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
    )

    # Add request size metric
    instrumentator.add(
        metrics.request_size(
            metric_namespace="",
            metric_subsystem="",
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )

    # Add response size metric
    instrumentator.add(
        metrics.response_size(
            metric_namespace="",
            metric_subsystem="",
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )

    # Instrument the app
    instrumentator.instrument(app)

    return instrumentator


def expose_metrics(app, instrumentator: Instrumentator) -> None:
    """Expose the /metrics endpoint."""
    instrumentator.expose(app, include_in_schema=False, should_gzip=True)


# Helper functions for updating custom metrics


def increment_websocket_connections() -> None:
    """Increment active WebSocket connections count."""
    websocket_connections.inc()


def decrement_websocket_connections() -> None:
    """Decrement active WebSocket connections count."""
    websocket_connections.dec()


def observe_alert_processing(source: str, duration: float) -> None:
    """Record alert processing duration."""
    alert_processing_time.labels(source=source).observe(duration)


def record_incident(category: str, priority: str, status: str) -> None:
    """Increment incident counter."""
    incidents_total.labels(category=category, priority=priority, status=status).inc()


def set_db_pool_available(count: int) -> None:
    """Set available database connections."""
    db_pool_available.set(count)


def set_redis_connected(connected: bool) -> None:
    """Set Redis connection status."""
    redis_connected.set(1 if connected else 0)

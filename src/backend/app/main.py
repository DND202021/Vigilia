"""ERIOP FastAPI Application Entry Point."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import router as api_router
from app.core.config import settings
from app.core.deps import async_session_factory, get_db, engine
from app.services.socketio import sio, create_combined_app
from app.services.fundamentum_mqtt import init_mqtt_client, shutdown_mqtt_client
from app.services.device_monitor_service import DeviceMonitorService
from app.services.sound_alert_pipeline import SoundAlertPipeline
from app.services.notification_service import NotificationService
from app.services.health_service import health_service

logger = structlog.get_logger()

# Module-level references for services that need lifecycle management
_device_monitor: DeviceMonitorService | None = None
_sound_pipeline: SoundAlertPipeline | None = None
_metrics_task: asyncio.Task | None = None


async def _update_health_metrics() -> None:
    """Background task to periodically update health metrics for Prometheus."""
    while True:
        try:
            async with async_session_factory() as session:
                await health_service.get_readiness(session, engine)
        except Exception as e:
            logger.warning("Failed to update health metrics", error=str(e))
        await asyncio.sleep(15)  # Update every 15 seconds


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    global _device_monitor, _sound_pipeline, _metrics_task

    # Startup
    logger.info("Starting ERIOP application", environment=settings.environment)

    # Start health metrics background task
    if settings.metrics_enabled:
        _metrics_task = asyncio.create_task(_update_health_metrics())
        logger.info("Health metrics background task started")

    # Initialize MQTT client for Fundamentum IoT integration
    if settings.mqtt_broker_host:
        try:
            loop = asyncio.get_event_loop()
            mqtt_client = init_mqtt_client(
                db_session_factory=async_session_factory,
                event_loop=loop,
            )
            if mqtt_client:
                logger.info(
                    "Fundamentum MQTT client initialized",
                    broker=settings.mqtt_broker_host,
                )
        except Exception as e:
            logger.warning("Failed to initialize MQTT client", error=str(e))

    # Initialize Device Monitor Service (background polling)
    try:
        _device_monitor = DeviceMonitorService(
            session_factory=async_session_factory,
            poll_interval=30.0,
            offline_threshold_seconds=120,
        )
        await _device_monitor.start()
        logger.info("Device monitor service started")
    except Exception as e:
        logger.warning("Failed to start device monitor service", error=str(e))

    # Initialize Notification Service and Sound Alert Pipeline
    try:
        notification_svc = NotificationService(session_factory=async_session_factory)
        _sound_pipeline = SoundAlertPipeline(
            session_factory=async_session_factory,
            auto_create_incidents=True,
            notification_service=notification_svc,
        )
        logger.info("Sound alert pipeline initialized with notification service")
    except Exception as e:
        logger.warning("Failed to initialize sound alert pipeline", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down ERIOP application")

    if _metrics_task:
        _metrics_task.cancel()
        try:
            await _metrics_task
        except asyncio.CancelledError:
            pass
        logger.info("Health metrics background task stopped")

    if _device_monitor:
        await _device_monitor.stop()
        logger.info("Device monitor service stopped")

    shutdown_mqtt_client()


fastapi_app = FastAPI(
    title="ERIOP API",
    description="Emergency Response IoT Platform - Tactical and Strategic Information System",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
fastapi_app.include_router(api_router, prefix="/api/v1")

# Add validation error logging
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@fastapi_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error("Validation error",
                 path=str(request.url.path),
                 errors=exc.errors(),
                 body=str(exc.body)[:500] if hasattr(exc, 'body') else None)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


# Set up Prometheus metrics instrumentation
_instrumentator = None
if settings.metrics_enabled:
    from app.core.metrics import setup_metrics, expose_metrics

    _instrumentator = setup_metrics(fastapi_app)
    expose_metrics(fastapi_app, _instrumentator)


@fastapi_app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for Kubernetes probes."""
    return {"status": "healthy", "version": "0.1.0"}


@fastapi_app.get("/health/live")
async def liveness_check() -> dict:
    """Liveness probe - checks if application is running."""
    result = health_service.get_liveness()
    return result.to_dict()


@fastapi_app.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness probe - checks if application can serve traffic."""
    result = await health_service.get_readiness(db, engine)
    return result.to_dict()


# Create combined ASGI app with Socket.IO wrapping FastAPI
# This is what gunicorn/uvicorn should serve
app = create_combined_app(fastapi_app)

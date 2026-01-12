"""ERIOP FastAPI Application Entry Point."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.core.config import settings
from app.core.deps import async_session_factory
from app.services.socketio import sio, create_combined_app
from app.services.fundamentum_mqtt import init_mqtt_client, shutdown_mqtt_client

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info("Starting ERIOP application", environment=settings.environment)

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

    yield

    # Shutdown
    logger.info("Shutting down ERIOP application")
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


@fastapi_app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for Kubernetes probes."""
    return {"status": "healthy", "version": "0.1.0"}


# Create combined ASGI app with Socket.IO wrapping FastAPI
# This is what gunicorn/uvicorn should serve
app = create_combined_app(fastapi_app)

"""ERIOP FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.core.config import settings
from app.services.socketio import sio, create_combined_app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    # TODO: Initialize database connections
    # TODO: Initialize Redis connection
    # TODO: Initialize MQTT client for Fundamentum
    yield
    # Shutdown
    # TODO: Close connections gracefully


fastapi_app = FastAPI(
    title="ERIOP API",
    description="Emergency Response IoT Platform - Tactical and Strategic Information System",
    version="0.1.0",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
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

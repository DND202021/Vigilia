"""API Routes Module."""

from fastapi import APIRouter

from app.api import auth, incidents, resources, alerts

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(incidents.router, prefix="/incidents", tags=["Incidents"])
router.include_router(resources.router, prefix="/resources", tags=["Resources"])
router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])

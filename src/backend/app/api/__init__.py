"""API Routes Module."""

from fastapi import APIRouter

from app.api import (
    auth,
    incidents,
    resources,
    alerts,
    dashboard,
    audit,
    communications,
    notifications,
    geospatial,
    alarm_receiver,
    devices,
    cad,
    gis,
    streaming,
    analytics,
    buildings,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(incidents.router, prefix="/incidents", tags=["Incidents"])
router.include_router(resources.router, prefix="/resources", tags=["Resources"])
router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
router.include_router(buildings.router, prefix="/buildings", tags=["Buildings"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(audit.router, prefix="/audit", tags=["Audit Logs"])
router.include_router(communications.router, prefix="/communications", tags=["Communications"])
router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
router.include_router(geospatial.router, prefix="/geospatial", tags=["Geospatial"])
router.include_router(alarm_receiver.router, prefix="/alarms", tags=["Alarm Receiver"])
router.include_router(devices.router, prefix="/devices", tags=["Devices"])
router.include_router(cad.router, prefix="/cad", tags=["CAD Integration"])
router.include_router(gis.router, prefix="/gis", tags=["GIS Layers"])
router.include_router(streaming.router, prefix="/streaming", tags=["Streaming & Recording"])
router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Reporting"])

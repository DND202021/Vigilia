"""Building Analytics Service for aggregating building-specific analytics data."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import IoTDevice, DeviceType, DeviceStatus
from app.models.incident import Incident, IncidentStatus, IncidentPriority, IncidentCategory
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.inspection import Inspection, InspectionStatus, InspectionType


class BuildingAnalyticsError(Exception):
    """Building analytics related errors."""
    pass


class BuildingAnalyticsService:
    """Service for aggregating building-specific analytics data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_building_overview(self, building_id: uuid.UUID) -> dict:
        """Get all analytics for a building in one call.

        Returns aggregated device health, incident stats, alert breakdown,
        and inspection compliance data.
        """
        device_health = await self.get_device_health(building_id)
        incident_stats = await self.get_incident_stats(building_id)
        alert_breakdown = await self.get_alert_breakdown(building_id)
        inspection_compliance = await self.get_inspection_compliance(building_id)

        return {
            "building_id": str(building_id),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "device_health": device_health,
            "incident_stats": incident_stats,
            "alert_breakdown": alert_breakdown,
            "inspection_compliance": inspection_compliance,
        }

    async def get_device_health(self, building_id: uuid.UUID) -> dict:
        """Get device status distribution.

        Returns:
            {
                total: int,
                by_status: {online: int, offline: int, alert: int, maintenance: int, error: int},
                by_type: {microphone: int, camera: int, sensor: int, gateway: int, other: int},
                health_percentage: float  # online / total * 100
            }
        """
        # Get total count
        total_query = select(func.count(IoTDevice.id)).where(
            and_(
                IoTDevice.building_id == building_id,
                IoTDevice.deleted_at.is_(None),
            )
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # Get counts by status
        status_query = (
            select(IoTDevice.status, func.count(IoTDevice.id).label("count"))
            .where(
                and_(
                    IoTDevice.building_id == building_id,
                    IoTDevice.deleted_at.is_(None),
                )
            )
            .group_by(IoTDevice.status)
        )
        status_result = await self.db.execute(status_query)
        status_rows = status_result.all()

        # Initialize with all statuses at 0
        by_status = {
            DeviceStatus.ONLINE.value: 0,
            DeviceStatus.OFFLINE.value: 0,
            DeviceStatus.ALERT.value: 0,
            DeviceStatus.MAINTENANCE.value: 0,
            DeviceStatus.ERROR.value: 0,
        }
        for row in status_rows:
            status_val = row[0]
            if status_val in by_status:
                by_status[status_val] = row[1]

        # Get counts by type
        type_query = (
            select(IoTDevice.device_type, func.count(IoTDevice.id).label("count"))
            .where(
                and_(
                    IoTDevice.building_id == building_id,
                    IoTDevice.deleted_at.is_(None),
                )
            )
            .group_by(IoTDevice.device_type)
        )
        type_result = await self.db.execute(type_query)
        type_rows = type_result.all()

        # Initialize with all types at 0
        by_type = {
            DeviceType.MICROPHONE.value: 0,
            DeviceType.CAMERA.value: 0,
            DeviceType.SENSOR.value: 0,
            DeviceType.GATEWAY.value: 0,
            DeviceType.OTHER.value: 0,
        }
        for row in type_rows:
            type_val = row[0]
            if type_val in by_type:
                by_type[type_val] = row[1]

        # Calculate health percentage
        health_percentage = 0.0
        if total > 0:
            health_percentage = (by_status[DeviceStatus.ONLINE.value] / total) * 100

        return {
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "health_percentage": round(health_percentage, 2),
        }

    async def get_incident_stats(
        self, building_id: uuid.UUID, days: int = 30
    ) -> dict:
        """Get incident statistics.

        Returns:
            {
                total: int,
                by_status: {new: int, assigned: int, en_route: int, on_scene: int, resolved: int, closed: int},
                by_category: {fire: int, medical: int, ...},
                by_priority: {critical: int, high: int, medium: int, low: int, minimal: int},
                trend: [{date: str, count: int}, ...]  # daily counts
            }
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Get total count within date range
        total_query = select(func.count(Incident.id)).where(
            and_(
                Incident.building_id == building_id,
                Incident.created_at >= cutoff_date,
            )
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # Get counts by status
        status_query = (
            select(Incident.status, func.count(Incident.id).label("count"))
            .where(
                and_(
                    Incident.building_id == building_id,
                    Incident.created_at >= cutoff_date,
                )
            )
            .group_by(Incident.status)
        )
        status_result = await self.db.execute(status_query)
        status_rows = status_result.all()

        # Initialize with all statuses at 0
        by_status = {
            IncidentStatus.NEW.value: 0,
            IncidentStatus.ASSIGNED.value: 0,
            IncidentStatus.EN_ROUTE.value: 0,
            IncidentStatus.ON_SCENE.value: 0,
            IncidentStatus.RESOLVED.value: 0,
            IncidentStatus.CLOSED.value: 0,
        }
        for row in status_rows:
            status_val = row[0].value if hasattr(row[0], 'value') else row[0]
            if status_val in by_status:
                by_status[status_val] = row[1]

        # Get counts by category
        category_query = (
            select(Incident.category, func.count(Incident.id).label("count"))
            .where(
                and_(
                    Incident.building_id == building_id,
                    Incident.created_at >= cutoff_date,
                )
            )
            .group_by(Incident.category)
        )
        category_result = await self.db.execute(category_query)
        category_rows = category_result.all()

        # Initialize with all categories at 0
        by_category = {cat.value: 0 for cat in IncidentCategory}
        for row in category_rows:
            cat_val = row[0].value if hasattr(row[0], 'value') else row[0]
            if cat_val in by_category:
                by_category[cat_val] = row[1]

        # Get counts by priority
        priority_query = (
            select(Incident.priority, func.count(Incident.id).label("count"))
            .where(
                and_(
                    Incident.building_id == building_id,
                    Incident.created_at >= cutoff_date,
                )
            )
            .group_by(Incident.priority)
        )
        priority_result = await self.db.execute(priority_query)
        priority_rows = priority_result.all()

        # Map priority values to names
        priority_names = {
            IncidentPriority.CRITICAL.value: "critical",
            IncidentPriority.HIGH.value: "high",
            IncidentPriority.MEDIUM.value: "medium",
            IncidentPriority.LOW.value: "low",
            IncidentPriority.MINIMAL.value: "minimal",
        }
        by_priority = {name: 0 for name in priority_names.values()}
        for row in priority_rows:
            priority_val = row[0]
            if priority_val in priority_names:
                by_priority[priority_names[priority_val]] = row[1]

        # Get daily trend
        trend_query = (
            select(
                func.date(Incident.created_at).label("date"),
                func.count(Incident.id).label("count"),
            )
            .where(
                and_(
                    Incident.building_id == building_id,
                    Incident.created_at >= cutoff_date,
                )
            )
            .group_by(func.date(Incident.created_at))
            .order_by(func.date(Incident.created_at))
        )
        trend_result = await self.db.execute(trend_query)
        trend_rows = trend_result.all()

        trend = [
            {"date": str(row[0]), "count": row[1]}
            for row in trend_rows
        ]

        return {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "by_priority": by_priority,
            "trend": trend,
        }

    async def get_alert_breakdown(
        self, building_id: uuid.UUID, days: int = 30
    ) -> dict:
        """Get alert breakdown by severity and status.

        Returns:
            {
                total: int,
                pending: int,
                by_severity: {critical: int, high: int, medium: int, low: int, info: int},
                by_status: {pending: int, acknowledged: int, resolved: int, dismissed: int},
                recent: [{id, severity, created_at, title}, ...]  # last 5 alerts
            }
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Get total count within date range
        total_query = select(func.count(Alert.id)).where(
            and_(
                Alert.building_id == building_id,
                Alert.created_at >= cutoff_date,
            )
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # Get pending count
        pending_query = select(func.count(Alert.id)).where(
            and_(
                Alert.building_id == building_id,
                Alert.status == AlertStatus.PENDING,
                Alert.created_at >= cutoff_date,
            )
        )
        pending_result = await self.db.execute(pending_query)
        pending = pending_result.scalar() or 0

        # Get counts by severity
        severity_query = (
            select(Alert.severity, func.count(Alert.id).label("count"))
            .where(
                and_(
                    Alert.building_id == building_id,
                    Alert.created_at >= cutoff_date,
                )
            )
            .group_by(Alert.severity)
        )
        severity_result = await self.db.execute(severity_query)
        severity_rows = severity_result.all()

        # Initialize with all severities at 0
        by_severity = {
            AlertSeverity.CRITICAL.value: 0,
            AlertSeverity.HIGH.value: 0,
            AlertSeverity.MEDIUM.value: 0,
            AlertSeverity.LOW.value: 0,
            AlertSeverity.INFO.value: 0,
        }
        for row in severity_rows:
            sev_val = row[0].value if hasattr(row[0], 'value') else row[0]
            if sev_val in by_severity:
                by_severity[sev_val] = row[1]

        # Get counts by status
        status_query = (
            select(Alert.status, func.count(Alert.id).label("count"))
            .where(
                and_(
                    Alert.building_id == building_id,
                    Alert.created_at >= cutoff_date,
                )
            )
            .group_by(Alert.status)
        )
        status_result = await self.db.execute(status_query)
        status_rows = status_result.all()

        # Initialize with relevant statuses at 0
        by_status = {
            AlertStatus.PENDING.value: 0,
            AlertStatus.ACKNOWLEDGED.value: 0,
            AlertStatus.RESOLVED.value: 0,
            AlertStatus.DISMISSED.value: 0,
        }
        for row in status_rows:
            status_val = row[0].value if hasattr(row[0], 'value') else row[0]
            if status_val in by_status:
                by_status[status_val] = row[1]

        # Get recent alerts (last 5)
        recent_query = (
            select(Alert.id, Alert.severity, Alert.created_at, Alert.title)
            .where(
                and_(
                    Alert.building_id == building_id,
                    Alert.created_at >= cutoff_date,
                )
            )
            .order_by(Alert.created_at.desc())
            .limit(5)
        )
        recent_result = await self.db.execute(recent_query)
        recent_rows = recent_result.all()

        recent = [
            {
                "id": str(row[0]),
                "severity": row[1].value if hasattr(row[1], 'value') else row[1],
                "created_at": row[2].isoformat() if row[2] else None,
                "title": row[3],
            }
            for row in recent_rows
        ]

        return {
            "total": total,
            "pending": pending,
            "by_severity": by_severity,
            "by_status": by_status,
            "recent": recent,
        }

    async def get_inspection_compliance(self, building_id: uuid.UUID) -> dict:
        """Get inspection compliance metrics.

        Returns:
            {
                total: int,
                completed: int,
                scheduled: int,
                overdue: int,
                compliance_rate: float,  # completed / (completed + overdue) * 100
                upcoming: [{id, type, scheduled_date}, ...],  # next 5
                overdue_list: [{id, type, scheduled_date}, ...]  # all overdue
            }
        """
        today = datetime.now(timezone.utc).date()

        # Get total count
        total_query = select(func.count(Inspection.id)).where(
            Inspection.building_id == building_id
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # Get completed count
        # Use literal string for PostgreSQL enum comparison
        completed_query = select(func.count(Inspection.id)).where(
            and_(
                Inspection.building_id == building_id,
                Inspection.status == "completed",
            )
        )
        completed_result = await self.db.execute(completed_query)
        completed = completed_result.scalar() or 0

        # Get scheduled count (future, not overdue)
        scheduled_query = select(func.count(Inspection.id)).where(
            and_(
                Inspection.building_id == building_id,
                Inspection.status == "scheduled",
                Inspection.scheduled_date >= today,
            )
        )
        scheduled_result = await self.db.execute(scheduled_query)
        scheduled = scheduled_result.scalar() or 0

        # Get overdue count
        overdue_query = select(func.count(Inspection.id)).where(
            and_(
                Inspection.building_id == building_id,
                Inspection.status.in_(["scheduled", "overdue"]),
                Inspection.scheduled_date < today,
            )
        )
        overdue_result = await self.db.execute(overdue_query)
        overdue = overdue_result.scalar() or 0

        # Calculate compliance rate
        compliance_rate = 0.0
        if (completed + overdue) > 0:
            compliance_rate = (completed / (completed + overdue)) * 100

        # Get upcoming inspections (next 5)
        upcoming_query = (
            select(Inspection.id, Inspection.inspection_type, Inspection.scheduled_date)
            .where(
                and_(
                    Inspection.building_id == building_id,
                    Inspection.status == "scheduled",
                    Inspection.scheduled_date >= today,
                )
            )
            .order_by(Inspection.scheduled_date)
            .limit(5)
        )
        upcoming_result = await self.db.execute(upcoming_query)
        upcoming_rows = upcoming_result.all()

        upcoming = [
            {
                "id": str(row[0]),
                "type": row[1].value if hasattr(row[1], 'value') else row[1],
                "scheduled_date": str(row[2]) if row[2] else None,
            }
            for row in upcoming_rows
        ]

        # Get all overdue inspections
        overdue_list_query = (
            select(Inspection.id, Inspection.inspection_type, Inspection.scheduled_date)
            .where(
                and_(
                    Inspection.building_id == building_id,
                    Inspection.status.in_(["scheduled", "overdue"]),
                    Inspection.scheduled_date < today,
                )
            )
            .order_by(Inspection.scheduled_date)
        )
        overdue_list_result = await self.db.execute(overdue_list_query)
        overdue_list_rows = overdue_list_result.all()

        overdue_list = [
            {
                "id": str(row[0]),
                "type": row[1].value if hasattr(row[1], 'value') else row[1],
                "scheduled_date": str(row[2]) if row[2] else None,
            }
            for row in overdue_list_rows
        ]

        return {
            "total": total,
            "completed": completed,
            "scheduled": scheduled,
            "overdue": overdue,
            "compliance_rate": round(compliance_rate, 2),
            "upcoming": upcoming,
            "overdue_list": overdue_list,
        }

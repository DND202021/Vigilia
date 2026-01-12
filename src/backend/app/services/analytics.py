"""Analytics and Reporting Service.

This service provides analytics, metrics, and reporting capabilities:
- Incident statistics and trends
- Response time analysis
- Resource utilization metrics
- Performance dashboards
- Custom report generation
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from collections import defaultdict

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentStatus, IncidentCategory
from app.models.resource import Resource, ResourceStatus, ResourceType
from app.models.alert import Alert, AlertStatus, AlertSeverity


class TimeRange(str, Enum):
    """Time range for analytics."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"


class MetricType(str, Enum):
    """Metric types."""

    COUNT = "count"
    AVERAGE = "average"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    PERCENTAGE = "percentage"


@dataclass
class TimeSeriesPoint:
    """Single point in time series data."""

    timestamp: datetime
    value: float
    label: str | None = None


@dataclass
class TimeSeries:
    """Time series data."""

    name: str
    metric_type: MetricType
    unit: str
    points: list[TimeSeriesPoint] = field(default_factory=list)

    def add_point(self, timestamp: datetime, value: float, label: str | None = None) -> None:
        """Add a data point."""
        self.points.append(TimeSeriesPoint(timestamp=timestamp, value=value, label=label))


@dataclass
class IncidentStats:
    """Incident statistics."""

    total: int = 0
    open: int = 0
    closed: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    by_priority: dict[int, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    avg_resolution_minutes: float = 0
    avg_response_minutes: float = 0


@dataclass
class ResourceStats:
    """Resource statistics."""

    total: int = 0
    available: int = 0
    dispatched: int = 0
    on_scene: int = 0
    out_of_service: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    utilization_rate: float = 0


@dataclass
class AlertStats:
    """Alert statistics."""

    total: int = 0
    pending: int = 0
    acknowledged: int = 0
    resolved: int = 0
    by_severity: dict[str, int] = field(default_factory=dict)
    avg_acknowledgment_minutes: float = 0


@dataclass
class DashboardSummary:
    """Dashboard summary data."""

    period_start: datetime
    period_end: datetime
    incidents: IncidentStats = field(default_factory=IncidentStats)
    resources: ResourceStats = field(default_factory=ResourceStats)
    alerts: AlertStats = field(default_factory=AlertStats)
    key_metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class Report:
    """Generated report."""

    id: uuid.UUID
    title: str
    report_type: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime = field(default_factory=datetime.utcnow)
    generated_by: uuid.UUID | None = None
    data: dict[str, Any] = field(default_factory=dict)
    charts: list[dict] = field(default_factory=list)


class AnalyticsService:
    """Service for analytics and reporting."""

    def __init__(self, db: AsyncSession):
        """Initialize analytics service."""
        self.db = db

    def _get_time_range(
        self,
        time_range: TimeRange,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[datetime, datetime]:
        """Calculate time range boundaries."""
        now = datetime.utcnow()

        if time_range == TimeRange.CUSTOM:
            return (
                start_date or now - timedelta(days=30),
                end_date or now,
            )

        range_map = {
            TimeRange.HOUR: timedelta(hours=1),
            TimeRange.DAY: timedelta(days=1),
            TimeRange.WEEK: timedelta(weeks=1),
            TimeRange.MONTH: timedelta(days=30),
            TimeRange.QUARTER: timedelta(days=90),
            TimeRange.YEAR: timedelta(days=365),
        }

        delta = range_map.get(time_range, timedelta(days=1))
        return (now - delta, now)

    async def get_incident_stats(
        self,
        time_range: TimeRange = TimeRange.DAY,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        agency_id: uuid.UUID | None = None,
    ) -> IncidentStats:
        """Get incident statistics.

        Args:
            time_range: Time range for stats
            start_date: Custom start date
            end_date: Custom end date
            agency_id: Filter by agency

        Returns:
            Incident statistics
        """
        start, end = self._get_time_range(time_range, start_date, end_date)

        # Base query
        base_filter = [
            Incident.created_at >= start,
            Incident.created_at <= end,
        ]
        if agency_id:
            base_filter.append(Incident.agency_id == agency_id)

        # Total count
        total_query = select(func.count(Incident.id)).where(and_(*base_filter))
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # By status
        status_query = select(
            Incident.status,
            func.count(Incident.id)
        ).where(and_(*base_filter)).group_by(Incident.status)
        status_result = await self.db.execute(status_query)
        by_status = {str(row[0].value): row[1] for row in status_result}

        # By category
        category_query = select(
            Incident.category,
            func.count(Incident.id)
        ).where(and_(*base_filter)).group_by(Incident.category)
        category_result = await self.db.execute(category_query)
        by_category = {str(row[0].value): row[1] for row in category_result}

        # By priority
        priority_query = select(
            Incident.priority,
            func.count(Incident.id)
        ).where(and_(*base_filter)).group_by(Incident.priority)
        priority_result = await self.db.execute(priority_query)
        by_priority = {row[0]: row[1] for row in priority_result}

        # Calculate open/closed
        open_statuses = [IncidentStatus.NEW, IncidentStatus.ASSIGNED, IncidentStatus.EN_ROUTE, IncidentStatus.ON_SCENE]
        open_count = sum(by_status.get(s.value, 0) for s in open_statuses)
        closed_count = by_status.get(IncidentStatus.CLOSED.value, 0) + by_status.get(IncidentStatus.RESOLVED.value, 0)

        # Average resolution time (for closed incidents)
        # This is simplified - real implementation would calculate from timeline events
        avg_resolution = 0.0

        return IncidentStats(
            total=total,
            open=open_count,
            closed=closed_count,
            by_category=by_category,
            by_priority=by_priority,
            by_status=by_status,
            avg_resolution_minutes=avg_resolution,
            avg_response_minutes=0.0,
        )

    async def get_resource_stats(
        self,
        agency_id: uuid.UUID | None = None,
    ) -> ResourceStats:
        """Get resource statistics.

        Args:
            agency_id: Filter by agency

        Returns:
            Resource statistics
        """
        # Base filter
        base_filter = [Resource.deleted_at.is_(None)]
        if agency_id:
            base_filter.append(Resource.agency_id == agency_id)

        # Total count
        total_query = select(func.count(Resource.id)).where(and_(*base_filter))
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # By status
        status_query = select(
            Resource.status,
            func.count(Resource.id)
        ).where(and_(*base_filter)).group_by(Resource.status)
        status_result = await self.db.execute(status_query)
        status_counts = {row[0]: row[1] for row in status_result}

        # By type
        type_query = select(
            Resource.resource_type,
            func.count(Resource.id)
        ).where(and_(*base_filter)).group_by(Resource.resource_type)
        type_result = await self.db.execute(type_query)
        by_type = {str(row[0].value): row[1] for row in type_result}

        # Calculate utilization
        active_count = (
            status_counts.get(ResourceStatus.DISPATCHED, 0) +
            status_counts.get(ResourceStatus.ON_SCENE, 0) +
            status_counts.get(ResourceStatus.BUSY, 0)
        )
        utilization = (active_count / total * 100) if total > 0 else 0

        return ResourceStats(
            total=total,
            available=status_counts.get(ResourceStatus.AVAILABLE, 0),
            dispatched=status_counts.get(ResourceStatus.DISPATCHED, 0),
            on_scene=status_counts.get(ResourceStatus.ON_SCENE, 0),
            out_of_service=status_counts.get(ResourceStatus.OUT_OF_SERVICE, 0),
            by_type=by_type,
            utilization_rate=round(utilization, 2),
        )

    async def get_alert_stats(
        self,
        time_range: TimeRange = TimeRange.DAY,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AlertStats:
        """Get alert statistics."""
        start, end = self._get_time_range(time_range, start_date, end_date)

        base_filter = [
            Alert.created_at >= start,
            Alert.created_at <= end,
        ]

        # Total count
        total_query = select(func.count(Alert.id)).where(and_(*base_filter))
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # By status
        status_query = select(
            Alert.status,
            func.count(Alert.id)
        ).where(and_(*base_filter)).group_by(Alert.status)
        status_result = await self.db.execute(status_query)
        status_counts = {row[0]: row[1] for row in status_result}

        # By severity
        severity_query = select(
            Alert.severity,
            func.count(Alert.id)
        ).where(and_(*base_filter)).group_by(Alert.severity)
        severity_result = await self.db.execute(severity_query)
        by_severity = {str(row[0].value): row[1] for row in severity_result}

        return AlertStats(
            total=total,
            pending=status_counts.get(AlertStatus.PENDING, 0),
            acknowledged=status_counts.get(AlertStatus.ACKNOWLEDGED, 0),
            resolved=status_counts.get(AlertStatus.RESOLVED, 0),
            by_severity=by_severity,
            avg_acknowledgment_minutes=0.0,
        )

    async def get_dashboard_summary(
        self,
        time_range: TimeRange = TimeRange.DAY,
        agency_id: uuid.UUID | None = None,
    ) -> DashboardSummary:
        """Get dashboard summary data.

        Args:
            time_range: Time range for summary
            agency_id: Filter by agency

        Returns:
            Dashboard summary
        """
        start, end = self._get_time_range(time_range)

        incidents = await self.get_incident_stats(time_range, agency_id=agency_id)
        resources = await self.get_resource_stats(agency_id)
        alerts = await self.get_alert_stats(time_range)

        # Calculate key metrics
        key_metrics = {
            "incident_rate": incidents.total / max(1, (end - start).total_seconds() / 3600),  # per hour
            "resource_utilization": resources.utilization_rate,
            "alert_pending_ratio": (alerts.pending / alerts.total * 100) if alerts.total > 0 else 0,
            "high_priority_incidents": incidents.by_priority.get(1, 0) + incidents.by_priority.get(2, 0),
        }

        return DashboardSummary(
            period_start=start,
            period_end=end,
            incidents=incidents,
            resources=resources,
            alerts=alerts,
            key_metrics=key_metrics,
        )

    async def get_incident_trend(
        self,
        time_range: TimeRange = TimeRange.WEEK,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        granularity: str = "day",
    ) -> TimeSeries:
        """Get incident count trend over time.

        Args:
            time_range: Time range
            start_date: Custom start date
            end_date: Custom end date
            granularity: Data granularity (hour, day, week)

        Returns:
            Time series data
        """
        start, end = self._get_time_range(time_range, start_date, end_date)

        # Determine time buckets
        if granularity == "hour":
            delta = timedelta(hours=1)
        elif granularity == "week":
            delta = timedelta(weeks=1)
        else:
            delta = timedelta(days=1)

        series = TimeSeries(
            name="Incident Count",
            metric_type=MetricType.COUNT,
            unit="incidents",
        )

        current = start
        while current < end:
            next_time = current + delta

            query = select(func.count(Incident.id)).where(
                and_(
                    Incident.created_at >= current,
                    Incident.created_at < next_time,
                )
            )
            result = await self.db.execute(query)
            count = result.scalar() or 0

            series.add_point(current, float(count))
            current = next_time

        return series

    async def get_response_time_trend(
        self,
        time_range: TimeRange = TimeRange.WEEK,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> TimeSeries:
        """Get average response time trend.

        Note: This is a simplified implementation. Real implementation
        would track response times from incident timeline events.
        """
        start, end = self._get_time_range(time_range, start_date, end_date)

        series = TimeSeries(
            name="Average Response Time",
            metric_type=MetricType.AVERAGE,
            unit="minutes",
        )

        # Simplified - generate sample data points
        current = start
        delta = timedelta(days=1)

        while current < end:
            # Placeholder - would calculate actual response times
            series.add_point(current, 0.0)
            current += delta

        return series

    async def get_category_distribution(
        self,
        time_range: TimeRange = TimeRange.MONTH,
    ) -> dict[str, int]:
        """Get incident distribution by category."""
        start, end = self._get_time_range(time_range)

        query = select(
            Incident.category,
            func.count(Incident.id)
        ).where(
            and_(
                Incident.created_at >= start,
                Incident.created_at <= end,
            )
        ).group_by(Incident.category)

        result = await self.db.execute(query)

        return {str(row[0].value): row[1] for row in result}

    async def generate_report(
        self,
        report_type: str,
        time_range: TimeRange,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: uuid.UUID | None = None,
        options: dict | None = None,
    ) -> Report:
        """Generate a report.

        Args:
            report_type: Type of report (summary, incidents, resources, performance)
            time_range: Time range for report
            start_date: Custom start date
            end_date: Custom end date
            user_id: User generating report
            options: Additional report options

        Returns:
            Generated report
        """
        start, end = self._get_time_range(time_range, start_date, end_date)
        options = options or {}

        report = Report(
            id=uuid.uuid4(),
            title=f"{report_type.title()} Report",
            report_type=report_type,
            period_start=start,
            period_end=end,
            generated_by=user_id,
        )

        if report_type == "summary":
            summary = await self.get_dashboard_summary(time_range)
            report.data = {
                "incidents": {
                    "total": summary.incidents.total,
                    "open": summary.incidents.open,
                    "closed": summary.incidents.closed,
                    "by_category": summary.incidents.by_category,
                    "by_priority": summary.incidents.by_priority,
                },
                "resources": {
                    "total": summary.resources.total,
                    "available": summary.resources.available,
                    "utilization_rate": summary.resources.utilization_rate,
                    "by_type": summary.resources.by_type,
                },
                "alerts": {
                    "total": summary.alerts.total,
                    "pending": summary.alerts.pending,
                    "by_severity": summary.alerts.by_severity,
                },
                "key_metrics": summary.key_metrics,
            }

            # Add charts
            trend = await self.get_incident_trend(time_range)
            report.charts.append({
                "type": "line",
                "title": "Incident Trend",
                "data": [
                    {"x": p.timestamp.isoformat(), "y": p.value}
                    for p in trend.points
                ],
            })

            category_dist = await self.get_category_distribution(time_range)
            report.charts.append({
                "type": "pie",
                "title": "Incidents by Category",
                "data": [
                    {"label": k, "value": v}
                    for k, v in category_dist.items()
                ],
            })

        elif report_type == "incidents":
            stats = await self.get_incident_stats(time_range, start_date, end_date)
            report.data = {
                "statistics": {
                    "total": stats.total,
                    "open": stats.open,
                    "closed": stats.closed,
                    "avg_resolution_minutes": stats.avg_resolution_minutes,
                },
                "breakdown": {
                    "by_category": stats.by_category,
                    "by_priority": stats.by_priority,
                    "by_status": stats.by_status,
                },
            }

        elif report_type == "resources":
            stats = await self.get_resource_stats()
            report.data = {
                "statistics": {
                    "total": stats.total,
                    "available": stats.available,
                    "utilization_rate": stats.utilization_rate,
                },
                "breakdown": {
                    "by_type": stats.by_type,
                    "by_status": {
                        "available": stats.available,
                        "dispatched": stats.dispatched,
                        "on_scene": stats.on_scene,
                        "out_of_service": stats.out_of_service,
                    },
                },
            }

        elif report_type == "performance":
            summary = await self.get_dashboard_summary(time_range)
            report.data = {
                "metrics": summary.key_metrics,
                "incidents": {
                    "avg_response_time": summary.incidents.avg_response_minutes,
                    "avg_resolution_time": summary.incidents.avg_resolution_minutes,
                },
                "resources": {
                    "utilization_rate": summary.resources.utilization_rate,
                },
            }

        return report


class MetricsCollector:
    """Collects and stores performance metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self._metrics: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        self._counters[name] += value

    def gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""
        self._gauges[name] = value

    def record(self, name: str, value: float) -> None:
        """Record a metric value with timestamp."""
        self._metrics[name].append((datetime.utcnow(), value))

        # Keep only last 1000 values per metric
        if len(self._metrics[name]) > 1000:
            self._metrics[name] = self._metrics[name][-1000:]

    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float | None:
        """Get gauge value."""
        return self._gauges.get(name)

    def get_metrics(self, name: str, since: datetime | None = None) -> list[tuple[datetime, float]]:
        """Get recorded metrics."""
        metrics = self._metrics.get(name, [])
        if since:
            metrics = [(t, v) for t, v in metrics if t >= since]
        return metrics

    def get_summary(self) -> dict:
        """Get summary of all metrics."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "recorded_metrics": list(self._metrics.keys()),
        }

    def reset_counters(self) -> None:
        """Reset all counters."""
        self._counters.clear()


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector."""
    return _metrics_collector

"""Analytics and Reporting API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user, require_permission, Permission
from app.models.user import User
from app.services.analytics import (
    AnalyticsService,
    TimeRange,
    DashboardSummary,
    IncidentStats,
    ResourceStats,
    AlertStats,
    TimeSeries,
    Report,
    get_metrics_collector,
    MetricsCollector,
)

router = APIRouter()


def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    """Get analytics service instance."""
    return AnalyticsService(db)


# Response Models
class IncidentStatsResponse(BaseModel):
    """Incident statistics response."""

    total: int
    open: int
    closed: int
    by_category: dict[str, int]
    by_priority: dict[int, int]
    by_status: dict[str, int]
    avg_resolution_minutes: float
    avg_response_minutes: float


class ResourceStatsResponse(BaseModel):
    """Resource statistics response."""

    total: int
    available: int
    dispatched: int
    on_scene: int
    out_of_service: int
    by_type: dict[str, int]
    utilization_rate: float


class AlertStatsResponse(BaseModel):
    """Alert statistics response."""

    total: int
    pending: int
    acknowledged: int
    resolved: int
    by_severity: dict[str, int]
    avg_acknowledgment_minutes: float


class DashboardSummaryResponse(BaseModel):
    """Dashboard summary response."""

    period_start: datetime
    period_end: datetime
    incidents: IncidentStatsResponse
    resources: ResourceStatsResponse
    alerts: AlertStatsResponse
    key_metrics: dict[str, float]


class TimeSeriesPointResponse(BaseModel):
    """Time series point response."""

    timestamp: datetime
    value: float
    label: str | None = None


class TimeSeriesResponse(BaseModel):
    """Time series response."""

    name: str
    metric_type: str
    unit: str
    points: list[TimeSeriesPointResponse]


class ReportResponse(BaseModel):
    """Report response."""

    id: str
    title: str
    report_type: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    generated_by: str | None
    data: dict
    charts: list[dict]


class GenerateReportRequest(BaseModel):
    """Generate report request."""

    report_type: str = Field(..., description="Report type: summary, incidents, resources, performance")
    time_range: str = Field("week", description="Time range: hour, day, week, month, quarter, year")
    start_date: datetime | None = None
    end_date: datetime | None = None
    options: dict | None = None


class MetricsSummaryResponse(BaseModel):
    """Metrics summary response."""

    counters: dict[str, int]
    gauges: dict[str, float]
    recorded_metrics: list[str]


# Dashboard Endpoints
@router.get("/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    time_range: str = Query("day", description="Time range: hour, day, week, month, quarter, year"),
    agency_id: str | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
) -> DashboardSummaryResponse:
    """Get dashboard summary data."""
    try:
        tr = TimeRange(time_range.lower())
    except ValueError:
        tr = TimeRange.DAY

    agency_uuid = None
    if agency_id:
        try:
            agency_uuid = uuid.UUID(agency_id)
        except ValueError:
            pass

    summary = await service.get_dashboard_summary(tr, agency_uuid)

    return DashboardSummaryResponse(
        period_start=summary.period_start,
        period_end=summary.period_end,
        incidents=IncidentStatsResponse(
            total=summary.incidents.total,
            open=summary.incidents.open,
            closed=summary.incidents.closed,
            by_category=summary.incidents.by_category,
            by_priority=summary.incidents.by_priority,
            by_status=summary.incidents.by_status,
            avg_resolution_minutes=summary.incidents.avg_resolution_minutes,
            avg_response_minutes=summary.incidents.avg_response_minutes,
        ),
        resources=ResourceStatsResponse(
            total=summary.resources.total,
            available=summary.resources.available,
            dispatched=summary.resources.dispatched,
            on_scene=summary.resources.on_scene,
            out_of_service=summary.resources.out_of_service,
            by_type=summary.resources.by_type,
            utilization_rate=summary.resources.utilization_rate,
        ),
        alerts=AlertStatsResponse(
            total=summary.alerts.total,
            pending=summary.alerts.pending,
            acknowledged=summary.alerts.acknowledged,
            resolved=summary.alerts.resolved,
            by_severity=summary.alerts.by_severity,
            avg_acknowledgment_minutes=summary.alerts.avg_acknowledgment_minutes,
        ),
        key_metrics=summary.key_metrics,
    )


# Statistics Endpoints
@router.get("/incidents/stats", response_model=IncidentStatsResponse)
async def get_incident_stats(
    time_range: str = Query("day"),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    agency_id: str | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
) -> IncidentStatsResponse:
    """Get incident statistics."""
    try:
        tr = TimeRange(time_range.lower())
    except ValueError:
        tr = TimeRange.DAY

    agency_uuid = None
    if agency_id:
        try:
            agency_uuid = uuid.UUID(agency_id)
        except ValueError:
            pass

    stats = await service.get_incident_stats(tr, start_date, end_date, agency_uuid)

    return IncidentStatsResponse(
        total=stats.total,
        open=stats.open,
        closed=stats.closed,
        by_category=stats.by_category,
        by_priority=stats.by_priority,
        by_status=stats.by_status,
        avg_resolution_minutes=stats.avg_resolution_minutes,
        avg_response_minutes=stats.avg_response_minutes,
    )


@router.get("/resources/stats", response_model=ResourceStatsResponse)
async def get_resource_stats(
    agency_id: str | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
) -> ResourceStatsResponse:
    """Get resource statistics."""
    agency_uuid = None
    if agency_id:
        try:
            agency_uuid = uuid.UUID(agency_id)
        except ValueError:
            pass

    stats = await service.get_resource_stats(agency_uuid)

    return ResourceStatsResponse(
        total=stats.total,
        available=stats.available,
        dispatched=stats.dispatched,
        on_scene=stats.on_scene,
        out_of_service=stats.out_of_service,
        by_type=stats.by_type,
        utilization_rate=stats.utilization_rate,
    )


@router.get("/alerts/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    time_range: str = Query("day"),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
) -> AlertStatsResponse:
    """Get alert statistics."""
    try:
        tr = TimeRange(time_range.lower())
    except ValueError:
        tr = TimeRange.DAY

    stats = await service.get_alert_stats(tr, start_date, end_date)

    return AlertStatsResponse(
        total=stats.total,
        pending=stats.pending,
        acknowledged=stats.acknowledged,
        resolved=stats.resolved,
        by_severity=stats.by_severity,
        avg_acknowledgment_minutes=stats.avg_acknowledgment_minutes,
    )


# Trend Endpoints
@router.get("/incidents/trend", response_model=TimeSeriesResponse)
async def get_incident_trend(
    time_range: str = Query("week"),
    granularity: str = Query("day", description="Granularity: hour, day, week"),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
) -> TimeSeriesResponse:
    """Get incident count trend over time."""
    try:
        tr = TimeRange(time_range.lower())
    except ValueError:
        tr = TimeRange.WEEK

    series = await service.get_incident_trend(tr, start_date, end_date, granularity)

    return TimeSeriesResponse(
        name=series.name,
        metric_type=series.metric_type.value,
        unit=series.unit,
        points=[
            TimeSeriesPointResponse(
                timestamp=p.timestamp,
                value=p.value,
                label=p.label,
            )
            for p in series.points
        ],
    )


@router.get("/response-time/trend", response_model=TimeSeriesResponse)
async def get_response_time_trend(
    time_range: str = Query("week"),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
) -> TimeSeriesResponse:
    """Get response time trend."""
    try:
        tr = TimeRange(time_range.lower())
    except ValueError:
        tr = TimeRange.WEEK

    series = await service.get_response_time_trend(tr, start_date, end_date)

    return TimeSeriesResponse(
        name=series.name,
        metric_type=series.metric_type.value,
        unit=series.unit,
        points=[
            TimeSeriesPointResponse(
                timestamp=p.timestamp,
                value=p.value,
                label=p.label,
            )
            for p in series.points
        ],
    )


@router.get("/incidents/distribution")
async def get_category_distribution(
    time_range: str = Query("month"),
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get incident distribution by category."""
    try:
        tr = TimeRange(time_range.lower())
    except ValueError:
        tr = TimeRange.MONTH

    distribution = await service.get_category_distribution(tr)

    return {
        "time_range": tr.value,
        "distribution": distribution,
        "total": sum(distribution.values()),
    }


# Report Endpoints
@router.post("/reports", response_model=ReportResponse)
async def generate_report(
    request: GenerateReportRequest,
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_active_user),
) -> ReportResponse:
    """Generate a report."""
    try:
        tr = TimeRange(request.time_range.lower())
    except ValueError:
        tr = TimeRange.WEEK

    valid_types = ["summary", "incidents", "resources", "performance"]
    if request.report_type.lower() not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report type. Valid types: {valid_types}",
        )

    report = await service.generate_report(
        report_type=request.report_type.lower(),
        time_range=tr,
        start_date=request.start_date,
        end_date=request.end_date,
        user_id=current_user.id,
        options=request.options,
    )

    return ReportResponse(
        id=str(report.id),
        title=report.title,
        report_type=report.report_type,
        period_start=report.period_start,
        period_end=report.period_end,
        generated_at=report.generated_at,
        generated_by=str(report.generated_by) if report.generated_by else None,
        data=report.data,
        charts=report.charts,
    )


# Metrics Endpoints
@router.get("/metrics", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    current_user: User = Depends(require_permission(Permission.DASHBOARD_ANALYTICS)),
) -> MetricsSummaryResponse:
    """Get system metrics summary."""
    collector = get_metrics_collector()
    summary = collector.get_summary()

    return MetricsSummaryResponse(
        counters=summary["counters"],
        gauges=summary["gauges"],
        recorded_metrics=summary["recorded_metrics"],
    )


@router.get("/metrics/{metric_name}")
async def get_metric_values(
    metric_name: str,
    since: datetime | None = None,
    current_user: User = Depends(require_permission(Permission.DASHBOARD_ANALYTICS)),
) -> dict:
    """Get values for a specific metric."""
    collector = get_metrics_collector()

    # Check if it's a counter
    counter_value = collector.get_counter(metric_name)
    if counter_value > 0:
        return {
            "name": metric_name,
            "type": "counter",
            "value": counter_value,
        }

    # Check if it's a gauge
    gauge_value = collector.get_gauge(metric_name)
    if gauge_value is not None:
        return {
            "name": metric_name,
            "type": "gauge",
            "value": gauge_value,
        }

    # Get recorded metrics
    metrics = collector.get_metrics(metric_name, since)
    if metrics:
        return {
            "name": metric_name,
            "type": "recorded",
            "values": [
                {"timestamp": t.isoformat(), "value": v}
                for t, v in metrics
            ],
        }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Metric '{metric_name}' not found",
    )


@router.post("/metrics/record")
async def record_metric(
    name: str,
    value: float,
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Record a metric value."""
    collector = get_metrics_collector()
    collector.record(name, value)

    return {"message": f"Recorded {name}={value}"}


@router.get("/time-ranges")
async def list_time_ranges(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """List available time ranges."""
    return {
        "time_ranges": [
            {"id": tr.value, "name": tr.value.title()}
            for tr in TimeRange
        ]
    }


@router.get("/report-types")
async def list_report_types(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """List available report types."""
    return {
        "report_types": [
            {
                "id": "summary",
                "name": "Summary Report",
                "description": "Overview of incidents, resources, and alerts",
            },
            {
                "id": "incidents",
                "name": "Incident Report",
                "description": "Detailed incident statistics and breakdown",
            },
            {
                "id": "resources",
                "name": "Resource Report",
                "description": "Resource utilization and status breakdown",
            },
            {
                "id": "performance",
                "name": "Performance Report",
                "description": "Response times and operational metrics",
            },
        ]
    }

"""Telemetry query service for reading stored telemetry data.

Provides raw data queries via SQLAlchemy ORM and aggregate queries
(hourly, daily) via raw SQL on TimescaleDB continuous aggregates.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device_telemetry import DeviceTelemetry


class TelemetryQueryService:
    """Query telemetry with time range, metric filtering, and aggregations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def query_raw(
        self,
        device_id: UUID,
        metric_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict]:
        """Query raw telemetry from DeviceTelemetry hypertable.

        Returns most recent data first (time DESC).
        """
        query = select(DeviceTelemetry).where(DeviceTelemetry.device_id == device_id)

        if metric_name:
            query = query.where(DeviceTelemetry.metric_name == metric_name)
        if start_time:
            query = query.where(DeviceTelemetry.time >= start_time)
        if end_time:
            query = query.where(DeviceTelemetry.time <= end_time)

        query = query.order_by(DeviceTelemetry.time.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        rows = result.scalars().all()

        return [
            {
                "time": row.time.isoformat(),
                "device_id": str(row.device_id),
                "metric_name": row.metric_name,
                "value": self._coalesce_value(row),
            }
            for row in rows
        ]

    async def query_hourly(
        self,
        device_id: UUID,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict]:
        """Query hourly aggregates from device_telemetry_hourly continuous aggregate.

        Returns data in chronological order (bucket ASC).
        """
        return await self._query_aggregate(
            "device_telemetry_hourly", device_id, metric_name, start_time, end_time
        )

    async def query_daily(
        self,
        device_id: UUID,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict]:
        """Query daily aggregates from device_telemetry_daily continuous aggregate.

        Returns data in chronological order (bucket ASC).
        """
        return await self._query_aggregate(
            "device_telemetry_daily", device_id, metric_name, start_time, end_time
        )

    async def get_available_metrics(self, device_id: UUID) -> list[str]:
        """Return distinct metric names for a device."""
        query = (
            select(DeviceTelemetry.metric_name)
            .where(DeviceTelemetry.device_id == device_id)
            .distinct()
        )
        result = await self.db.execute(query)
        metrics = [row[0] for row in result.all()]
        return sorted(metrics)

    async def _query_aggregate(
        self,
        view_name: str,
        device_id: UUID,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict]:
        """Query a continuous aggregate view."""
        sql = text(f"""
            SELECT bucket, device_id, metric_name, avg_value, min_value, max_value, reading_count
            FROM {view_name}
            WHERE device_id = :device_id
              AND metric_name = :metric_name
              AND bucket BETWEEN :start_time AND :end_time
            ORDER BY bucket ASC
        """)

        result = await self.db.execute(
            sql,
            {
                "device_id": device_id,
                "metric_name": metric_name,
                "start_time": start_time,
                "end_time": end_time,
            },
        )

        return [
            {
                "time": row.bucket.isoformat(),
                "metric_name": row.metric_name,
                "avg": row.avg_value,
                "min": row.min_value,
                "max": row.max_value,
                "count": row.reading_count,
            }
            for row in result
        ]

    @staticmethod
    def _coalesce_value(row: DeviceTelemetry):
        """Coalesce value columns, checking bool before numeric."""
        if row.value_bool is not None:
            return row.value_bool
        if row.value_numeric is not None:
            return row.value_numeric
        if row.value_string is not None:
            return row.value_string
        return None

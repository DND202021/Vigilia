"""Telemetry batch worker service for Redis Stream → TimescaleDB ingestion.

Consumes telemetry from Redis Stream "telemetry:stream" using consumer groups,
accumulates into batches, expands metrics into narrow-schema rows, and batch-inserts
into the device_telemetry hypertable.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import structlog
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

if TYPE_CHECKING:
    from app.services.alert_rule_evaluation_service import AlertRuleEvaluationService

logger = structlog.get_logger()

STREAM_NAME = "telemetry:stream"
GROUP_NAME = "telemetry-workers"


class TelemetryWorkerService:
    """Consumes telemetry from Redis Streams and batch-inserts to TimescaleDB."""

    def __init__(
        self,
        redis_client: aioredis.Redis,
        session_factory: async_sessionmaker,
        batch_size: int = 1000,
        batch_timeout: float = 5.0,
        num_workers: int = 2,
        alert_evaluator: AlertRuleEvaluationService | None = None,
    ):
        self.redis = redis_client
        self.session_factory = session_factory
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.num_workers = num_workers
        self.alert_evaluator = alert_evaluator
        self._running = False
        self._worker_tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start worker pool consuming from Redis Stream."""
        self._running = True

        # Create consumer group if not exists
        try:
            await self.redis.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        # Start worker tasks
        for i in range(self.num_workers):
            task = asyncio.create_task(
                self._worker_loop(worker_id=i),
                name=f"telemetry-worker-{i}",
            )
            self._worker_tasks.append(task)

        logger.info("Telemetry worker pool started", num_workers=self.num_workers)

    async def stop(self) -> None:
        """Stop worker pool gracefully."""
        self._running = False

        for task in self._worker_tasks:
            task.cancel()

        for task in self._worker_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._worker_tasks.clear()
        logger.info("Telemetry worker pool stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        """Main consumer loop for a single worker."""
        consumer_name = f"worker-{worker_id}"
        batch: list[tuple[bytes, dict]] = []
        last_flush = asyncio.get_event_loop().time()

        logger.info("Telemetry worker started", worker_id=worker_id)

        while self._running:
            try:
                # Read from stream (1s block, shorter than batch_timeout)
                messages = await self.redis.xreadgroup(
                    groupname=GROUP_NAME,
                    consumername=consumer_name,
                    streams={STREAM_NAME: ">"},
                    count=100,
                    block=1000,
                )

                if messages:
                    for stream, msg_list in messages:
                        for msg_id, msg_data in msg_list:
                            # Handle both bytes and string keys
                            raw_payload = msg_data.get(b"payload") or msg_data.get("payload")
                            if raw_payload:
                                if isinstance(raw_payload, bytes):
                                    raw_payload = raw_payload.decode()
                                payload = json.loads(raw_payload)
                                batch.append((msg_id, payload))

                now = asyncio.get_event_loop().time()
                batch_rows = self._count_rows(batch)

                # Flush if batch full or timeout reached
                if batch_rows >= self.batch_size or (batch and (now - last_flush) >= self.batch_timeout):
                    await self._flush_batch(batch, worker_id)
                    batch = []
                    last_flush = now

            except asyncio.CancelledError:
                # Flush remaining batch before exit
                if batch:
                    try:
                        await self._flush_batch(batch, worker_id)
                    except Exception as e:
                        logger.error("Failed to flush final batch", worker_id=worker_id, error=str(e))
                logger.info("Telemetry worker cancelled", worker_id=worker_id)
                raise
            except Exception as e:
                logger.error("Worker error", worker_id=worker_id, error=str(e))
                await asyncio.sleep(1)

    def _count_rows(self, batch: list) -> int:
        """Count total rows that would be inserted (metrics per message)."""
        return sum(len(payload.get("metrics", {})) for _, payload in batch)

    async def _flush_batch(self, batch: list[tuple], worker_id: int) -> None:
        """Expand metrics into rows and batch-insert to device_telemetry."""
        if not batch:
            return

        # Expand metrics into narrow-schema rows
        rows = []
        for msg_id, item in batch:
            server_ts = datetime.fromisoformat(item["server_timestamp"])
            device_id = uuid.UUID(item["device_id"])

            for metric_name, value in item.get("metrics", {}).items():
                value_numeric = None
                value_string = None
                value_bool = None

                # CRITICAL: Check bool BEFORE numeric (isinstance(True, int) is True)
                if isinstance(value, bool):
                    value_bool = value
                elif isinstance(value, (int, float)):
                    value_numeric = float(value)
                elif isinstance(value, str):
                    value_string = value

                rows.append({
                    "time": server_ts,
                    "device_id": device_id,
                    "metric_name": metric_name,
                    "value_numeric": value_numeric,
                    "value_string": value_string,
                    "value_bool": value_bool,
                })

        # Evaluate alert rules (non-blocking, must not fail the batch insert)
        if self.alert_evaluator:
            try:
                items = [payload for _, payload in batch]
                await self.alert_evaluator.evaluate_batch(items)
            except Exception as e:
                logger.error("Alert evaluation failed", error=str(e))
                # Don't fail the batch insert due to alert eval failure

        if not rows:
            # Acknowledge messages with no metrics
            message_ids = [msg_id for msg_id, _ in batch]
            if message_ids:
                await self.redis.xack(STREAM_NAME, GROUP_NAME, *message_ids)
            return

        try:
            # Batch insert via SQLAlchemy session.execute with list of dicts
            async with self.session_factory() as session:
                await session.execute(
                    text("""
                        INSERT INTO device_telemetry
                            (time, device_id, metric_name, value_numeric, value_string, value_bool)
                        VALUES
                            (:time, :device_id, :metric_name, :value_numeric, :value_string, :value_bool)
                    """),
                    rows,
                )
                await session.commit()

            # Acknowledge all messages after successful insert
            message_ids = [msg_id for msg_id, _ in batch]
            if message_ids:
                await self.redis.xack(STREAM_NAME, GROUP_NAME, *message_ids)

            # Emit real-time telemetry events via Socket.IO
            await self._emit_telemetry_events(batch)

            logger.info(
                "Batch flushed",
                worker_id=worker_id,
                messages=len(batch),
                rows=len(rows),
            )

        except Exception as e:
            # Do NOT acknowledge - messages remain in pending list for retry
            logger.error(
                "Batch flush failed",
                worker_id=worker_id,
                messages=len(batch),
                rows=len(rows),
                error=str(e),
            )

    async def _emit_telemetry_events(self, batch: list[tuple]) -> None:
        """Emit telemetry data points to Socket.IO clients subscribed to device rooms."""
        try:
            from app.services.socketio import emit_telemetry_data

            for _, payload in batch:
                device_id = payload["device_id"]
                timestamp = payload["server_timestamp"]
                metrics = payload.get("metrics", {})

                for metric_name, value in metrics.items():
                    await emit_telemetry_data(device_id, metric_name, value, timestamp)

        except Exception as e:
            # Don't fail the batch if Socket.IO emit fails
            logger.warning("Failed to emit telemetry events", error=str(e))

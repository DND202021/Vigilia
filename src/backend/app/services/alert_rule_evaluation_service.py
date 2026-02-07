"""Alert Rule Evaluation Service for evaluating telemetry against device profile alert rules.

Processes telemetry batches, checks conditions against DeviceProfile.alert_rules,
enforces Redis cooldown deduplication, and creates alerts/incidents via AlertService.
"""

from __future__ import annotations

import uuid

import structlog
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.alert import AlertSeverity, AlertSource
from app.models.device import IoTDevice
from app.models.device_profile import DeviceProfile
from app.services.alert_service import AlertService
from app.services.socketio import emit_alert_created, emit_incident_created

logger = structlog.get_logger()


class AlertRuleEvaluationService:
    """Evaluates telemetry against device profile alert rules."""

    def __init__(
        self,
        redis_client: aioredis.Redis,
        session_factory: async_sessionmaker,
    ):
        self.redis = redis_client
        self.session_factory = session_factory

    async def evaluate_batch(self, batch_items: list[dict]) -> list[dict]:
        """Evaluate alert rules for a batch of telemetry items.

        Args:
            batch_items: List of telemetry payloads from Redis Stream
                [{"device_id": "...", "metrics": {"temp": 95}, "server_timestamp": "..."}]

        Returns:
            List of triggered alert dicts for logging/metrics.
        """
        if not batch_items:
            return []

        # 1. Collect unique device_ids from batch
        device_ids: set[uuid.UUID] = set()
        for item in batch_items:
            try:
                device_ids.add(uuid.UUID(item["device_id"]))
            except (KeyError, ValueError):
                continue

        if not device_ids:
            return []

        # 2. Bulk-load devices with profiles and buildings (single query)
        async with self.session_factory() as session:
            result = await session.execute(
                select(IoTDevice)
                .where(IoTDevice.id.in_(device_ids))
                .options(
                    selectinload(IoTDevice.profile),
                    selectinload(IoTDevice.building),
                )
            )
            devices = {d.id: d for d in result.scalars().all()}

        # 3. For each item, evaluate rules for matching metrics
        all_triggered: list[dict] = []
        for item in batch_items:
            try:
                device_id = uuid.UUID(item["device_id"])
            except (KeyError, ValueError):
                continue

            device = devices.get(device_id)
            if not device or not device.profile:
                continue

            profile: DeviceProfile = device.profile
            if not profile.alert_rules:
                continue

            metrics = item.get("metrics", {})
            if not metrics:
                continue

            server_timestamp = item.get("server_timestamp", "")

            # Evaluate rules against metrics
            triggered = self._evaluate_rules(profile, metrics)
            for rule_match in triggered:
                rule = rule_match["rule"]
                metric_value = rule_match["value"]
                cooldown_seconds = rule.get(
                    "cooldown_seconds", settings.alert_default_cooldown_seconds
                )

                # Check cooldown (skip if still in cooldown)
                can_fire = await self._check_cooldown(
                    str(device_id), rule["name"], cooldown_seconds
                )
                if not can_fire:
                    continue

                # Create alert and optionally auto-create incident
                try:
                    await self._create_alert_and_incident(
                        device=device,
                        building=device.building,
                        rule=rule,
                        metric_value=metric_value,
                        server_timestamp=server_timestamp,
                    )
                    all_triggered.append({
                        "device_id": str(device_id),
                        "device_name": device.name,
                        "rule_name": rule["name"],
                        "metric": rule["metric"],
                        "value": metric_value,
                        "severity": rule.get("severity", "medium"),
                    })
                    logger.info(
                        "Alert rule triggered",
                        device_id=str(device_id),
                        rule_name=rule["name"],
                        metric=rule["metric"],
                        value=metric_value,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to create alert from rule",
                        device_id=str(device_id),
                        rule_name=rule["name"],
                        error=str(e),
                    )

        return all_triggered

    @staticmethod
    def _evaluate_rules(profile: DeviceProfile, metrics: dict) -> list[dict]:
        """Evaluate all profile rules against provided metrics.

        Returns list of dicts with 'rule' and 'value' keys for triggered rules.
        """
        triggered: list[dict] = []
        for rule in profile.alert_rules:
            metric_name = rule.get("metric")
            if not metric_name or metric_name not in metrics:
                continue

            value = metrics[metric_name]
            condition = rule.get("condition", "gt")
            threshold = rule.get("threshold")
            if threshold is None:
                continue

            if AlertRuleEvaluationService._check_condition(condition, value, threshold):
                triggered.append({"rule": rule, "value": value})

        return triggered

    @staticmethod
    def _check_condition(condition: str, value, threshold) -> bool:
        """Evaluate a single condition.

        Conditions: gt, lt, gte, lte, eq, ne, range
        """
        try:
            if condition == "gt":
                return float(value) > float(threshold)
            if condition == "lt":
                return float(value) < float(threshold)
            if condition == "gte":
                return float(value) >= float(threshold)
            if condition == "lte":
                return float(value) <= float(threshold)
            if condition == "eq":
                return value == threshold
            if condition == "ne":
                return value != threshold
            if condition == "range":
                # threshold = {"min": X, "max": Y}
                return float(threshold["min"]) <= float(value) <= float(threshold["max"])
        except (TypeError, ValueError, KeyError):
            return False
        return False

    async def _check_cooldown(
        self, device_id: str, rule_name: str, cooldown_seconds: int
    ) -> bool:
        """Check Redis cooldown. Returns True if NOT in cooldown (can fire)."""
        key = f"alert:rule:cooldown:{device_id}:{rule_name}"
        was_set = await self.redis.set(key, "1", nx=True, ex=cooldown_seconds)
        return bool(was_set)

    async def _create_alert_and_incident(
        self,
        device: IoTDevice,
        building,
        rule: dict,
        metric_value,
        server_timestamp: str,
    ) -> None:
        """Create Alert via AlertService, optionally auto-create Incident."""
        async with self.session_factory() as session:
            alert_service = AlertService(session)

            # Determine alert_type from rule metric
            alert_type = self._rule_to_alert_type(rule)
            severity = AlertSeverity(rule.get("severity", "medium"))

            alert = await alert_service.ingest_alert(
                source=AlertSource.IOT_TELEMETRY,
                alert_type=alert_type,
                title=f"{rule['name']}: {rule['metric']}={metric_value} on {device.name}",
                severity=severity,
                source_id=f"iot:{device.id}:{rule['name']}:{server_timestamp}",
                source_device_id=str(device.id),
                latitude=device.latitude or (building.latitude if building else None),
                longitude=device.longitude or (building.longitude if building else None),
                raw_payload={
                    "device_id": str(device.id),
                    "device_name": device.name,
                    "rule_name": rule["name"],
                    "metric": rule["metric"],
                    "condition": rule.get("condition", "gt"),
                    "threshold": rule.get("threshold"),
                    "actual_value": metric_value,
                    "building_id": str(building.id) if building else None,
                },
            )

            # Set device linkage
            alert.device_id = device.id
            if building:
                alert.building_id = building.id
            await session.commit()

            # Emit Socket.IO alert event
            await emit_alert_created({
                "id": str(alert.id),
                "source": alert.source.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "device_id": str(device.id),
                "device_name": device.name,
                "rule_name": rule["name"],
                "metric": rule["metric"],
                "value": metric_value,
            })

            # Auto-create incident for CRITICAL/HIGH
            if settings.alert_auto_create_incidents and severity in (
                AlertSeverity.CRITICAL,
                AlertSeverity.HIGH,
            ):
                agency_id = building.agency_id if building else None
                if agency_id and alert.latitude and alert.longitude:
                    try:
                        incident = await alert_service.create_incident_from_alert(
                            alert_id=alert.id,
                            agency_id=agency_id,
                        )
                        await emit_incident_created({
                            "id": str(incident.id),
                            "incident_number": incident.incident_number,
                            "title": incident.title,
                            "category": incident.category.value,
                            "priority": incident.priority.value,
                            "status": incident.status.value,
                            "source": "iot_telemetry",
                            "device_id": str(device.id),
                        })
                    except Exception as e:
                        logger.error(
                            "Failed to auto-create incident from alert",
                            alert_id=str(alert.id),
                            error=str(e),
                        )

    @staticmethod
    def _rule_to_alert_type(rule: dict) -> str:
        """Map rule metric/condition to an alert_type string."""
        metric = rule.get("metric", "").lower()
        threshold_str = str(rule.get("threshold", "")).lower()

        if "gunshot" in threshold_str or "gunshot" in metric:
            return "iot_gunshot"
        if "temperature" in metric or "temp" in metric:
            return "iot_temperature_high"
        if "tamper" in metric:
            return "iot_tamper"
        if "gas" in metric:
            return "iot_gas_detected"
        if "sound" in metric or "db" in metric:
            return "iot_sound_anomaly"
        if "motion" in metric or "intrusion" in metric:
            return "iot_intrusion"
        return "iot_threshold_violation"

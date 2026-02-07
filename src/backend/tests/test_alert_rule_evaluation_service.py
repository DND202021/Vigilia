"""Tests for AlertRuleEvaluationService."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.alert_rule_evaluation_service import AlertRuleEvaluationService
from app.models.device import IoTDevice
from app.models.device_profile import DeviceProfile
from app.models.alert import AlertSeverity


class TestCheckCondition:
    """Tests for _check_condition static method."""

    def test_greater_than_true(self):
        """Test gt condition when value is greater."""
        result = AlertRuleEvaluationService._check_condition("gt", 100, 50)
        assert result is True

    def test_greater_than_false(self):
        """Test gt condition when value is not greater."""
        result = AlertRuleEvaluationService._check_condition("gt", 50, 100)
        assert result is False

    def test_less_than_true(self):
        """Test lt condition when value is less."""
        result = AlertRuleEvaluationService._check_condition("lt", 20, 50)
        assert result is True

    def test_less_than_false(self):
        """Test lt condition when value is not less."""
        result = AlertRuleEvaluationService._check_condition("lt", 100, 50)
        assert result is False

    def test_greater_than_or_equal_true(self):
        """Test gte condition when value is greater or equal."""
        assert AlertRuleEvaluationService._check_condition("gte", 50, 50) is True
        assert AlertRuleEvaluationService._check_condition("gte", 60, 50) is True

    def test_greater_than_or_equal_false(self):
        """Test gte condition when value is less."""
        result = AlertRuleEvaluationService._check_condition("gte", 40, 50)
        assert result is False

    def test_less_than_or_equal_true(self):
        """Test lte condition when value is less or equal."""
        assert AlertRuleEvaluationService._check_condition("lte", 50, 50) is True
        assert AlertRuleEvaluationService._check_condition("lte", 40, 50) is True

    def test_less_than_or_equal_false(self):
        """Test lte condition when value is greater."""
        result = AlertRuleEvaluationService._check_condition("lte", 60, 50)
        assert result is False

    def test_equal_true(self):
        """Test eq condition when values match."""
        result = AlertRuleEvaluationService._check_condition("eq", "active", "active")
        assert result is True

    def test_equal_false(self):
        """Test eq condition when values don't match."""
        result = AlertRuleEvaluationService._check_condition("eq", "active", "inactive")
        assert result is False

    def test_not_equal_true(self):
        """Test ne condition when values don't match."""
        result = AlertRuleEvaluationService._check_condition("ne", "active", "inactive")
        assert result is True

    def test_not_equal_false(self):
        """Test ne condition when values match."""
        result = AlertRuleEvaluationService._check_condition("ne", "active", "active")
        assert result is False

    def test_range_true(self):
        """Test range condition when value is within range."""
        result = AlertRuleEvaluationService._check_condition(
            "range", 50, {"min": 0, "max": 100}
        )
        assert result is True

    def test_range_false_below(self):
        """Test range condition when value is below range."""
        result = AlertRuleEvaluationService._check_condition(
            "range", -10, {"min": 0, "max": 100}
        )
        assert result is False

    def test_range_false_above(self):
        """Test range condition when value is above range."""
        result = AlertRuleEvaluationService._check_condition(
            "range", 150, {"min": 0, "max": 100}
        )
        assert result is False

    def test_unknown_condition(self):
        """Test unknown condition returns False."""
        result = AlertRuleEvaluationService._check_condition("unknown", 50, 50)
        assert result is False

    def test_invalid_value_type(self):
        """Test invalid value type returns False."""
        result = AlertRuleEvaluationService._check_condition("gt", "not-a-number", 50)
        assert result is False


class TestRuleToAlertType:
    """Tests for _rule_to_alert_type static method."""

    def test_gunshot_metric(self):
        """Test gunshot detection rule."""
        rule = {"metric": "gunshot_level", "threshold": 0.9}
        result = AlertRuleEvaluationService._rule_to_alert_type(rule)
        assert result == "iot_gunshot"

    def test_temperature_metric(self):
        """Test temperature rule."""
        rule = {"metric": "temperature", "threshold": 80}
        result = AlertRuleEvaluationService._rule_to_alert_type(rule)
        assert result == "iot_temperature_high"

    def test_temp_metric(self):
        """Test temp abbreviation rule."""
        rule = {"metric": "temp", "threshold": 80}
        result = AlertRuleEvaluationService._rule_to_alert_type(rule)
        assert result == "iot_temperature_high"

    def test_tamper_metric(self):
        """Test tamper detection rule."""
        rule = {"metric": "tamper_detected", "threshold": True}
        result = AlertRuleEvaluationService._rule_to_alert_type(rule)
        assert result == "iot_tamper"

    def test_gas_metric(self):
        """Test gas detection rule."""
        rule = {"metric": "gas_level", "threshold": 100}
        result = AlertRuleEvaluationService._rule_to_alert_type(rule)
        assert result == "iot_gas_detected"

    def test_sound_metric(self):
        """Test sound level rule."""
        rule = {"metric": "sound_level", "threshold": 90}
        result = AlertRuleEvaluationService._rule_to_alert_type(rule)
        assert result == "iot_sound_anomaly"

    def test_db_metric(self):
        """Test decibel metric rule."""
        rule = {"metric": "db_level", "threshold": 85}
        result = AlertRuleEvaluationService._rule_to_alert_type(rule)
        assert result == "iot_sound_anomaly"

    def test_motion_metric(self):
        """Test motion detection rule."""
        rule = {"metric": "motion", "threshold": True}
        result = AlertRuleEvaluationService._rule_to_alert_type(rule)
        assert result == "iot_intrusion"

    def test_intrusion_metric(self):
        """Test intrusion detection rule."""
        rule = {"metric": "intrusion", "threshold": True}
        result = AlertRuleEvaluationService._rule_to_alert_type(rule)
        assert result == "iot_intrusion"

    def test_default_metric(self):
        """Test default alert type for unknown metric."""
        rule = {"metric": "humidity", "threshold": 80}
        result = AlertRuleEvaluationService._rule_to_alert_type(rule)
        assert result == "iot_threshold_violation"


class TestEvaluateRules:
    """Tests for _evaluate_rules static method."""

    def test_no_matching_metrics(self):
        """Test no rules trigger when metrics don't match."""
        profile = MagicMock()
        profile.alert_rules = [
            {"metric": "temperature", "condition": "gt", "threshold": 80}
        ]
        metrics = {"humidity": 60}

        result = AlertRuleEvaluationService._evaluate_rules(profile, metrics)
        assert result == []

    def test_single_rule_triggers(self):
        """Test single rule triggers when condition met."""
        profile = MagicMock()
        profile.alert_rules = [
            {"metric": "temperature", "condition": "gt", "threshold": 80}
        ]
        metrics = {"temperature": 95}

        result = AlertRuleEvaluationService._evaluate_rules(profile, metrics)
        assert len(result) == 1
        assert result[0]["value"] == 95

    def test_single_rule_not_triggered(self):
        """Test rule doesn't trigger when condition not met."""
        profile = MagicMock()
        profile.alert_rules = [
            {"metric": "temperature", "condition": "gt", "threshold": 80}
        ]
        metrics = {"temperature": 70}

        result = AlertRuleEvaluationService._evaluate_rules(profile, metrics)
        assert result == []

    def test_multiple_rules_trigger(self):
        """Test multiple rules can trigger."""
        profile = MagicMock()
        profile.alert_rules = [
            {"metric": "temperature", "condition": "gt", "threshold": 80},
            {"metric": "humidity", "condition": "gt", "threshold": 70},
        ]
        metrics = {"temperature": 95, "humidity": 85}

        result = AlertRuleEvaluationService._evaluate_rules(profile, metrics)
        assert len(result) == 2

    def test_rule_without_threshold(self):
        """Test rule without threshold is skipped."""
        profile = MagicMock()
        profile.alert_rules = [
            {"metric": "temperature", "condition": "gt"}  # No threshold
        ]
        metrics = {"temperature": 95}

        result = AlertRuleEvaluationService._evaluate_rules(profile, metrics)
        assert result == []


class TestAlertRuleEvaluationService:
    """Tests for AlertRuleEvaluationService methods."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_session_factory(self):
        """Create mock session factory."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_factory = MagicMock()
        mock_factory.return_value = mock_session

        return mock_factory

    @pytest.mark.asyncio
    async def test_evaluate_batch_empty(self, mock_redis, mock_session_factory):
        """Test evaluating empty batch."""
        service = AlertRuleEvaluationService(mock_redis, mock_session_factory)

        result = await service.evaluate_batch([])
        assert result == []

    @pytest.mark.asyncio
    async def test_evaluate_batch_invalid_device_id(self, mock_redis, mock_session_factory):
        """Test evaluating batch with invalid device IDs."""
        service = AlertRuleEvaluationService(mock_redis, mock_session_factory)

        result = await service.evaluate_batch([
            {"device_id": "not-a-uuid", "metrics": {"temp": 90}},
            {"metrics": {"temp": 90}},  # Missing device_id
        ])
        assert result == []

    @pytest.mark.asyncio
    async def test_check_cooldown_not_in_cooldown(self, mock_redis, mock_session_factory):
        """Test cooldown check when not in cooldown."""
        mock_redis.set.return_value = True  # Key was set (not in cooldown)

        service = AlertRuleEvaluationService(mock_redis, mock_session_factory)
        result = await service._check_cooldown("device-1", "High Temp", 300)

        assert result is True
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_cooldown_in_cooldown(self, mock_redis, mock_session_factory):
        """Test cooldown check when in cooldown."""
        mock_redis.set.return_value = False  # Key exists (in cooldown)

        service = AlertRuleEvaluationService(mock_redis, mock_session_factory)
        result = await service._check_cooldown("device-1", "High Temp", 300)

        assert result is False

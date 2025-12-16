"""
Tests for croom.dashboard.alerting module.
"""

import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

import pytest

from croom.dashboard.alerting import (
    AlertSeverity,
    AlertChannel,
    AlertState,
    AlertRule,
    Alert,
    AlertNotifier,
    EmailNotifier,
    SlackNotifier,
    TeamsNotifier,
    WebhookNotifier,
    AlertManager,
)


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_values(self):
        """Test alert severity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertChannel:
    """Tests for AlertChannel enum."""

    def test_values(self):
        """Test alert channel enum values."""
        assert AlertChannel.EMAIL.value == "email"
        assert AlertChannel.SLACK.value == "slack"
        assert AlertChannel.SMS.value == "sms"
        assert AlertChannel.WEBHOOK.value == "webhook"
        assert AlertChannel.TEAMS.value == "teams"


class TestAlertState:
    """Tests for AlertState enum."""

    def test_values(self):
        """Test alert state enum values."""
        assert AlertState.ACTIVE.value == "active"
        assert AlertState.ACKNOWLEDGED.value == "acknowledged"
        assert AlertState.RESOLVED.value == "resolved"
        assert AlertState.SNOOZED.value == "snoozed"


class TestAlertRule:
    """Tests for AlertRule dataclass."""

    def test_creation(self):
        """Test creating an alert rule."""
        rule = AlertRule(
            id="rule_1",
            name="High CPU",
            description="CPU usage is too high",
            condition="cpu_percent > 90",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
            cooldown_seconds=300,
        )

        assert rule.id == "rule_1"
        assert rule.name == "High CPU"
        assert rule.severity == AlertSeverity.WARNING
        assert len(rule.channels) == 2

    def test_default_values(self):
        """Test alert rule default values."""
        rule = AlertRule(id="rule_1", name="Test Rule")

        assert rule.description == ""
        assert rule.condition == ""
        assert rule.severity == AlertSeverity.WARNING
        assert rule.channels == []
        assert rule.cooldown_seconds == 300
        assert rule.enabled is True

    def test_to_dict(self):
        """Test converting rule to dictionary."""
        rule = AlertRule(
            id="rule_1",
            name="Test Rule",
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.EMAIL],
        )
        result = rule.to_dict()

        assert result["id"] == "rule_1"
        assert result["name"] == "Test Rule"
        assert result["severity"] == "critical"
        assert "email" in result["channels"]


class TestAlert:
    """Tests for Alert dataclass."""

    def test_creation(self):
        """Test creating an alert."""
        alert = Alert(
            id="alert_1",
            rule_id="rule_1",
            device_id="device_1",
            severity=AlertSeverity.WARNING,
            title="High CPU Usage",
            message="CPU usage is at 95%",
        )

        assert alert.id == "alert_1"
        assert alert.rule_id == "rule_1"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.state == AlertState.ACTIVE

    def test_default_values(self):
        """Test alert default values."""
        alert = Alert(
            id="alert_1",
            rule_id="rule_1",
            device_id="device_1",
            severity=AlertSeverity.INFO,
            title="Test",
            message="Test message",
        )

        assert alert.state == AlertState.ACTIVE
        assert alert.acknowledged_at is None
        assert alert.resolved_at is None

    def test_to_dict(self):
        """Test converting alert to dictionary."""
        alert = Alert(
            id="alert_1",
            rule_id="rule_1",
            device_id="device_1",
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
        )
        result = alert.to_dict()

        assert result["id"] == "alert_1"
        assert result["severity"] == "warning"
        assert result["state"] == "active"
        assert "created_at" in result


class TestEmailNotifier:
    """Tests for EmailNotifier class."""

    def test_init(self):
        """Test email notifier initialization."""
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_address="alerts@example.com",
            to_addresses=["admin@example.com"],
        )

        assert notifier._smtp_host == "smtp.example.com"
        assert notifier._smtp_port == 587
        assert notifier.channel == AlertChannel.EMAIL

    @pytest.mark.asyncio
    async def test_send_no_recipients(self):
        """Test email send with no recipients."""
        notifier = EmailNotifier(smtp_host="localhost")
        rule = AlertRule(id="rule_1", name="Test Rule")
        alert = Alert(
            id="alert_1",
            rule_id="rule_1",
            device_id="device_1",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
        )

        result = await notifier.send(alert, rule)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_success(self):
        """Test successful email send."""
        notifier = EmailNotifier(
            smtp_host="localhost",
            to_addresses=["admin@example.com"],
        )
        rule = AlertRule(id="rule_1", name="Test Rule")
        alert = Alert(
            id="alert_1",
            rule_id="rule_1",
            device_id="device_1",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
        )

        with patch.object(notifier, "_send_smtp"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock()
                result = await notifier.send(alert, rule)
                assert result is True


class TestSlackNotifier:
    """Tests for SlackNotifier class."""

    def test_init(self):
        """Test Slack notifier initialization."""
        notifier = SlackNotifier(
            webhook_url="https://hooks.slack.com/services/xxx",
            channel="#alerts",
        )

        assert notifier._webhook_url == "https://hooks.slack.com/services/xxx"
        assert notifier._channel == "#alerts"
        assert notifier.channel == AlertChannel.SLACK

    @pytest.mark.asyncio
    async def test_send_success(self):
        """Test successful Slack send."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/xxx")
        rule = AlertRule(id="rule_1", name="Test Rule")
        alert = Alert(
            id="alert_1",
            rule_id="rule_1",
            device_id="device_1",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
        )

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_response
            mock_session_instance = MagicMock()
            mock_session_instance.post.return_value = mock_cm
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            result = await notifier.send(alert, rule)
            assert result is True


class TestTeamsNotifier:
    """Tests for TeamsNotifier class."""

    def test_init(self):
        """Test Teams notifier initialization."""
        notifier = TeamsNotifier(
            webhook_url="https://outlook.office.com/webhook/xxx",
        )

        assert notifier._webhook_url == "https://outlook.office.com/webhook/xxx"
        assert notifier.channel == AlertChannel.TEAMS

    @pytest.mark.asyncio
    async def test_send_success(self):
        """Test successful Teams send."""
        notifier = TeamsNotifier(webhook_url="https://outlook.office.com/webhook/xxx")
        rule = AlertRule(id="rule_1", name="Test Rule")
        alert = Alert(
            id="alert_1",
            rule_id="rule_1",
            device_id="device_1",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
        )

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_response
            mock_session_instance = MagicMock()
            mock_session_instance.post.return_value = mock_cm
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            result = await notifier.send(alert, rule)
            assert result is True


class TestWebhookNotifier:
    """Tests for WebhookNotifier class."""

    def test_init(self):
        """Test webhook notifier initialization."""
        notifier = WebhookNotifier(
            url="https://example.com/webhook",
            method="POST",
            headers={"Authorization": "Bearer xxx"},
            secret="mysecret",
        )

        assert notifier._url == "https://example.com/webhook"
        assert notifier._method == "POST"
        assert notifier._secret == "mysecret"
        assert notifier.channel == AlertChannel.WEBHOOK

    @pytest.mark.asyncio
    async def test_send_success(self):
        """Test successful webhook send."""
        notifier = WebhookNotifier(url="https://example.com/webhook")
        rule = AlertRule(id="rule_1", name="Test Rule")
        alert = Alert(
            id="alert_1",
            rule_id="rule_1",
            device_id="device_1",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
        )

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_response
            mock_session_instance = MagicMock()
            mock_session_instance.post.return_value = mock_cm
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            result = await notifier.send(alert, rule)
            assert result is True


class TestAlertManager:
    """Tests for AlertManager class."""

    def test_init(self):
        """Test alert manager initialization."""
        manager = AlertManager()

        assert len(manager._rules) == 0
        assert len(manager._alerts) == 0
        assert len(manager._notifiers) == 0

    def test_add_rule(self):
        """Test adding an alert rule."""
        manager = AlertManager()
        rule = AlertRule(id="rule_1", name="Test Rule")

        manager.add_rule(rule)

        assert "rule_1" in manager._rules
        assert manager.get_rule("rule_1") == rule

    def test_remove_rule(self):
        """Test removing an alert rule."""
        manager = AlertManager()
        rule = AlertRule(id="rule_1", name="Test Rule")
        manager.add_rule(rule)

        result = manager.remove_rule("rule_1")

        assert result is True
        assert "rule_1" not in manager._rules

    def test_remove_nonexistent_rule(self):
        """Test removing a nonexistent rule."""
        manager = AlertManager()

        result = manager.remove_rule("nonexistent")
        assert result is False

    def test_get_rules(self):
        """Test getting all rules."""
        manager = AlertManager()
        manager.add_rule(AlertRule(id="rule_1", name="Rule 1"))
        manager.add_rule(AlertRule(id="rule_2", name="Rule 2"))

        rules = manager.get_rules()
        assert len(rules) == 2

    def test_add_notifier(self):
        """Test adding a notifier."""
        manager = AlertManager()
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/xxx")

        manager.add_notifier(notifier)

        assert AlertChannel.SLACK in manager._notifiers

    @pytest.mark.asyncio
    async def test_check_condition_true(self):
        """Test checking condition that evaluates to true."""
        manager = AlertManager()
        rule = AlertRule(
            id="rule_1",
            name="High CPU",
            condition="cpu_percent > 90",
            severity=AlertSeverity.WARNING,
        )
        manager.add_rule(rule)

        alert = await manager.check_condition(
            rule_id="rule_1",
            device_id="device_1",
            metrics={"cpu_percent": 95},
        )

        assert alert is not None
        assert alert.rule_id == "rule_1"
        assert alert.device_id == "device_1"

    @pytest.mark.asyncio
    async def test_check_condition_false(self):
        """Test checking condition that evaluates to false."""
        manager = AlertManager()
        rule = AlertRule(
            id="rule_1",
            name="High CPU",
            condition="cpu_percent > 90",
            severity=AlertSeverity.WARNING,
        )
        manager.add_rule(rule)

        alert = await manager.check_condition(
            rule_id="rule_1",
            device_id="device_1",
            metrics={"cpu_percent": 50},
        )

        assert alert is None

    @pytest.mark.asyncio
    async def test_check_condition_disabled_rule(self):
        """Test checking condition with disabled rule."""
        manager = AlertManager()
        rule = AlertRule(
            id="rule_1",
            name="High CPU",
            condition="cpu_percent > 90",
            enabled=False,
        )
        manager.add_rule(rule)

        alert = await manager.check_condition(
            rule_id="rule_1",
            device_id="device_1",
            metrics={"cpu_percent": 95},
        )

        assert alert is None

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        manager = AlertManager()
        rule = AlertRule(
            id="rule_1",
            name="Test Rule",
            condition="value > 0",
        )
        manager.add_rule(rule)

        alert = await manager.check_condition(
            rule_id="rule_1",
            device_id="device_1",
            metrics={"value": 1},
        )

        result = await manager.acknowledge_alert(alert.id, "admin")

        assert result is True
        assert alert.state == AlertState.ACKNOWLEDGED
        assert alert.acknowledged_by == "admin"

    @pytest.mark.asyncio
    async def test_resolve_alert(self):
        """Test resolving an alert."""
        manager = AlertManager()
        rule = AlertRule(
            id="rule_1",
            name="Test Rule",
            condition="value > 0",
        )
        manager.add_rule(rule)

        alert = await manager.check_condition(
            rule_id="rule_1",
            device_id="device_1",
            metrics={"value": 1},
        )

        result = await manager.resolve_alert(alert.id)

        assert result is True
        assert alert.state == AlertState.RESOLVED
        assert alert.resolved_at is not None

    @pytest.mark.asyncio
    async def test_snooze_alert(self):
        """Test snoozing an alert."""
        manager = AlertManager()
        rule = AlertRule(
            id="rule_1",
            name="Test Rule",
            condition="value > 0",
        )
        manager.add_rule(rule)

        alert = await manager.check_condition(
            rule_id="rule_1",
            device_id="device_1",
            metrics={"value": 1},
        )

        result = await manager.snooze_alert(alert.id, duration_minutes=30)

        assert result is True
        assert alert.state == AlertState.SNOOZED
        assert alert.snoozed_until is not None

    def test_get_alerts_filtered(self):
        """Test getting alerts with filters."""
        manager = AlertManager()
        manager._alerts = {
            "a1": Alert(
                id="a1", rule_id="r1", device_id="d1",
                severity=AlertSeverity.WARNING, title="Test", message="Test",
                state=AlertState.ACTIVE,
            ),
            "a2": Alert(
                id="a2", rule_id="r1", device_id="d1",
                severity=AlertSeverity.CRITICAL, title="Test", message="Test",
                state=AlertState.RESOLVED,
            ),
        }

        active_alerts = manager.get_alerts(state=AlertState.ACTIVE)
        assert len(active_alerts) == 1
        assert active_alerts[0].id == "a1"

        critical_alerts = manager.get_alerts(severity=AlertSeverity.CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0].id == "a2"

    def test_get_active_count(self):
        """Test getting active alert count."""
        manager = AlertManager()
        manager._alerts = {
            "a1": Alert(
                id="a1", rule_id="r1", device_id="d1",
                severity=AlertSeverity.WARNING, title="Test", message="Test",
                state=AlertState.ACTIVE,
            ),
            "a2": Alert(
                id="a2", rule_id="r1", device_id="d1",
                severity=AlertSeverity.WARNING, title="Test", message="Test",
                state=AlertState.ACTIVE,
            ),
            "a3": Alert(
                id="a3", rule_id="r1", device_id="d1",
                severity=AlertSeverity.WARNING, title="Test", message="Test",
                state=AlertState.RESOLVED,
            ),
        }

        count = manager.get_active_count()
        assert count == 2

    def test_on_alert_callback(self):
        """Test alert callback registration."""
        manager = AlertManager()
        callback = MagicMock()

        manager.on_alert(callback)

        assert callback in manager._callbacks

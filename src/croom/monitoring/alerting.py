"""
Alerting system for Croom.

Provides configurable alert rules, notification channels, and alert management.
"""

import asyncio
import hashlib
import json
import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertState(Enum):
    """Alert state."""
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class NotificationChannel(Enum):
    """Notification channel types."""
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    MQTT = "mqtt"
    CALLBACK = "callback"


class ComparisonOperator(Enum):
    """Comparison operators for alert rules."""
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NE = "!="


@dataclass
class AlertRule:
    """Definition of an alert rule."""
    id: str
    name: str
    description: str
    metric_name: str
    operator: ComparisonOperator
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING
    duration: int = 0  # Seconds the condition must persist
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    def evaluate(self, value: float) -> bool:
        """Evaluate if the condition is met."""
        if self.operator == ComparisonOperator.GT:
            return value > self.threshold
        elif self.operator == ComparisonOperator.GTE:
            return value >= self.threshold
        elif self.operator == ComparisonOperator.LT:
            return value < self.threshold
        elif self.operator == ComparisonOperator.LTE:
            return value <= self.threshold
        elif self.operator == ComparisonOperator.EQ:
            return value == self.threshold
        elif self.operator == ComparisonOperator.NE:
            return value != self.threshold
        return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "metric_name": self.metric_name,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "duration": self.duration,
            "labels": self.labels,
            "annotations": self.annotations,
            "enabled": self.enabled,
        }


@dataclass
class Alert:
    """An active or historical alert."""
    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    state: AlertState
    message: str
    value: float
    threshold: float
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    last_notification: Optional[datetime] = None
    notification_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "state": self.state.value,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "labels": self.labels,
            "annotations": self.annotations,
            "started_at": self.started_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "last_notification": self.last_notification.isoformat() if self.last_notification else None,
            "notification_count": self.notification_count,
        }


@dataclass
class AlertSilence:
    """A silence rule to suppress alerts."""
    id: str
    matchers: Dict[str, str]  # Label matchers
    created_by: str
    comment: str
    starts_at: datetime
    ends_at: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_active(self) -> bool:
        """Check if silence is currently active."""
        now = datetime.utcnow()
        return self.starts_at <= now <= self.ends_at

    def matches(self, alert: Alert) -> bool:
        """Check if silence matches an alert."""
        if not self.is_active():
            return False
        for key, value in self.matchers.items():
            if key == "rule_id" and alert.rule_id != value:
                return False
            elif key == "severity" and alert.severity.value != value:
                return False
            elif key in alert.labels and alert.labels.get(key) != value:
                return False
        return True


@dataclass
class NotificationConfig:
    """Configuration for a notification channel."""
    id: str
    name: str
    channel_type: NotificationChannel
    config: Dict[str, Any]
    enabled: bool = True
    min_severity: AlertSeverity = AlertSeverity.WARNING
    labels_filter: Dict[str, str] = field(default_factory=dict)


class WebhookNotifier:
    """Sends alerts via webhook."""

    async def send(
        self,
        alert: Alert,
        config: NotificationConfig,
    ) -> bool:
        """Send webhook notification."""
        try:
            url = config.config.get("url")
            if not url:
                logger.error("Webhook URL not configured")
                return False

            payload = {
                "version": "1.0",
                "status": alert.state.value,
                "alert": alert.to_dict(),
                "timestamp": datetime.utcnow().isoformat(),
            }

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Croom-Alerting/1.0",
            }

            # Add custom headers
            if "headers" in config.config:
                headers.update(config.config["headers"])

            # Add authentication
            if "auth_token" in config.config:
                headers["Authorization"] = f"Bearer {config.config['auth_token']}"

            data = json.dumps(payload).encode("utf-8")
            req = Request(url, data=data, headers=headers, method="POST")

            # Send async
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: urlopen(req, timeout=10),
            )
            return True

        except URLError as e:
            logger.error(f"Webhook notification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Webhook notification error: {e}")
            return False


class EmailNotifier:
    """Sends alerts via email."""

    async def send(
        self,
        alert: Alert,
        config: NotificationConfig,
    ) -> bool:
        """Send email notification."""
        try:
            smtp_config = config.config
            host = smtp_config.get("smtp_host", "localhost")
            port = smtp_config.get("smtp_port", 587)
            username = smtp_config.get("username")
            password = smtp_config.get("password")
            use_tls = smtp_config.get("use_tls", True)
            from_addr = smtp_config.get("from_address", "croom@localhost")
            to_addrs = smtp_config.get("to_addresses", [])

            if not to_addrs:
                logger.error("No email recipients configured")
                return False

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[Croom {alert.severity.value.upper()}] {alert.rule_name}"
            msg["From"] = from_addr
            msg["To"] = ", ".join(to_addrs)

            # Plain text body
            text_body = f"""
Croom Alert Notification
==========================

Alert: {alert.rule_name}
Severity: {alert.severity.value.upper()}
Status: {alert.state.value}
Time: {alert.started_at.isoformat()}

Message:
{alert.message}

Details:
- Current Value: {alert.value}
- Threshold: {alert.threshold}

Labels: {json.dumps(alert.labels, indent=2)}

---
This is an automated message from Croom Monitoring.
"""

            # HTML body
            html_body = f"""
<html>
<head>
<style>
.alert {{ padding: 20px; border-radius: 5px; margin: 10px 0; }}
.critical {{ background: #ffebee; border-left: 4px solid #f44336; }}
.warning {{ background: #fff3e0; border-left: 4px solid #ff9800; }}
.info {{ background: #e3f2fd; border-left: 4px solid #2196f3; }}
</style>
</head>
<body>
<h2>Croom Alert Notification</h2>
<div class="alert {alert.severity.value}">
<h3>{alert.rule_name}</h3>
<p><strong>Severity:</strong> {alert.severity.value.upper()}</p>
<p><strong>Status:</strong> {alert.state.value}</p>
<p><strong>Time:</strong> {alert.started_at.isoformat()}</p>
</div>
<h4>Message</h4>
<p>{alert.message}</p>
<h4>Details</h4>
<ul>
<li><strong>Current Value:</strong> {alert.value}</li>
<li><strong>Threshold:</strong> {alert.threshold}</li>
</ul>
<hr>
<p><small>This is an automated message from Croom Monitoring.</small></p>
</body>
</html>
"""

            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Send email
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._send_email(
                    host, port, username, password, use_tls,
                    from_addr, to_addrs, msg
                ),
            )
            return True

        except Exception as e:
            logger.error(f"Email notification error: {e}")
            return False

    def _send_email(
        self,
        host: str,
        port: int,
        username: Optional[str],
        password: Optional[str],
        use_tls: bool,
        from_addr: str,
        to_addrs: List[str],
        msg: MIMEMultipart,
    ) -> None:
        """Send email synchronously."""
        if use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port) as server:
                server.starttls(context=context)
                if username and password:
                    server.login(username, password)
                server.sendmail(from_addr, to_addrs, msg.as_string())
        else:
            with smtplib.SMTP(host, port) as server:
                if username and password:
                    server.login(username, password)
                server.sendmail(from_addr, to_addrs, msg.as_string())


class SlackNotifier:
    """Sends alerts via Slack webhook."""

    async def send(
        self,
        alert: Alert,
        config: NotificationConfig,
    ) -> bool:
        """Send Slack notification."""
        try:
            webhook_url = config.config.get("webhook_url")
            if not webhook_url:
                logger.error("Slack webhook URL not configured")
                return False

            # Color based on severity
            colors = {
                AlertSeverity.INFO: "#2196f3",
                AlertSeverity.WARNING: "#ff9800",
                AlertSeverity.CRITICAL: "#f44336",
            }

            emoji = "🔴" if alert.severity == AlertSeverity.CRITICAL else "🟡" if alert.severity == AlertSeverity.WARNING else "🔵"

            payload = {
                "attachments": [{
                    "color": colors.get(alert.severity, "#808080"),
                    "title": f"{emoji} {alert.rule_name}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                        {"title": "Status", "value": alert.state.value, "short": True},
                        {"title": "Current Value", "value": str(alert.value), "short": True},
                        {"title": "Threshold", "value": str(alert.threshold), "short": True},
                    ],
                    "footer": "Croom Monitoring",
                    "ts": int(alert.started_at.timestamp()),
                }],
            }

            # Add channel if specified
            if "channel" in config.config:
                payload["channel"] = config.config["channel"]

            data = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            req = Request(webhook_url, data=data, headers=headers, method="POST")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: urlopen(req, timeout=10),
            )
            return True

        except Exception as e:
            logger.error(f"Slack notification error: {e}")
            return False


class TeamsNotifier:
    """Sends alerts via Microsoft Teams webhook."""

    async def send(
        self,
        alert: Alert,
        config: NotificationConfig,
    ) -> bool:
        """Send Teams notification."""
        try:
            webhook_url = config.config.get("webhook_url")
            if not webhook_url:
                logger.error("Teams webhook URL not configured")
                return False

            # Theme color based on severity
            colors = {
                AlertSeverity.INFO: "2196f3",
                AlertSeverity.WARNING: "ff9800",
                AlertSeverity.CRITICAL: "f44336",
            }

            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": colors.get(alert.severity, "808080"),
                "summary": f"Croom Alert: {alert.rule_name}",
                "sections": [{
                    "activityTitle": f"**{alert.rule_name}**",
                    "activitySubtitle": f"Severity: {alert.severity.value.upper()}",
                    "facts": [
                        {"name": "Status", "value": alert.state.value},
                        {"name": "Current Value", "value": str(alert.value)},
                        {"name": "Threshold", "value": str(alert.threshold)},
                        {"name": "Time", "value": alert.started_at.isoformat()},
                    ],
                    "text": alert.message,
                    "markdown": True,
                }],
            }

            data = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            req = Request(webhook_url, data=data, headers=headers, method="POST")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: urlopen(req, timeout=10),
            )
            return True

        except Exception as e:
            logger.error(f"Teams notification error: {e}")
            return False


class MQTTNotifier:
    """Sends alerts via MQTT."""

    async def send(
        self,
        alert: Alert,
        config: NotificationConfig,
    ) -> bool:
        """Send MQTT notification."""
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            logger.warning("paho-mqtt not installed, MQTT notifications unavailable")
            return False

        try:
            broker = config.config.get("broker", "localhost")
            port = config.config.get("port", 1883)
            topic = config.config.get("topic", "croom/alerts")
            username = config.config.get("username")
            password = config.config.get("password")
            use_tls = config.config.get("use_tls", False)

            client = mqtt.Client()
            if username and password:
                client.username_pw_set(username, password)
            if use_tls:
                client.tls_set()

            # Connect and publish
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._mqtt_publish(client, broker, port, topic, alert),
            )
            return True

        except Exception as e:
            logger.error(f"MQTT notification error: {e}")
            return False

    def _mqtt_publish(
        self,
        client,
        broker: str,
        port: int,
        topic: str,
        alert: Alert,
    ) -> None:
        """Publish MQTT message synchronously."""
        client.connect(broker, port, 60)
        payload = json.dumps(alert.to_dict())
        client.publish(topic, payload, qos=1)
        client.disconnect()


class AlertManager:
    """Manages alert rules, evaluation, and notifications."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        on_alert: Optional[Callable[[Alert], None]] = None,
    ):
        """
        Initialize alert manager.

        Args:
            storage_path: Path to store alert state
            on_alert: Callback for alert state changes
        """
        self._storage_path = storage_path or Path("/var/lib/croom/alerts")
        self._on_alert = on_alert

        # Rules and alerts
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._max_history = 1000

        # Pending alerts (for duration evaluation)
        self._pending: Dict[str, datetime] = {}

        # Silences
        self._silences: Dict[str, AlertSilence] = {}

        # Notification channels
        self._channels: Dict[str, NotificationConfig] = {}

        # Notifiers
        self._notifiers = {
            NotificationChannel.WEBHOOK: WebhookNotifier(),
            NotificationChannel.EMAIL: EmailNotifier(),
            NotificationChannel.SLACK: SlackNotifier(),
            NotificationChannel.TEAMS: TeamsNotifier(),
            NotificationChannel.MQTT: MQTTNotifier(),
        }

        # Callback notifiers
        self._callback_handlers: Dict[str, Callable[[Alert], None]] = {}

        # Rate limiting
        self._notification_interval = timedelta(minutes=5)

        # Load default rules
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default alert rules."""
        default_rules = [
            AlertRule(
                id="cpu_high",
                name="High CPU Usage",
                description="CPU usage is above 90%",
                metric_name="cpu_usage_percent",
                operator=ComparisonOperator.GT,
                threshold=90,
                severity=AlertSeverity.WARNING,
                duration=60,
            ),
            AlertRule(
                id="cpu_critical",
                name="Critical CPU Usage",
                description="CPU usage is above 95%",
                metric_name="cpu_usage_percent",
                operator=ComparisonOperator.GT,
                threshold=95,
                severity=AlertSeverity.CRITICAL,
                duration=30,
            ),
            AlertRule(
                id="memory_high",
                name="High Memory Usage",
                description="Memory usage is above 85%",
                metric_name="memory_usage_percent",
                operator=ComparisonOperator.GT,
                threshold=85,
                severity=AlertSeverity.WARNING,
                duration=60,
            ),
            AlertRule(
                id="memory_critical",
                name="Critical Memory Usage",
                description="Memory usage is above 95%",
                metric_name="memory_usage_percent",
                operator=ComparisonOperator.GT,
                threshold=95,
                severity=AlertSeverity.CRITICAL,
                duration=30,
            ),
            AlertRule(
                id="disk_high",
                name="High Disk Usage",
                description="Disk usage is above 80%",
                metric_name="disk_usage_percent",
                operator=ComparisonOperator.GT,
                threshold=80,
                severity=AlertSeverity.WARNING,
            ),
            AlertRule(
                id="disk_critical",
                name="Critical Disk Usage",
                description="Disk usage is above 95%",
                metric_name="disk_usage_percent",
                operator=ComparisonOperator.GT,
                threshold=95,
                severity=AlertSeverity.CRITICAL,
            ),
            AlertRule(
                id="temperature_high",
                name="High Temperature",
                description="CPU temperature is above 70°C",
                metric_name="cpu_temperature_celsius",
                operator=ComparisonOperator.GT,
                threshold=70,
                severity=AlertSeverity.WARNING,
                duration=120,
            ),
            AlertRule(
                id="temperature_critical",
                name="Critical Temperature",
                description="CPU temperature is above 80°C",
                metric_name="cpu_temperature_celsius",
                operator=ComparisonOperator.GT,
                threshold=80,
                severity=AlertSeverity.CRITICAL,
                duration=60,
            ),
        ]

        for rule in default_rules:
            self._rules[rule.id] = rule

    def add_rule(self, rule: AlertRule) -> None:
        """Add or update an alert rule."""
        self._rules[rule.id] = rule
        logger.info(f"Alert rule added: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.info(f"Alert rule removed: {rule_id}")
            return True
        return False

    def get_rules(self) -> List[AlertRule]:
        """Get all alert rules."""
        return list(self._rules.values())

    def add_channel(self, channel: NotificationConfig) -> None:
        """Add a notification channel."""
        self._channels[channel.id] = channel
        logger.info(f"Notification channel added: {channel.name}")

    def remove_channel(self, channel_id: str) -> bool:
        """Remove a notification channel."""
        if channel_id in self._channels:
            del self._channels[channel_id]
            return True
        return False

    def get_channels(self) -> List[NotificationConfig]:
        """Get all notification channels."""
        return list(self._channels.values())

    def add_callback_handler(
        self,
        handler_id: str,
        handler: Callable[[Alert], None],
    ) -> None:
        """Add a callback handler for alerts."""
        self._callback_handlers[handler_id] = handler

    def remove_callback_handler(self, handler_id: str) -> None:
        """Remove a callback handler."""
        self._callback_handlers.pop(handler_id, None)

    def add_silence(self, silence: AlertSilence) -> None:
        """Add a silence rule."""
        self._silences[silence.id] = silence
        logger.info(f"Silence added: {silence.id}")

    def remove_silence(self, silence_id: str) -> bool:
        """Remove a silence rule."""
        if silence_id in self._silences:
            del self._silences[silence_id]
            return True
        return False

    def get_silences(self) -> List[AlertSilence]:
        """Get all active silences."""
        return [s for s in self._silences.values() if s.is_active()]

    async def evaluate(self, metrics: Dict[str, float]) -> List[Alert]:
        """
        Evaluate all rules against current metrics.

        Args:
            metrics: Dictionary of metric name to value

        Returns:
            List of alerts that changed state
        """
        changed_alerts = []
        now = datetime.utcnow()

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            if rule.metric_name not in metrics:
                continue

            value = metrics[rule.metric_name]
            condition_met = rule.evaluate(value)
            alert_id = self._get_alert_id(rule)

            if condition_met:
                # Check duration requirement
                if rule.duration > 0:
                    if alert_id not in self._pending:
                        self._pending[alert_id] = now
                        continue

                    elapsed = (now - self._pending[alert_id]).total_seconds()
                    if elapsed < rule.duration:
                        continue

                # Clear pending
                self._pending.pop(alert_id, None)

                # Create or update alert
                if alert_id not in self._active_alerts:
                    alert = Alert(
                        id=alert_id,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        state=AlertState.FIRING,
                        message=f"{rule.description}. Current: {value:.1f}, Threshold: {rule.threshold}",
                        value=value,
                        threshold=rule.threshold,
                        labels=rule.labels.copy(),
                        annotations=rule.annotations.copy(),
                    )

                    # Check silences
                    for silence in self._silences.values():
                        if silence.matches(alert):
                            alert.state = AlertState.SILENCED
                            break

                    self._active_alerts[alert_id] = alert
                    changed_alerts.append(alert)

                    if self._on_alert:
                        self._on_alert(alert)

                else:
                    # Update existing alert value
                    alert = self._active_alerts[alert_id]
                    alert.value = value
                    alert.message = f"{rule.description}. Current: {value:.1f}, Threshold: {rule.threshold}"

            else:
                # Clear pending
                self._pending.pop(alert_id, None)

                # Resolve alert if active
                if alert_id in self._active_alerts:
                    alert = self._active_alerts.pop(alert_id)
                    alert.state = AlertState.RESOLVED
                    alert.resolved_at = now

                    # Store in history
                    self._alert_history.append(alert)
                    if len(self._alert_history) > self._max_history:
                        self._alert_history = self._alert_history[-self._max_history:]

                    changed_alerts.append(alert)

                    if self._on_alert:
                        self._on_alert(alert)

        return changed_alerts

    def _get_alert_id(self, rule: AlertRule) -> str:
        """Generate alert ID from rule."""
        label_str = json.dumps(rule.labels, sort_keys=True)
        hash_input = f"{rule.id}:{label_str}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    async def send_notifications(self, alerts: List[Alert]) -> None:
        """Send notifications for alerts."""
        for alert in alerts:
            # Skip silenced alerts
            if alert.state == AlertState.SILENCED:
                continue

            # Rate limiting
            if alert.last_notification:
                elapsed = datetime.utcnow() - alert.last_notification
                if elapsed < self._notification_interval:
                    continue

            # Send to all matching channels
            for channel in self._channels.values():
                if not channel.enabled:
                    continue

                # Check severity filter
                severity_order = {
                    AlertSeverity.INFO: 0,
                    AlertSeverity.WARNING: 1,
                    AlertSeverity.CRITICAL: 2,
                }
                if severity_order[alert.severity] < severity_order[channel.min_severity]:
                    continue

                # Check label filters
                if channel.labels_filter:
                    match = True
                    for key, value in channel.labels_filter.items():
                        if alert.labels.get(key) != value:
                            match = False
                            break
                    if not match:
                        continue

                # Send notification
                if channel.channel_type in self._notifiers:
                    notifier = self._notifiers[channel.channel_type]
                    success = await notifier.send(alert, channel)
                    if success:
                        alert.last_notification = datetime.utcnow()
                        alert.notification_count += 1

            # Send to callback handlers
            for handler in self._callback_handlers.values():
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Callback handler error: {e}")

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self._active_alerts.values())

    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None,
    ) -> List[Alert]:
        """Get alert history."""
        history = self._alert_history
        if severity:
            history = [a for a in history if a.severity == severity]
        return history[-limit:]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert (clears notification rate limit)."""
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.last_notification = None
            return True
        return False

    def get_summary(self) -> Dict[str, Any]:
        """Get alert summary."""
        active = self.get_active_alerts()

        return {
            "total_active": len(active),
            "by_severity": {
                "critical": len([a for a in active if a.severity == AlertSeverity.CRITICAL]),
                "warning": len([a for a in active if a.severity == AlertSeverity.WARNING]),
                "info": len([a for a in active if a.severity == AlertSeverity.INFO]),
            },
            "by_state": {
                "firing": len([a for a in active if a.state == AlertState.FIRING]),
                "silenced": len([a for a in active if a.state == AlertState.SILENCED]),
            },
            "rules_count": len(self._rules),
            "channels_count": len(self._channels),
            "silences_count": len(self.get_silences()),
        }


class AlertingService:
    """Main alerting service that integrates with monitoring."""

    def __init__(
        self,
        alert_manager: AlertManager,
        evaluation_interval: int = 30,
    ):
        """
        Initialize alerting service.

        Args:
            alert_manager: Alert manager instance
            evaluation_interval: Seconds between evaluations
        """
        self._manager = alert_manager
        self._interval = evaluation_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._latest_metrics: Dict[str, float] = {}

    async def start(self) -> None:
        """Start the alerting service."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._evaluation_loop())
        logger.info("Alerting service started")

    async def stop(self) -> None:
        """Stop the alerting service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Alerting service stopped")

    async def _evaluation_loop(self) -> None:
        """Main evaluation loop."""
        while self._running:
            try:
                if self._latest_metrics:
                    alerts = await self._manager.evaluate(self._latest_metrics)
                    if alerts:
                        await self._manager.send_notifications(alerts)
            except Exception as e:
                logger.error(f"Alert evaluation error: {e}")

            await asyncio.sleep(self._interval)

    def update_metrics(self, metrics: Dict[str, float]) -> None:
        """Update metrics for evaluation."""
        self._latest_metrics.update(metrics)

    @property
    def manager(self) -> AlertManager:
        """Get the alert manager."""
        return self._manager


def create_alerting_service(
    config: Dict[str, Any],
    storage_path: Optional[Path] = None,
) -> AlertingService:
    """
    Create alerting service from configuration.

    Args:
        config: Configuration dictionary
        storage_path: Optional storage path

    Returns:
        Configured alerting service
    """
    manager = AlertManager(storage_path=storage_path)

    # Add custom rules
    for rule_config in config.get("rules", []):
        rule = AlertRule(
            id=rule_config["id"],
            name=rule_config["name"],
            description=rule_config.get("description", ""),
            metric_name=rule_config["metric_name"],
            operator=ComparisonOperator(rule_config["operator"]),
            threshold=rule_config["threshold"],
            severity=AlertSeverity(rule_config.get("severity", "warning")),
            duration=rule_config.get("duration", 0),
            labels=rule_config.get("labels", {}),
            annotations=rule_config.get("annotations", {}),
            enabled=rule_config.get("enabled", True),
        )
        manager.add_rule(rule)

    # Add notification channels
    for channel_config in config.get("channels", []):
        channel = NotificationConfig(
            id=channel_config["id"],
            name=channel_config["name"],
            channel_type=NotificationChannel(channel_config["type"]),
            config=channel_config.get("config", {}),
            enabled=channel_config.get("enabled", True),
            min_severity=AlertSeverity(channel_config.get("min_severity", "warning")),
            labels_filter=channel_config.get("labels_filter", {}),
        )
        manager.add_channel(channel)

    return AlertingService(
        alert_manager=manager,
        evaluation_interval=config.get("evaluation_interval", 30),
    )

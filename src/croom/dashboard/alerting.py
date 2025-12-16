"""
Alerting system for Croom dashboard.

Provides multi-channel alerting with email, Slack, SMS, and webhook support.
"""

import asyncio
import hashlib
import json
import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"
    TEAMS = "teams"
    PAGERDUTY = "pagerduty"


class AlertState(Enum):
    """Alert state."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SNOOZED = "snoozed"


@dataclass
class AlertRule:
    """Alert rule definition."""
    id: str
    name: str
    description: str = ""
    condition: str = ""  # Expression like "cpu_percent > 90"
    severity: AlertSeverity = AlertSeverity.WARNING
    channels: List[AlertChannel] = field(default_factory=list)
    cooldown_seconds: int = 300  # Minimum time between alerts
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    device_filter: Optional[str] = None  # Filter by device pattern

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "condition": self.condition,
            "severity": self.severity.value,
            "channels": [c.value for c in self.channels],
            "cooldown_seconds": self.cooldown_seconds,
            "enabled": self.enabled,
            "tags": self.tags,
            "device_filter": self.device_filter,
        }


@dataclass
class Alert:
    """Alert instance."""
    id: str
    rule_id: str
    device_id: str
    severity: AlertSeverity
    title: str
    message: str
    state: AlertState = AlertState.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "device_id": self.device_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
            "data": self.data,
        }


class AlertNotifier(ABC):
    """Base class for alert notifiers."""

    @property
    @abstractmethod
    def channel(self) -> AlertChannel:
        """Get channel type."""
        pass

    @abstractmethod
    async def send(self, alert: Alert, rule: AlertRule) -> bool:
        """Send alert notification."""
        pass


class EmailNotifier(AlertNotifier):
    """Email alert notifier using SMTP."""

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        from_address: str = "alerts@croom.to",
        to_addresses: Optional[List[str]] = None,
        use_tls: bool = True,
    ):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._from_address = from_address
        self._to_addresses = to_addresses or []
        self._use_tls = use_tls

    @property
    def channel(self) -> AlertChannel:
        return AlertChannel.EMAIL

    async def send(self, alert: Alert, rule: AlertRule) -> bool:
        """Send email alert."""
        if not self._to_addresses:
            logger.warning("No email recipients configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            msg['From'] = self._from_address
            msg['To'] = ', '.join(self._to_addresses)

            # Plain text version
            text_content = f"""
Croom Alert

Severity: {alert.severity.value.upper()}
Device: {alert.device_id}
Title: {alert.title}

{alert.message}

Time: {alert.created_at.isoformat()}
Rule: {rule.name}
Alert ID: {alert.id}
"""

            # HTML version
            severity_color = {
                AlertSeverity.INFO: "#3498db",
                AlertSeverity.WARNING: "#f39c12",
                AlertSeverity.CRITICAL: "#e74c3c",
            }.get(alert.severity, "#333")

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        .alert-box {{ border-left: 4px solid {severity_color}; padding: 15px; background: #f9f9f9; }}
        .severity {{ color: {severity_color}; font-weight: bold; text-transform: uppercase; }}
        .details {{ margin-top: 15px; font-size: 14px; color: #666; }}
    </style>
</head>
<body>
    <h2>Croom Alert</h2>
    <div class="alert-box">
        <p class="severity">{alert.severity.value}</p>
        <h3>{alert.title}</h3>
        <p>{alert.message}</p>
    </div>
    <div class="details">
        <p><strong>Device:</strong> {alert.device_id}</p>
        <p><strong>Time:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p><strong>Rule:</strong> {rule.name}</p>
        <p><strong>Alert ID:</strong> {alert.id}</p>
    </div>
</body>
</html>
"""

            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            # Send email
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp, msg)

            logger.info(f"Email alert sent to {len(self._to_addresses)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def _send_smtp(self, msg: MIMEMultipart) -> None:
        """Send email via SMTP (blocking)."""
        with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
            if self._use_tls:
                server.starttls()
            if self._username and self._password:
                server.login(self._username, self._password)
            server.send_message(msg)


class SlackNotifier(AlertNotifier):
    """Slack webhook alert notifier."""

    def __init__(self, webhook_url: str, channel: str = ""):
        self._webhook_url = webhook_url
        self._channel = channel

    @property
    def channel(self) -> AlertChannel:
        return AlertChannel.SLACK

    async def send(self, alert: Alert, rule: AlertRule) -> bool:
        """Send Slack alert."""
        try:
            import aiohttp

            color = {
                AlertSeverity.INFO: "#3498db",
                AlertSeverity.WARNING: "#f39c12",
                AlertSeverity.CRITICAL: "#e74c3c",
            }.get(alert.severity, "#333")

            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"[{alert.severity.value.upper()}] {alert.title}",
                        "text": alert.message,
                        "fields": [
                            {"title": "Device", "value": alert.device_id, "short": True},
                            {"title": "Rule", "value": rule.name, "short": True},
                            {"title": "Time", "value": alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'), "short": True},
                            {"title": "Alert ID", "value": alert.id, "short": True},
                        ],
                        "footer": "Croom Dashboard",
                        "ts": int(alert.created_at.timestamp()),
                    }
                ]
            }

            if self._channel:
                payload["channel"] = self._channel

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        logger.info("Slack alert sent successfully")
                        return True
                    else:
                        logger.error(f"Slack webhook error: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False


class TeamsNotifier(AlertNotifier):
    """Microsoft Teams webhook alert notifier."""

    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    @property
    def channel(self) -> AlertChannel:
        return AlertChannel.TEAMS

    async def send(self, alert: Alert, rule: AlertRule) -> bool:
        """Send Teams alert."""
        try:
            import aiohttp

            color = {
                AlertSeverity.INFO: "0078D7",
                AlertSeverity.WARNING: "FFC107",
                AlertSeverity.CRITICAL: "DC3545",
            }.get(alert.severity, "333333")

            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": color,
                "summary": f"[{alert.severity.value.upper()}] {alert.title}",
                "sections": [
                    {
                        "activityTitle": f"[{alert.severity.value.upper()}] {alert.title}",
                        "facts": [
                            {"name": "Device", "value": alert.device_id},
                            {"name": "Rule", "value": rule.name},
                            {"name": "Time", "value": alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')},
                            {"name": "Alert ID", "value": alert.id},
                        ],
                        "text": alert.message,
                        "markdown": True,
                    }
                ],
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status in (200, 201):
                        logger.info("Teams alert sent successfully")
                        return True
                    else:
                        logger.error(f"Teams webhook error: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Teams alert: {e}")
            return False


class SMSNotifier(AlertNotifier):
    """SMS alert notifier using Twilio."""

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_numbers: Optional[List[str]] = None,
    ):
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number
        self._to_numbers = to_numbers or []

    @property
    def channel(self) -> AlertChannel:
        return AlertChannel.SMS

    async def send(self, alert: Alert, rule: AlertRule) -> bool:
        """Send SMS alert via Twilio."""
        if not self._to_numbers:
            logger.warning("No SMS recipients configured")
            return False

        try:
            import aiohttp

            message = (
                f"[{alert.severity.value.upper()}] {alert.title}\n"
                f"Device: {alert.device_id}\n"
                f"{alert.message[:100]}..."
            )

            success_count = 0

            for to_number in self._to_numbers:
                try:
                    async with aiohttp.ClientSession() as session:
                        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._account_sid}/Messages.json"
                        auth = aiohttp.BasicAuth(self._account_sid, self._auth_token)

                        async with session.post(
                            url,
                            auth=auth,
                            data={
                                "From": self._from_number,
                                "To": to_number,
                                "Body": message,
                            },
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as response:
                            if response.status == 201:
                                success_count += 1
                            else:
                                logger.error(f"Twilio error for {to_number}: {response.status}")

                except Exception as e:
                    logger.error(f"SMS error for {to_number}: {e}")

            logger.info(f"SMS alerts sent: {success_count}/{len(self._to_numbers)}")
            return success_count > 0

        except Exception as e:
            logger.error(f"Failed to send SMS alerts: {e}")
            return False


class WebhookNotifier(AlertNotifier):
    """Generic webhook alert notifier."""

    def __init__(
        self,
        url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        secret: str = "",
    ):
        self._url = url
        self._method = method.upper()
        self._headers = headers or {}
        self._secret = secret

    @property
    def channel(self) -> AlertChannel:
        return AlertChannel.WEBHOOK

    async def send(self, alert: Alert, rule: AlertRule) -> bool:
        """Send webhook alert."""
        try:
            import aiohttp

            payload = {
                "alert": alert.to_dict(),
                "rule": rule.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            headers = self._headers.copy()
            headers["Content-Type"] = "application/json"

            # Add HMAC signature if secret is configured
            if self._secret:
                payload_bytes = json.dumps(payload).encode('utf-8')
                import hmac
                signature = hmac.new(
                    self._secret.encode('utf-8'),
                    payload_bytes,
                    hashlib.sha256,
                ).hexdigest()
                headers["X-Croom-Signature"] = f"sha256={signature}"

            async with aiohttp.ClientSession() as session:
                if self._method == "POST":
                    async with session.post(
                        self._url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response:
                        if response.status in (200, 201, 204):
                            logger.info("Webhook alert sent successfully")
                            return True
                        else:
                            logger.error(f"Webhook error: {response.status}")
                            return False

        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False


class PagerDutyNotifier(AlertNotifier):
    """PagerDuty alert notifier."""

    def __init__(self, routing_key: str):
        self._routing_key = routing_key

    @property
    def channel(self) -> AlertChannel:
        return AlertChannel.PAGERDUTY

    async def send(self, alert: Alert, rule: AlertRule) -> bool:
        """Send PagerDuty alert."""
        try:
            import aiohttp

            severity_map = {
                AlertSeverity.INFO: "info",
                AlertSeverity.WARNING: "warning",
                AlertSeverity.CRITICAL: "critical",
            }

            payload = {
                "routing_key": self._routing_key,
                "event_action": "trigger",
                "dedup_key": f"{alert.rule_id}:{alert.device_id}",
                "payload": {
                    "summary": f"[{alert.severity.value.upper()}] {alert.title}",
                    "source": alert.device_id,
                    "severity": severity_map.get(alert.severity, "warning"),
                    "custom_details": {
                        "message": alert.message,
                        "device_id": alert.device_id,
                        "rule": rule.name,
                        "alert_id": alert.id,
                    },
                },
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 202:
                        logger.info("PagerDuty alert sent successfully")
                        return True
                    else:
                        logger.error(f"PagerDuty error: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")
            return False


class AlertManager:
    """
    Central alert management service.

    Handles alert rules, deduplication, and notification dispatch.
    """

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._notifiers: Dict[AlertChannel, AlertNotifier] = {}
        self._cooldowns: Dict[str, datetime] = {}  # rule_id:device_id -> last_alert_time
        self._callbacks: List[Callable[[Alert], None]] = []

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._rules[rule.id] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get rule by ID."""
        return self._rules.get(rule_id)

    def get_rules(self) -> List[AlertRule]:
        """Get all rules."""
        return list(self._rules.values())

    def add_notifier(self, notifier: AlertNotifier) -> None:
        """Add a notifier."""
        self._notifiers[notifier.channel] = notifier
        logger.info(f"Added notifier: {notifier.channel.value}")

    def on_alert(self, callback: Callable[[Alert], None]) -> None:
        """Register callback for new alerts."""
        self._callbacks.append(callback)

    async def check_condition(
        self,
        rule_id: str,
        device_id: str,
        metrics: Dict[str, Any],
    ) -> Optional[Alert]:
        """
        Check if an alert condition is met.

        Args:
            rule_id: Alert rule ID
            device_id: Device ID
            metrics: Current metrics dictionary

        Returns:
            Alert if condition is met, None otherwise
        """
        rule = self._rules.get(rule_id)
        if not rule or not rule.enabled:
            return None

        # Check device filter
        if rule.device_filter and rule.device_filter not in device_id:
            return None

        # Evaluate condition
        try:
            # Simple expression evaluation
            # Supports: <metric> <op> <value>
            condition = rule.condition
            result = self._evaluate_condition(condition, metrics)

            if not result:
                return None

        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")
            return None

        # Check cooldown
        cooldown_key = f"{rule_id}:{device_id}"
        last_alert = self._cooldowns.get(cooldown_key)

        if last_alert:
            elapsed = (datetime.now(timezone.utc) - last_alert).total_seconds()
            if elapsed < rule.cooldown_seconds:
                return None

        # Create alert
        alert_id = hashlib.sha256(
            f"{rule_id}:{device_id}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]

        alert = Alert(
            id=alert_id,
            rule_id=rule_id,
            device_id=device_id,
            severity=rule.severity,
            title=rule.name,
            message=self._format_message(rule, metrics),
            data=metrics.copy(),
        )

        self._alerts[alert_id] = alert
        self._cooldowns[cooldown_key] = datetime.now(timezone.utc)

        # Send notifications
        await self._send_notifications(alert, rule)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        return alert

    def _evaluate_condition(self, condition: str, metrics: Dict[str, Any]) -> bool:
        """Evaluate a simple condition expression."""
        # Parse condition like "cpu_percent > 90"
        import re

        match = re.match(r'(\w+)\s*(>|<|>=|<=|==|!=)\s*(\d+\.?\d*)', condition)
        if not match:
            return False

        metric_name, operator, threshold = match.groups()
        threshold = float(threshold)

        value = metrics.get(metric_name)
        if value is None:
            return False

        value = float(value)

        operators = {
            '>': lambda a, b: a > b,
            '<': lambda a, b: a < b,
            '>=': lambda a, b: a >= b,
            '<=': lambda a, b: a <= b,
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
        }

        return operators.get(operator, lambda a, b: False)(value, threshold)

    def _format_message(self, rule: AlertRule, metrics: Dict[str, Any]) -> str:
        """Format alert message with metrics."""
        message = rule.description or f"Alert triggered: {rule.condition}"

        # Replace metric placeholders
        for key, value in metrics.items():
            message = message.replace(f"{{{key}}}", str(value))

        return message

    async def _send_notifications(self, alert: Alert, rule: AlertRule) -> None:
        """Send alert to all configured channels."""
        for channel in rule.channels:
            notifier = self._notifiers.get(channel)
            if notifier:
                try:
                    await notifier.send(alert, rule)
                except Exception as e:
                    logger.error(f"Notification error for {channel.value}: {e}")
            else:
                logger.warning(f"No notifier configured for {channel.value}")

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False

        alert.state = AlertState.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = acknowledged_by
        alert.updated_at = datetime.now(timezone.utc)
        return True

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False

        alert.state = AlertState.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        alert.updated_at = datetime.now(timezone.utc)
        return True

    async def snooze_alert(self, alert_id: str, duration_minutes: int) -> bool:
        """Snooze an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False

        alert.state = AlertState.SNOOZED
        alert.snoozed_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        alert.updated_at = datetime.now(timezone.utc)
        return True

    def get_alerts(
        self,
        state: Optional[AlertState] = None,
        severity: Optional[AlertSeverity] = None,
        device_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Alert]:
        """Get alerts with optional filters."""
        alerts = list(self._alerts.values())

        if state:
            alerts = [a for a in alerts if a.state == state]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if device_id:
            alerts = [a for a in alerts if a.device_id == device_id]

        # Sort by created_at descending
        alerts.sort(key=lambda a: a.created_at, reverse=True)

        return alerts[:limit]

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        return self._alerts.get(alert_id)

    def get_active_count(self) -> int:
        """Get count of active alerts."""
        return sum(1 for a in self._alerts.values() if a.state == AlertState.ACTIVE)

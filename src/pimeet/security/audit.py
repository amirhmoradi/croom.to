"""
Audit logging for PiMeet.

Provides comprehensive security event logging with tamper detection.
"""

import asyncio
import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
import gzip
import shutil

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_SESSION_CREATED = "auth.session.created"
    AUTH_SESSION_EXPIRED = "auth.session.expired"
    AUTH_SESSION_INVALIDATED = "auth.session.invalidated"
    AUTH_MFA_ENABLED = "auth.mfa.enabled"
    AUTH_MFA_DISABLED = "auth.mfa.disabled"
    AUTH_MFA_SUCCESS = "auth.mfa.success"
    AUTH_MFA_FAILURE = "auth.mfa.failure"
    AUTH_PASSWORD_CHANGED = "auth.password.changed"
    AUTH_PASSWORD_RESET = "auth.password.reset"

    # Authorization events
    AUTHZ_ACCESS_GRANTED = "authz.access.granted"
    AUTHZ_ACCESS_DENIED = "authz.access.denied"
    AUTHZ_ROLE_ASSIGNED = "authz.role.assigned"
    AUTHZ_ROLE_REVOKED = "authz.role.revoked"
    AUTHZ_ROLE_CREATED = "authz.role.created"
    AUTHZ_ROLE_MODIFIED = "authz.role.modified"
    AUTHZ_ROLE_DELETED = "authz.role.deleted"

    # Credential events
    CRED_ACCESS = "credential.access"
    CRED_CREATED = "credential.created"
    CRED_MODIFIED = "credential.modified"
    CRED_DELETED = "credential.deleted"
    CRED_ROTATED = "credential.rotated"
    CRED_REVOKED = "credential.revoked"

    # Device events
    DEVICE_REGISTERED = "device.registered"
    DEVICE_MODIFIED = "device.modified"
    DEVICE_DELETED = "device.deleted"
    DEVICE_ONLINE = "device.online"
    DEVICE_OFFLINE = "device.offline"
    DEVICE_REBOOTED = "device.rebooted"
    DEVICE_UPDATED = "device.updated"
    DEVICE_CONFIG_CHANGED = "device.config.changed"

    # Meeting events
    MEETING_JOINED = "meeting.joined"
    MEETING_LEFT = "meeting.left"
    MEETING_STARTED = "meeting.started"
    MEETING_ENDED = "meeting.ended"

    # User management events
    USER_CREATED = "user.created"
    USER_MODIFIED = "user.modified"
    USER_DELETED = "user.deleted"
    USER_LOCKED = "user.locked"
    USER_UNLOCKED = "user.unlocked"

    # Settings events
    SETTINGS_CHANGED = "settings.changed"
    SETTINGS_VIEWED = "settings.viewed"

    # API events
    API_KEY_CREATED = "api.key.created"
    API_KEY_REVOKED = "api.key.revoked"
    API_REQUEST = "api.request"
    API_RATE_LIMITED = "api.rate_limited"

    # Security events
    SECURITY_ALERT = "security.alert"
    SECURITY_THREAT_DETECTED = "security.threat.detected"
    SECURITY_POLICY_VIOLATION = "security.policy.violation"
    SECURITY_AUDIT_EXPORT = "security.audit.export"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_BACKUP = "system.backup"


class AuditSeverity(Enum):
    """Audit event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditActor:
    """
    Actor who performed an action.

    Attributes:
        actor_type: Type of actor (user, service, device, system)
        actor_id: Unique identifier
        display_name: Human-readable name
        ip_address: IP address of actor
        user_agent: User agent string
        session_id: Session ID (if applicable)
    """
    actor_type: str
    actor_id: str
    display_name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "type": self.actor_type,
            "id": self.actor_id,
            "display_name": self.display_name,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
        }


@dataclass
class AuditResource:
    """
    Resource that was acted upon.

    Attributes:
        resource_type: Type of resource
        resource_id: Unique identifier
        display_name: Human-readable name
        metadata: Additional resource metadata
    """
    resource_type: str
    resource_id: str
    display_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        result = {
            "type": self.resource_type,
            "id": self.resource_id,
        }
        if self.display_name:
            result["display_name"] = self.display_name
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class AuditEvent:
    """
    An audit event.

    Attributes:
        event_id: Unique event identifier
        event_type: Type of event
        timestamp: When event occurred
        actor: Who performed the action
        resource: What was acted upon
        action: The action performed
        result: Outcome (success/failure)
        severity: Event severity
        details: Additional details
        metadata: Event metadata
        previous_hash: Hash of previous event (for chain integrity)
        event_hash: Hash of this event
    """
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    actor: Optional[AuditActor]
    resource: Optional[AuditResource]
    action: str
    result: str  # "success" or "failure"
    severity: AuditSeverity = AuditSeverity.INFO
    details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    previous_hash: Optional[str] = None
    event_hash: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat() + "Z",
            "actor": self.actor.to_dict() if self.actor else None,
            "resource": self.resource.to_dict() if self.resource else None,
            "action": self.action,
            "result": self.result,
            "severity": self.severity.value,
            "details": self.details,
            "metadata": self.metadata,
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=None, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEvent":
        """Deserialize from dictionary."""
        actor = None
        if data.get("actor"):
            actor = AuditActor(
                actor_type=data["actor"]["type"],
                actor_id=data["actor"]["id"],
                display_name=data["actor"].get("display_name"),
                ip_address=data["actor"].get("ip_address"),
                user_agent=data["actor"].get("user_agent"),
                session_id=data["actor"].get("session_id"),
            )

        resource = None
        if data.get("resource"):
            resource = AuditResource(
                resource_type=data["resource"]["type"],
                resource_id=data["resource"]["id"],
                display_name=data["resource"].get("display_name"),
                metadata=data["resource"].get("metadata", {}),
            )

        return cls(
            event_id=data["event_id"],
            event_type=AuditEventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"].rstrip("Z")),
            actor=actor,
            resource=resource,
            action=data["action"],
            result=data["result"],
            severity=AuditSeverity(data.get("severity", "info")),
            details=data.get("details", {}),
            metadata=data.get("metadata", {}),
            previous_hash=data.get("previous_hash"),
            event_hash=data.get("event_hash"),
        )


class AuditLogWriter:
    """
    Writes audit events to storage.

    Supports multiple output formats and destinations.
    """

    def __init__(
        self,
        log_path: Path,
        rotate_size_mb: int = 100,
        compress_rotated: bool = True,
        retention_days: int = 365,
    ):
        """
        Initialize audit log writer.

        Args:
            log_path: Directory for audit logs
            rotate_size_mb: Rotate log when it reaches this size
            compress_rotated: Compress rotated logs
            retention_days: Days to retain logs
        """
        self._log_path = Path(log_path)
        self._log_path.mkdir(parents=True, exist_ok=True)
        self._rotate_size = rotate_size_mb * 1024 * 1024
        self._compress = compress_rotated
        self._retention_days = retention_days

        # Current log file
        self._current_log = self._log_path / "audit.log"
        self._file_handle = None
        self._lock = asyncio.Lock()

        # Last event hash for chain integrity
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        """Load the hash of the last event."""
        hash_file = self._log_path / ".last_hash"

        if hash_file.exists():
            try:
                return hash_file.read_text().strip()
            except Exception:
                pass

        # Generate initial hash
        return hashlib.sha256(b"AUDIT_LOG_INIT").hexdigest()

    def _save_last_hash(self, hash_value: str) -> None:
        """Save the hash of the last event."""
        hash_file = self._log_path / ".last_hash"
        hash_file.write_text(hash_value)

    def _compute_event_hash(self, event: AuditEvent) -> str:
        """Compute hash for an event."""
        # Hash includes all event data plus previous hash
        data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "actor": event.actor.to_dict() if event.actor else None,
            "resource": event.resource.to_dict() if event.resource else None,
            "action": event.action,
            "result": event.result,
            "details": event.details,
            "previous_hash": event.previous_hash,
        }

        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    async def write(self, event: AuditEvent) -> bool:
        """
        Write an audit event.

        Args:
            event: Event to write

        Returns:
            True if written successfully
        """
        async with self._lock:
            try:
                # Set chain integrity fields
                event.previous_hash = self._last_hash
                event.event_hash = self._compute_event_hash(event)

                # Check if rotation needed
                await self._check_rotation()

                # Write event
                event_json = event.to_json() + "\n"

                with open(self._current_log, 'a') as f:
                    f.write(event_json)

                # Update last hash
                self._last_hash = event.event_hash
                self._save_last_hash(self._last_hash)

                return True

            except Exception as e:
                logger.error(f"Failed to write audit event: {e}")
                return False

    async def _check_rotation(self) -> None:
        """Check if log rotation is needed."""
        if not self._current_log.exists():
            return

        if self._current_log.stat().st_size < self._rotate_size:
            return

        # Rotate log
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        rotated_name = f"audit_{timestamp}.log"
        rotated_path = self._log_path / rotated_name

        # Move current log
        shutil.move(self._current_log, rotated_path)

        # Compress if enabled
        if self._compress:
            with open(rotated_path, 'rb') as f_in:
                with gzip.open(f"{rotated_path}.gz", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            rotated_path.unlink()

        logger.info(f"Rotated audit log: {rotated_name}")

        # Cleanup old logs
        await self._cleanup_old_logs()

    async def _cleanup_old_logs(self) -> None:
        """Remove logs older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self._retention_days)

        for log_file in self._log_path.glob("audit_*.log*"):
            try:
                # Parse timestamp from filename
                parts = log_file.stem.replace("audit_", "").split("_")
                if len(parts) >= 2:
                    file_date = datetime.strptime(
                        f"{parts[0]}_{parts[1].split('.')[0]}",
                        "%Y%m%d_%H%M%S"
                    )

                    if file_date < cutoff:
                        log_file.unlink()
                        logger.info(f"Deleted old audit log: {log_file.name}")

            except Exception as e:
                logger.warning(f"Error cleaning up {log_file}: {e}")


class SIEMExporter:
    """
    Export audit events to SIEM systems.

    Supports multiple SIEM formats and protocols.
    """

    def __init__(
        self,
        endpoint: str,
        format: str = "json",
        auth_token: Optional[str] = None,
    ):
        """
        Initialize SIEM exporter.

        Args:
            endpoint: SIEM endpoint URL
            format: Export format (json, cef, leef)
            auth_token: Authentication token
        """
        self._endpoint = endpoint
        self._format = format
        self._auth_token = auth_token

    async def export(self, event: AuditEvent) -> bool:
        """Export an event to SIEM."""
        try:
            if self._format == "cef":
                data = self._to_cef(event)
            elif self._format == "leef":
                data = self._to_leef(event)
            else:
                data = event.to_json()

            # Send to SIEM
            import aiohttp

            headers = {"Content-Type": "application/json"}
            if self._auth_token:
                headers["Authorization"] = f"Bearer {self._auth_token}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._endpoint,
                    data=data,
                    headers=headers,
                ) as response:
                    return response.status < 400

        except Exception as e:
            logger.error(f"SIEM export error: {e}")
            return False

    def _to_cef(self, event: AuditEvent) -> str:
        """Convert event to CEF format."""
        severity_map = {
            AuditSeverity.INFO: 1,
            AuditSeverity.WARNING: 5,
            AuditSeverity.ERROR: 8,
            AuditSeverity.CRITICAL: 10,
        }

        cef = (
            f"CEF:0|PiMeet|Enterprise|1.0|{event.event_type.value}|"
            f"{event.action}|{severity_map.get(event.severity, 1)}|"
            f"rt={int(event.timestamp.timestamp() * 1000)} "
            f"eventId={event.event_id} "
            f"outcome={event.result}"
        )

        if event.actor:
            cef += f" suser={event.actor.actor_id}"
            if event.actor.ip_address:
                cef += f" src={event.actor.ip_address}"

        if event.resource:
            cef += f" destinationServiceName={event.resource.resource_type}"
            cef += f" duid={event.resource.resource_id}"

        return cef

    def _to_leef(self, event: AuditEvent) -> str:
        """Convert event to LEEF format."""
        leef = (
            f"LEEF:2.0|PiMeet|Enterprise|1.0|{event.event_type.value}|"
            f"devTime={event.timestamp.isoformat()}\t"
            f"eventId={event.event_id}\t"
            f"action={event.action}\t"
            f"outcome={event.result}"
        )

        if event.actor:
            leef += f"\tusrName={event.actor.actor_id}"
            if event.actor.ip_address:
                leef += f"\tsrc={event.actor.ip_address}"

        return leef


class AuditLogger:
    """
    Main audit logging service.

    Provides a high-level API for logging security events.
    """

    def __init__(
        self,
        log_path: Path,
        siem_exporter: Optional[SIEMExporter] = None,
        alert_callbacks: Optional[List[Callable[[AuditEvent], None]]] = None,
    ):
        """
        Initialize audit logger.

        Args:
            log_path: Path for audit log storage
            siem_exporter: Optional SIEM exporter
            alert_callbacks: Optional alert callbacks
        """
        self._writer = AuditLogWriter(log_path)
        self._siem = siem_exporter
        self._alert_callbacks = alert_callbacks or []

        # Alert thresholds
        self._failed_logins: Dict[str, List[datetime]] = {}
        self._alert_threshold = 5
        self._alert_window = timedelta(minutes=10)

    async def log(
        self,
        event_type: AuditEventType,
        action: str,
        result: str = "success",
        actor: Optional[AuditActor] = None,
        resource: Optional[AuditResource] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            action: Action description
            result: Outcome (success/failure)
            actor: Actor who performed action
            resource: Resource acted upon
            severity: Event severity
            details: Additional details
            metadata: Event metadata

        Returns:
            Created AuditEvent
        """
        event = AuditEvent(
            event_id=secrets.token_hex(16),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            actor=actor,
            resource=resource,
            action=action,
            result=result,
            severity=severity,
            details=details or {},
            metadata=metadata or {},
        )

        # Write to log
        await self._writer.write(event)

        # Export to SIEM
        if self._siem:
            asyncio.create_task(self._siem.export(event))

        # Check for alerts
        await self._check_alerts(event)

        return event

    async def log_authentication(
        self,
        success: bool,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> AuditEvent:
        """Log an authentication event."""
        event_type = (
            AuditEventType.AUTH_LOGIN_SUCCESS if success
            else AuditEventType.AUTH_LOGIN_FAILURE
        )

        actor = AuditActor(
            actor_type="user",
            actor_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        details = {}
        if reason:
            details["reason"] = reason

        return await self.log(
            event_type=event_type,
            action="login",
            result="success" if success else "failure",
            actor=actor,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            details=details,
        )

    async def log_credential_access(
        self,
        credential_id: str,
        credential_type: str,
        accessor_id: str,
        accessor_ip: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> AuditEvent:
        """Log a credential access event."""
        return await self.log(
            event_type=AuditEventType.CRED_ACCESS,
            action="access",
            result="success",
            actor=AuditActor(
                actor_type="user",
                actor_id=accessor_id,
                ip_address=accessor_ip,
            ),
            resource=AuditResource(
                resource_type="credential",
                resource_id=credential_id,
                metadata={"credential_type": credential_type},
            ),
            details={"reason": reason} if reason else {},
        )

    async def log_device_event(
        self,
        device_id: str,
        device_name: str,
        event_type: AuditEventType,
        action: str,
        actor_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log a device event."""
        actor = None
        if actor_id:
            actor = AuditActor(actor_type="user", actor_id=actor_id)

        return await self.log(
            event_type=event_type,
            action=action,
            result="success",
            actor=actor,
            resource=AuditResource(
                resource_type="device",
                resource_id=device_id,
                display_name=device_name,
            ),
            details=details or {},
        )

    async def log_access_decision(
        self,
        user_id: str,
        permission: str,
        allowed: bool,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> AuditEvent:
        """Log an access control decision."""
        event_type = (
            AuditEventType.AUTHZ_ACCESS_GRANTED if allowed
            else AuditEventType.AUTHZ_ACCESS_DENIED
        )

        resource = None
        if resource_type:
            resource = AuditResource(
                resource_type=resource_type,
                resource_id=resource_id or "any",
            )

        return await self.log(
            event_type=event_type,
            action=f"check:{permission}",
            result="granted" if allowed else "denied",
            actor=AuditActor(actor_type="user", actor_id=user_id),
            resource=resource,
            severity=AuditSeverity.INFO if allowed else AuditSeverity.WARNING,
        )

    async def log_security_alert(
        self,
        alert_type: str,
        description: str,
        severity: AuditSeverity = AuditSeverity.WARNING,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log a security alert."""
        return await self.log(
            event_type=AuditEventType.SECURITY_ALERT,
            action=alert_type,
            result="alert",
            severity=severity,
            details={"description": description, **(details or {})},
        )

    async def _check_alerts(self, event: AuditEvent) -> None:
        """Check if event should trigger an alert."""
        # Check for brute force attempts
        if event.event_type == AuditEventType.AUTH_LOGIN_FAILURE:
            if event.actor:
                await self._check_brute_force(event.actor.actor_id)

        # Trigger alert callbacks for high-severity events
        if event.severity in (AuditSeverity.ERROR, AuditSeverity.CRITICAL):
            for callback in self._alert_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")

    async def _check_brute_force(self, user_id: str) -> None:
        """Check for brute force login attempts."""
        now = datetime.utcnow()

        # Clean old entries
        if user_id in self._failed_logins:
            self._failed_logins[user_id] = [
                t for t in self._failed_logins[user_id]
                if now - t < self._alert_window
            ]
        else:
            self._failed_logins[user_id] = []

        # Add current failure
        self._failed_logins[user_id].append(now)

        # Check threshold
        if len(self._failed_logins[user_id]) >= self._alert_threshold:
            await self.log_security_alert(
                alert_type="brute_force_attempt",
                description=f"Multiple failed login attempts for user {user_id}",
                severity=AuditSeverity.WARNING,
                details={
                    "user_id": user_id,
                    "attempt_count": len(self._failed_logins[user_id]),
                    "window_minutes": self._alert_window.total_seconds() / 60,
                },
            )

    async def query(
        self,
        event_types: Optional[List[AuditEventType]] = None,
        actor_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """
        Query audit events.

        Args:
            event_types: Filter by event types
            actor_id: Filter by actor
            resource_id: Filter by resource
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum events to return

        Returns:
            List of matching events
        """
        events = []

        # Read from current log
        log_file = self._writer._current_log
        if not log_file.exists():
            return events

        with open(log_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                    event = AuditEvent.from_dict(data)

                    # Apply filters
                    if event_types and event.event_type not in event_types:
                        continue
                    if actor_id and (not event.actor or event.actor.actor_id != actor_id):
                        continue
                    if resource_id and (not event.resource or event.resource.resource_id != resource_id):
                        continue
                    if start_time and event.timestamp < start_time:
                        continue
                    if end_time and event.timestamp > end_time:
                        continue

                    events.append(event)

                    if len(events) >= limit:
                        break

                except Exception as e:
                    logger.warning(f"Error parsing audit event: {e}")

        return events

    async def export(
        self,
        output_path: Path,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format: str = "json",
    ) -> int:
        """
        Export audit events to file.

        Args:
            output_path: Output file path
            start_time: Start of time range
            end_time: End of time range
            format: Output format (json, csv)

        Returns:
            Number of events exported
        """
        events = await self.query(start_time=start_time, end_time=end_time, limit=100000)

        if format == "csv":
            import csv
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "event_type", "action", "result",
                    "actor_id", "actor_ip", "resource_type", "resource_id",
                    "severity", "details",
                ])
                for event in events:
                    writer.writerow([
                        event.timestamp.isoformat(),
                        event.event_type.value,
                        event.action,
                        event.result,
                        event.actor.actor_id if event.actor else "",
                        event.actor.ip_address if event.actor else "",
                        event.resource.resource_type if event.resource else "",
                        event.resource.resource_id if event.resource else "",
                        event.severity.value,
                        json.dumps(event.details),
                    ])
        else:
            with open(output_path, 'w') as f:
                for event in events:
                    f.write(event.to_json() + "\n")

        # Log the export
        await self.log(
            event_type=AuditEventType.SECURITY_AUDIT_EXPORT,
            action="export",
            result="success",
            details={
                "event_count": len(events),
                "format": format,
                "output_path": str(output_path),
            },
        )

        return len(events)


def create_audit_logger(config: Dict[str, Any]) -> AuditLogger:
    """
    Create an audit logger from configuration.

    Args:
        config: Audit logger configuration

    Returns:
        Configured AuditLogger instance
    """
    log_path = Path(config.get("log_path", "/var/log/pimeet/audit"))

    siem_exporter = None
    if config.get("siem_endpoint"):
        siem_exporter = SIEMExporter(
            endpoint=config["siem_endpoint"],
            format=config.get("siem_format", "json"),
            auth_token=config.get("siem_auth_token"),
        )

    return AuditLogger(
        log_path=log_path,
        siem_exporter=siem_exporter,
    )

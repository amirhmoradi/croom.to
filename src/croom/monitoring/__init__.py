"""
Monitoring service for Croom.

Provides real-time device health monitoring and metrics collection.
"""

import asyncio
import logging
import os
import psutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    GAUGE = "gauge"  # Current value
    COUNTER = "counter"  # Cumulative count
    HISTOGRAM = "histogram"  # Distribution


class HealthStatus(Enum):
    """Device health status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class Metric:
    """A metric data point."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "unit": self.unit,
        }


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class SystemMetricsCollector:
    """Collects system metrics from the device."""

    def __init__(self):
        self._boot_time = psutil.boot_time()

    async def collect(self) -> List[Metric]:
        """Collect all system metrics."""
        metrics = []

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        metrics.append(Metric(
            name="cpu_usage_percent",
            value=cpu_percent,
            metric_type=MetricType.GAUGE,
            unit="percent",
        ))

        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            metrics.append(Metric(
                name="cpu_frequency_mhz",
                value=cpu_freq.current,
                metric_type=MetricType.GAUGE,
                unit="MHz",
            ))

        # Memory metrics
        memory = psutil.virtual_memory()
        metrics.extend([
            Metric(
                name="memory_total_bytes",
                value=memory.total,
                metric_type=MetricType.GAUGE,
                unit="bytes",
            ),
            Metric(
                name="memory_used_bytes",
                value=memory.used,
                metric_type=MetricType.GAUGE,
                unit="bytes",
            ),
            Metric(
                name="memory_usage_percent",
                value=memory.percent,
                metric_type=MetricType.GAUGE,
                unit="percent",
            ),
        ])

        # Disk metrics
        disk = psutil.disk_usage('/')
        metrics.extend([
            Metric(
                name="disk_total_bytes",
                value=disk.total,
                metric_type=MetricType.GAUGE,
                unit="bytes",
            ),
            Metric(
                name="disk_used_bytes",
                value=disk.used,
                metric_type=MetricType.GAUGE,
                unit="bytes",
            ),
            Metric(
                name="disk_usage_percent",
                value=disk.percent,
                metric_type=MetricType.GAUGE,
                unit="percent",
            ),
        ])

        # Temperature (Raspberry Pi specific)
        temp = self._get_cpu_temperature()
        if temp is not None:
            metrics.append(Metric(
                name="cpu_temperature_celsius",
                value=temp,
                metric_type=MetricType.GAUGE,
                unit="celsius",
            ))

        # Network metrics
        net_io = psutil.net_io_counters()
        metrics.extend([
            Metric(
                name="network_bytes_sent",
                value=net_io.bytes_sent,
                metric_type=MetricType.COUNTER,
                unit="bytes",
            ),
            Metric(
                name="network_bytes_recv",
                value=net_io.bytes_recv,
                metric_type=MetricType.COUNTER,
                unit="bytes",
            ),
        ])

        # Uptime
        uptime = time.time() - self._boot_time
        metrics.append(Metric(
            name="system_uptime_seconds",
            value=uptime,
            metric_type=MetricType.GAUGE,
            unit="seconds",
        ))

        # Process count
        metrics.append(Metric(
            name="process_count",
            value=len(psutil.pids()),
            metric_type=MetricType.GAUGE,
        ))

        return metrics

    def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature (Pi-specific)."""
        try:
            # Raspberry Pi thermal zone
            temp_path = Path("/sys/class/thermal/thermal_zone0/temp")
            if temp_path.exists():
                temp = int(temp_path.read_text().strip())
                return temp / 1000.0
        except Exception:
            pass

        try:
            # Try psutil sensors
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        return entries[0].current
        except Exception:
            pass

        return None


class NetworkMetricsCollector:
    """Collects network connectivity metrics."""

    def __init__(self):
        self._test_hosts = [
            ("8.8.8.8", "Google DNS"),
            ("1.1.1.1", "Cloudflare DNS"),
        ]

    async def collect(self) -> List[Metric]:
        """Collect network metrics."""
        metrics = []

        # Network interfaces
        interfaces = psutil.net_if_stats()
        for name, stats in interfaces.items():
            if name == "lo":
                continue

            metrics.append(Metric(
                name="network_interface_up",
                value=1 if stats.isup else 0,
                metric_type=MetricType.GAUGE,
                labels={"interface": name},
            ))

            if stats.speed > 0:
                metrics.append(Metric(
                    name="network_interface_speed_mbps",
                    value=stats.speed,
                    metric_type=MetricType.GAUGE,
                    labels={"interface": name},
                    unit="Mbps",
                ))

        # WiFi signal strength (if available)
        wifi_signal = await self._get_wifi_signal()
        if wifi_signal is not None:
            metrics.append(Metric(
                name="wifi_signal_dbm",
                value=wifi_signal,
                metric_type=MetricType.GAUGE,
                unit="dBm",
            ))

        # Latency to test hosts
        for host, label in self._test_hosts:
            latency = await self._measure_latency(host)
            if latency is not None:
                metrics.append(Metric(
                    name="network_latency_ms",
                    value=latency,
                    metric_type=MetricType.GAUGE,
                    labels={"target": label},
                    unit="ms",
                ))

        return metrics

    async def _get_wifi_signal(self) -> Optional[float]:
        """Get WiFi signal strength."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "iwconfig", "wlan0",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode()

            for line in output.split('\n'):
                if "Signal level" in line:
                    # Parse: "Signal level=-50 dBm"
                    parts = line.split("Signal level=")
                    if len(parts) > 1:
                        value = parts[1].split()[0]
                        return float(value.replace("dBm", ""))
        except Exception:
            pass
        return None

    async def _measure_latency(self, host: str) -> Optional[float]:
        """Measure network latency to host."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "-W", "2", host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                output = stdout.decode()
                # Parse: "time=10.5 ms"
                for part in output.split():
                    if part.startswith("time="):
                        return float(part[5:])
        except Exception:
            pass
        return None


class MeetingMetricsCollector:
    """Collects meeting-related metrics."""

    def __init__(self):
        self._meeting_start_time: Optional[datetime] = None
        self._total_meetings = 0
        self._total_meeting_minutes = 0

    def on_meeting_started(self) -> None:
        """Called when a meeting starts."""
        self._meeting_start_time = datetime.utcnow()
        self._total_meetings += 1

    def on_meeting_ended(self) -> None:
        """Called when a meeting ends."""
        if self._meeting_start_time:
            duration = datetime.utcnow() - self._meeting_start_time
            self._total_meeting_minutes += duration.total_seconds() / 60
            self._meeting_start_time = None

    async def collect(self) -> List[Metric]:
        """Collect meeting metrics."""
        metrics = []

        # Meeting state
        in_meeting = 1 if self._meeting_start_time else 0
        metrics.append(Metric(
            name="meeting_active",
            value=in_meeting,
            metric_type=MetricType.GAUGE,
        ))

        # Current meeting duration
        if self._meeting_start_time:
            duration = (datetime.utcnow() - self._meeting_start_time).total_seconds()
            metrics.append(Metric(
                name="meeting_duration_seconds",
                value=duration,
                metric_type=MetricType.GAUGE,
                unit="seconds",
            ))

        # Totals
        metrics.extend([
            Metric(
                name="meetings_total",
                value=self._total_meetings,
                metric_type=MetricType.COUNTER,
            ),
            Metric(
                name="meeting_minutes_total",
                value=self._total_meeting_minutes,
                metric_type=MetricType.COUNTER,
                unit="minutes",
            ),
        ])

        return metrics


class HealthChecker:
    """Performs health checks on device components."""

    def __init__(self):
        self._thresholds = {
            "cpu_percent": {"warning": 80, "critical": 95},
            "memory_percent": {"warning": 85, "critical": 95},
            "disk_percent": {"warning": 80, "critical": 95},
            "temperature": {"warning": 70, "critical": 80},
        }

    async def check_all(self) -> List[HealthCheck]:
        """Perform all health checks."""
        checks = []

        checks.append(await self._check_cpu())
        checks.append(await self._check_memory())
        checks.append(await self._check_disk())
        checks.append(await self._check_temperature())
        checks.append(await self._check_network())
        checks.append(await self._check_services())
        checks.append(await self._check_audio())
        checks.append(await self._check_video())

        return checks

    async def _check_cpu(self) -> HealthCheck:
        """Check CPU health."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        thresholds = self._thresholds["cpu_percent"]

        if cpu_percent >= thresholds["critical"]:
            status = HealthStatus.CRITICAL
            message = f"CPU usage critical: {cpu_percent}%"
        elif cpu_percent >= thresholds["warning"]:
            status = HealthStatus.WARNING
            message = f"CPU usage high: {cpu_percent}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"CPU usage normal: {cpu_percent}%"

        return HealthCheck(
            name="cpu",
            status=status,
            message=message,
            details={"usage_percent": cpu_percent},
        )

    async def _check_memory(self) -> HealthCheck:
        """Check memory health."""
        memory = psutil.virtual_memory()
        thresholds = self._thresholds["memory_percent"]

        if memory.percent >= thresholds["critical"]:
            status = HealthStatus.CRITICAL
            message = f"Memory usage critical: {memory.percent}%"
        elif memory.percent >= thresholds["warning"]:
            status = HealthStatus.WARNING
            message = f"Memory usage high: {memory.percent}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Memory usage normal: {memory.percent}%"

        return HealthCheck(
            name="memory",
            status=status,
            message=message,
            details={
                "usage_percent": memory.percent,
                "available_mb": memory.available / (1024 * 1024),
            },
        )

    async def _check_disk(self) -> HealthCheck:
        """Check disk health."""
        disk = psutil.disk_usage('/')
        thresholds = self._thresholds["disk_percent"]

        if disk.percent >= thresholds["critical"]:
            status = HealthStatus.CRITICAL
            message = f"Disk usage critical: {disk.percent}%"
        elif disk.percent >= thresholds["warning"]:
            status = HealthStatus.WARNING
            message = f"Disk usage high: {disk.percent}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Disk usage normal: {disk.percent}%"

        return HealthCheck(
            name="disk",
            status=status,
            message=message,
            details={
                "usage_percent": disk.percent,
                "free_gb": disk.free / (1024 * 1024 * 1024),
            },
        )

    async def _check_temperature(self) -> HealthCheck:
        """Check temperature health."""
        temp = self._get_temperature()
        thresholds = self._thresholds["temperature"]

        if temp is None:
            return HealthCheck(
                name="temperature",
                status=HealthStatus.UNKNOWN,
                message="Temperature sensor not available",
            )

        if temp >= thresholds["critical"]:
            status = HealthStatus.CRITICAL
            message = f"Temperature critical: {temp}°C"
        elif temp >= thresholds["warning"]:
            status = HealthStatus.WARNING
            message = f"Temperature high: {temp}°C"
        else:
            status = HealthStatus.HEALTHY
            message = f"Temperature normal: {temp}°C"

        return HealthCheck(
            name="temperature",
            status=status,
            message=message,
            details={"celsius": temp},
        )

    def _get_temperature(self) -> Optional[float]:
        """Get CPU temperature."""
        try:
            temp_path = Path("/sys/class/thermal/thermal_zone0/temp")
            if temp_path.exists():
                return int(temp_path.read_text().strip()) / 1000.0
        except Exception:
            pass
        return None

    async def _check_network(self) -> HealthCheck:
        """Check network connectivity."""
        # Check if any interface is up
        interfaces = psutil.net_if_stats()
        active_interfaces = [
            name for name, stats in interfaces.items()
            if stats.isup and name != "lo"
        ]

        if not active_interfaces:
            return HealthCheck(
                name="network",
                status=HealthStatus.CRITICAL,
                message="No active network interfaces",
            )

        # Check internet connectivity
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "-W", "2", "8.8.8.8",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()

            if proc.returncode == 0:
                return HealthCheck(
                    name="network",
                    status=HealthStatus.HEALTHY,
                    message="Network connected",
                    details={"interfaces": active_interfaces},
                )
            else:
                return HealthCheck(
                    name="network",
                    status=HealthStatus.WARNING,
                    message="Local network up, no internet",
                    details={"interfaces": active_interfaces},
                )
        except Exception:
            return HealthCheck(
                name="network",
                status=HealthStatus.WARNING,
                message="Could not verify internet connectivity",
            )

    async def _check_services(self) -> HealthCheck:
        """Check Croom services."""
        services = ["croom-agent", "croom-browser"]
        running = []
        stopped = []

        for service in services:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "systemctl", "is-active", service,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await proc.communicate()
                if stdout.decode().strip() == "active":
                    running.append(service)
                else:
                    stopped.append(service)
            except Exception:
                stopped.append(service)

        if stopped:
            return HealthCheck(
                name="services",
                status=HealthStatus.WARNING,
                message=f"Services stopped: {', '.join(stopped)}",
                details={"running": running, "stopped": stopped},
            )

        return HealthCheck(
            name="services",
            status=HealthStatus.HEALTHY,
            message="All services running",
            details={"running": running},
        )

    async def _check_audio(self) -> HealthCheck:
        """Check audio devices."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "pactl", "list", "sources", "short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0 and stdout:
                sources = [
                    line.split()[1]
                    for line in stdout.decode().strip().split('\n')
                    if line and not line.endswith('.monitor')
                ]
                return HealthCheck(
                    name="audio",
                    status=HealthStatus.HEALTHY,
                    message=f"Audio devices available: {len(sources)}",
                    details={"sources": sources[:5]},  # Limit to 5
                )
        except Exception:
            pass

        return HealthCheck(
            name="audio",
            status=HealthStatus.WARNING,
            message="Could not enumerate audio devices",
        )

    async def _check_video(self) -> HealthCheck:
        """Check video devices."""
        video_devices = list(Path("/dev").glob("video*"))

        if video_devices:
            return HealthCheck(
                name="video",
                status=HealthStatus.HEALTHY,
                message=f"Video devices available: {len(video_devices)}",
                details={"devices": [d.name for d in video_devices]},
            )

        return HealthCheck(
            name="video",
            status=HealthStatus.WARNING,
            message="No video devices found",
        )


class MonitoringService:
    """Main monitoring service that coordinates collectors."""

    def __init__(
        self,
        collection_interval: int = 30,
        on_metrics: Optional[Callable[[List[Metric]], None]] = None,
        on_health: Optional[Callable[[List[HealthCheck]], None]] = None,
    ):
        """
        Initialize monitoring service.

        Args:
            collection_interval: Seconds between collections
            on_metrics: Callback for metrics
            on_health: Callback for health checks
        """
        self._interval = collection_interval
        self._on_metrics = on_metrics
        self._on_health = on_health
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Collectors
        self._system_collector = SystemMetricsCollector()
        self._network_collector = NetworkMetricsCollector()
        self._meeting_collector = MeetingMetricsCollector()
        self._health_checker = HealthChecker()

        # Metrics history (last 24 hours)
        self._metrics_history: List[Dict[str, Any]] = []
        self._max_history = 2880  # 24 hours at 30-second intervals

    async def start(self) -> None:
        """Start the monitoring service."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
        logger.info("Monitoring service started")

    async def stop(self) -> None:
        """Stop the monitoring service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring service stopped")

    async def _collection_loop(self) -> None:
        """Main collection loop."""
        while self._running:
            try:
                # Collect metrics
                metrics = []
                metrics.extend(await self._system_collector.collect())
                metrics.extend(await self._network_collector.collect())
                metrics.extend(await self._meeting_collector.collect())

                # Store in history
                self._store_metrics(metrics)

                # Callback
                if self._on_metrics:
                    self._on_metrics(metrics)

                # Health checks (less frequent)
                health_checks = await self._health_checker.check_all()
                if self._on_health:
                    self._on_health(health_checks)

            except Exception as e:
                logger.error(f"Monitoring collection error: {e}")

            await asyncio.sleep(self._interval)

    def _store_metrics(self, metrics: List[Metric]) -> None:
        """Store metrics in history."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {m.name: m.value for m in metrics},
        }
        self._metrics_history.append(snapshot)

        # Trim history
        if len(self._metrics_history) > self._max_history:
            self._metrics_history = self._metrics_history[-self._max_history:]

    async def collect_now(self) -> Dict[str, Any]:
        """Collect metrics immediately."""
        metrics = []
        metrics.extend(await self._system_collector.collect())
        metrics.extend(await self._network_collector.collect())
        metrics.extend(await self._meeting_collector.collect())

        health_checks = await self._health_checker.check_all()

        # Overall health status
        statuses = [h.status for h in health_checks]
        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": overall_status.value,
            "metrics": [m.to_dict() for m in metrics],
            "health_checks": [h.to_dict() for h in health_checks],
        }

    def get_metrics_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get metrics history within time range."""
        if not start_time and not end_time:
            return self._metrics_history

        result = []
        for snapshot in self._metrics_history:
            ts = datetime.fromisoformat(snapshot["timestamp"])
            if start_time and ts < start_time:
                continue
            if end_time and ts > end_time:
                continue
            result.append(snapshot)

        return result

    @property
    def meeting_collector(self) -> MeetingMetricsCollector:
        """Get meeting collector for event notifications."""
        return self._meeting_collector


def create_monitoring_service(config: Dict[str, Any]) -> MonitoringService:
    """Create monitoring service from configuration."""
    return MonitoringService(
        collection_interval=config.get("collection_interval", 30),
    )


# Re-export from submodules
from .alerting import (
    AlertSeverity,
    AlertState,
    AlertRule,
    Alert,
    AlertSilence,
    NotificationChannel,
    NotificationConfig,
    AlertManager,
    AlertingService,
    create_alerting_service,
)

from .remote_ops import (
    OperationType,
    OperationStatus,
    Operation,
    DiagnosticResult,
    DiagnosticRunner,
    LogCollector,
    UpdateManager,
    RemoteOperationsService,
    create_remote_ops_service,
)

from .analytics import (
    TimeRange,
    AggregationType,
    MeetingStats,
    DeviceStats,
    FleetStats,
    MetricsStore,
    AnalyticsEngine,
    ReportGenerator,
    AnalyticsService,
    create_analytics_service,
)

__all__ = [
    # Core monitoring
    "MetricType",
    "HealthStatus",
    "Metric",
    "HealthCheck",
    "SystemMetricsCollector",
    "NetworkMetricsCollector",
    "MeetingMetricsCollector",
    "HealthChecker",
    "MonitoringService",
    "create_monitoring_service",
    # Alerting
    "AlertSeverity",
    "AlertState",
    "AlertRule",
    "Alert",
    "AlertSilence",
    "NotificationChannel",
    "NotificationConfig",
    "AlertManager",
    "AlertingService",
    "create_alerting_service",
    # Remote operations
    "OperationType",
    "OperationStatus",
    "Operation",
    "DiagnosticResult",
    "DiagnosticRunner",
    "LogCollector",
    "UpdateManager",
    "RemoteOperationsService",
    "create_remote_ops_service",
    # Analytics
    "TimeRange",
    "AggregationType",
    "MeetingStats",
    "DeviceStats",
    "FleetStats",
    "MetricsStore",
    "AnalyticsEngine",
    "ReportGenerator",
    "AnalyticsService",
    "create_analytics_service",
]

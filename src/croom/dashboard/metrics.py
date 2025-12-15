"""
Metrics collection for Croom dashboard.

Collects system and application metrics for reporting.
"""

import asyncio
import logging
import os
import platform
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DeviceMetrics:
    """Device metrics snapshot."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # System
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_total_mb: float = 0.0
    memory_used_mb: float = 0.0
    disk_percent: float = 0.0
    temperature_c: Optional[float] = None
    uptime_seconds: float = 0.0

    # Network
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0

    # Meeting
    is_in_meeting: bool = False
    meeting_duration_seconds: float = 0.0
    meeting_platform: str = ""

    # Audio/Video
    microphone_active: bool = False
    camera_active: bool = False
    audio_level: float = 0.0
    video_fps: float = 0.0

    # AI
    ai_backend: str = ""
    ai_inference_time_ms: float = 0.0
    people_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class MetricsCollector:
    """
    Collects device and application metrics.

    Periodically samples system state for dashboard reporting.
    """

    def __init__(self, interval: float = 10.0):
        """
        Initialize metrics collector.

        Args:
            interval: Collection interval in seconds
        """
        self._interval = interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Latest metrics
        self._current: DeviceMetrics = DeviceMetrics()
        self._history: List[DeviceMetrics] = []
        self._history_max = 360  # 1 hour at 10s interval

        # Meeting state (set externally)
        self._meeting_active = False
        self._meeting_start: Optional[datetime] = None
        self._meeting_platform = ""

        # Audio/Video state
        self._mic_active = False
        self._camera_active = False
        self._audio_level = 0.0
        self._video_fps = 0.0

        # AI state
        self._ai_backend = ""
        self._ai_inference_ms = 0.0
        self._people_count = 0

        # Network tracking
        self._last_net_rx = 0
        self._last_net_tx = 0

    async def start(self) -> None:
        """Start metrics collection."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._collect_loop())
        logger.info(f"Metrics collection started (interval: {self._interval}s)")

    async def stop(self) -> None:
        """Stop metrics collection."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Metrics collection stopped")

    async def _collect_loop(self) -> None:
        """Background collection loop."""
        while self._running:
            try:
                await self._collect()
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(self._interval)

    async def _collect(self) -> None:
        """Collect current metrics."""
        loop = asyncio.get_event_loop()

        # Collect system metrics in thread pool (blocking calls)
        metrics = await loop.run_in_executor(None, self._collect_system_metrics)

        # Add application state
        metrics.is_in_meeting = self._meeting_active
        metrics.meeting_platform = self._meeting_platform
        if self._meeting_active and self._meeting_start:
            dt = datetime.now(timezone.utc) - self._meeting_start
            metrics.meeting_duration_seconds = dt.total_seconds()

        metrics.microphone_active = self._mic_active
        metrics.camera_active = self._camera_active
        metrics.audio_level = self._audio_level
        metrics.video_fps = self._video_fps

        metrics.ai_backend = self._ai_backend
        metrics.ai_inference_time_ms = self._ai_inference_ms
        metrics.people_count = self._people_count

        self._current = metrics

        # Add to history
        self._history.append(metrics)
        while len(self._history) > self._history_max:
            self._history.pop(0)

    def _collect_system_metrics(self) -> DeviceMetrics:
        """Collect system metrics (runs in thread pool)."""
        metrics = DeviceMetrics()

        try:
            # CPU usage
            metrics.cpu_percent = self._get_cpu_percent()

            # Memory
            mem = self._get_memory_info()
            metrics.memory_percent = mem['percent']
            metrics.memory_total_mb = mem['total_mb']
            metrics.memory_used_mb = mem['used_mb']

            # Disk
            metrics.disk_percent = self._get_disk_percent()

            # Temperature (Pi specific)
            metrics.temperature_c = self._get_temperature()

            # Uptime
            metrics.uptime_seconds = self._get_uptime()

            # Network
            net = self._get_network_stats()
            metrics.network_rx_bytes = net['rx']
            metrics.network_tx_bytes = net['tx']

        except Exception as e:
            logger.error(f"System metrics error: {e}")

        return metrics

    def _get_cpu_percent(self) -> float:
        """Get CPU usage percentage."""
        try:
            # Read /proc/stat
            with open('/proc/stat', 'r') as f:
                line = f.readline()

            parts = line.split()
            user = int(parts[1])
            nice = int(parts[2])
            system = int(parts[3])
            idle = int(parts[4])

            total = user + nice + system + idle
            busy = user + nice + system

            # Simple estimate (more accurate would need delta)
            return (busy / total) * 100 if total > 0 else 0

        except Exception:
            return 0.0

    def _get_memory_info(self) -> Dict[str, float]:
        """Get memory information."""
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()

            mem = {}
            for line in lines:
                parts = line.split()
                key = parts[0].rstrip(':')
                value = int(parts[1])  # kB
                mem[key] = value

            total = mem.get('MemTotal', 0) / 1024  # MB
            available = mem.get('MemAvailable', mem.get('MemFree', 0)) / 1024
            used = total - available
            percent = (used / total * 100) if total > 0 else 0

            return {
                'total_mb': total,
                'used_mb': used,
                'percent': percent,
            }

        except Exception:
            return {'total_mb': 0, 'used_mb': 0, 'percent': 0}

    def _get_disk_percent(self) -> float:
        """Get disk usage percentage."""
        try:
            stat = os.statvfs('/')
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            return (used / total * 100) if total > 0 else 0

        except Exception:
            return 0.0

    def _get_temperature(self) -> Optional[float]:
        """Get CPU temperature (Raspberry Pi)."""
        try:
            # Try Pi thermal zone
            temp_file = Path('/sys/class/thermal/thermal_zone0/temp')
            if temp_file.exists():
                with open(temp_file, 'r') as f:
                    temp_millic = int(f.read().strip())
                return temp_millic / 1000.0

            # Try vcgencmd
            import subprocess
            result = subprocess.run(
                ['vcgencmd', 'measure_temp'],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0:
                # Parse "temp=45.0'C"
                temp_str = result.stdout.strip()
                temp = float(temp_str.split('=')[1].rstrip("'C"))
                return temp

        except Exception:
            pass

        return None

    def _get_uptime(self) -> float:
        """Get system uptime in seconds."""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime = float(f.read().split()[0])
            return uptime
        except Exception:
            return 0.0

    def _get_network_stats(self) -> Dict[str, int]:
        """Get network statistics."""
        try:
            rx_total = 0
            tx_total = 0

            # Read /proc/net/dev
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()[2:]  # Skip headers

            for line in lines:
                parts = line.split()
                iface = parts[0].rstrip(':')

                # Skip loopback
                if iface == 'lo':
                    continue

                rx_total += int(parts[1])
                tx_total += int(parts[9])

            return {'rx': rx_total, 'tx': tx_total}

        except Exception:
            return {'rx': 0, 'tx': 0}

    # Public setters for application state

    def set_meeting_state(
        self,
        active: bool,
        platform: str = "",
        start_time: Optional[datetime] = None
    ) -> None:
        """Update meeting state."""
        self._meeting_active = active
        self._meeting_platform = platform
        self._meeting_start = start_time if active else None

    def set_audio_state(self, active: bool, level: float = 0.0) -> None:
        """Update audio state."""
        self._mic_active = active
        self._audio_level = level

    def set_video_state(self, active: bool, fps: float = 0.0) -> None:
        """Update video state."""
        self._camera_active = active
        self._video_fps = fps

    def set_ai_state(
        self,
        backend: str,
        inference_ms: float = 0.0,
        people_count: int = 0
    ) -> None:
        """Update AI state."""
        self._ai_backend = backend
        self._ai_inference_ms = inference_ms
        self._people_count = people_count

    @property
    def current(self) -> DeviceMetrics:
        """Get current metrics."""
        return self._current

    @property
    def history(self) -> List[DeviceMetrics]:
        """Get metrics history."""
        return self._history.copy()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics from history."""
        if not self._history:
            return {}

        cpu_values = [m.cpu_percent for m in self._history]
        mem_values = [m.memory_percent for m in self._history]
        temp_values = [m.temperature_c for m in self._history if m.temperature_c]

        return {
            'cpu_avg': sum(cpu_values) / len(cpu_values),
            'cpu_max': max(cpu_values),
            'mem_avg': sum(mem_values) / len(mem_values),
            'mem_max': max(mem_values),
            'temp_avg': sum(temp_values) / len(temp_values) if temp_values else None,
            'temp_max': max(temp_values) if temp_values else None,
            'sample_count': len(self._history),
        }

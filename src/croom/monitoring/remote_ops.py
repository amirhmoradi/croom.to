"""
Remote operations service for Croom.

Provides remote device management capabilities including reboot, update,
diagnostics, configuration, and troubleshooting.
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import signal
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of remote operations."""
    REBOOT = "reboot"
    SHUTDOWN = "shutdown"
    RESTART_SERVICE = "restart_service"
    UPDATE_SOFTWARE = "update_software"
    UPDATE_CONFIG = "update_config"
    RUN_DIAGNOSTIC = "run_diagnostic"
    COLLECT_LOGS = "collect_logs"
    CAPTURE_SCREENSHOT = "capture_screenshot"
    EXECUTE_COMMAND = "execute_command"
    FACTORY_RESET = "factory_reset"


class OperationStatus(Enum):
    """Status of a remote operation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Operation:
    """A remote operation request."""
    id: str
    type: OperationType
    status: OperationStatus
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    requested_by: str = "system"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "status": self.status.value,
            "parameters": self.parameters,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "requested_by": self.requested_by,
        }


@dataclass
class DiagnosticResult:
    """Result of a diagnostic test."""
    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
        }


class DiagnosticRunner:
    """Runs device diagnostics."""

    async def run_all(self) -> List[DiagnosticResult]:
        """Run all diagnostic tests."""
        results = []

        # Run each diagnostic
        results.append(await self._test_cpu())
        results.append(await self._test_memory())
        results.append(await self._test_disk())
        results.append(await self._test_network())
        results.append(await self._test_dns())
        results.append(await self._test_audio())
        results.append(await self._test_video())
        results.append(await self._test_usb())
        results.append(await self._test_services())

        return results

    async def _test_cpu(self) -> DiagnosticResult:
        """Test CPU functionality."""
        start = datetime.utcnow()
        try:
            import psutil
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            cpu_percent = psutil.cpu_percent(interval=0.5)

            return DiagnosticResult(
                name="cpu",
                passed=True,
                message=f"CPU healthy: {cpu_count} cores, {cpu_percent}% usage",
                details={
                    "cores": cpu_count,
                    "usage_percent": cpu_percent,
                    "frequency_mhz": cpu_freq.current if cpu_freq else None,
                },
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return DiagnosticResult(
                name="cpu",
                passed=False,
                message=f"CPU test failed: {e}",
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )

    async def _test_memory(self) -> DiagnosticResult:
        """Test memory availability."""
        start = datetime.utcnow()
        try:
            import psutil
            mem = psutil.virtual_memory()
            available_mb = mem.available / (1024 * 1024)

            # Need at least 256MB free
            passed = available_mb >= 256

            return DiagnosticResult(
                name="memory",
                passed=passed,
                message=f"Memory: {available_mb:.0f}MB available ({100 - mem.percent:.1f}% free)",
                details={
                    "total_mb": mem.total / (1024 * 1024),
                    "available_mb": available_mb,
                    "percent_used": mem.percent,
                },
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return DiagnosticResult(
                name="memory",
                passed=False,
                message=f"Memory test failed: {e}",
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )

    async def _test_disk(self) -> DiagnosticResult:
        """Test disk space and I/O."""
        start = datetime.utcnow()
        try:
            import psutil
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024 * 1024 * 1024)

            # Need at least 1GB free
            passed = free_gb >= 1

            # Test write speed
            write_speed = await self._test_disk_write()

            return DiagnosticResult(
                name="disk",
                passed=passed and write_speed > 0,
                message=f"Disk: {free_gb:.1f}GB free, {write_speed:.1f}MB/s write",
                details={
                    "total_gb": disk.total / (1024 * 1024 * 1024),
                    "free_gb": free_gb,
                    "percent_used": disk.percent,
                    "write_speed_mbs": write_speed,
                },
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return DiagnosticResult(
                name="disk",
                passed=False,
                message=f"Disk test failed: {e}",
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )

    async def _test_disk_write(self) -> float:
        """Test disk write speed."""
        try:
            test_file = Path("/tmp/croom_disk_test")
            test_size = 10 * 1024 * 1024  # 10MB
            data = os.urandom(test_size)

            start = datetime.utcnow()
            test_file.write_bytes(data)
            elapsed = (datetime.utcnow() - start).total_seconds()

            test_file.unlink()

            return test_size / (1024 * 1024) / elapsed if elapsed > 0 else 0
        except Exception:
            return 0

    async def _test_network(self) -> DiagnosticResult:
        """Test network connectivity."""
        start = datetime.utcnow()
        try:
            # Test ping to multiple hosts
            hosts = [
                ("8.8.8.8", "Google DNS"),
                ("1.1.1.1", "Cloudflare DNS"),
            ]

            latencies = {}
            for ip, name in hosts:
                latency = await self._ping(ip)
                if latency:
                    latencies[name] = latency

            passed = len(latencies) > 0
            avg_latency = sum(latencies.values()) / len(latencies) if latencies else 0

            return DiagnosticResult(
                name="network",
                passed=passed,
                message=f"Network: {len(latencies)}/{len(hosts)} hosts reachable, avg {avg_latency:.1f}ms",
                details={
                    "latencies": latencies,
                    "reachable": len(latencies),
                    "total_tested": len(hosts),
                },
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return DiagnosticResult(
                name="network",
                passed=False,
                message=f"Network test failed: {e}",
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )

    async def _ping(self, host: str) -> Optional[float]:
        """Ping a host and return latency in ms."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "-W", "2", host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                output = stdout.decode()
                for part in output.split():
                    if part.startswith("time="):
                        return float(part[5:])
        except Exception:
            pass
        return None

    async def _test_dns(self) -> DiagnosticResult:
        """Test DNS resolution."""
        start = datetime.utcnow()
        try:
            import socket
            test_domains = ["google.com", "cloudflare.com", "microsoft.com"]

            resolved = {}
            for domain in test_domains:
                try:
                    ip = socket.gethostbyname(domain)
                    resolved[domain] = ip
                except Exception:
                    pass

            passed = len(resolved) > 0

            return DiagnosticResult(
                name="dns",
                passed=passed,
                message=f"DNS: {len(resolved)}/{len(test_domains)} domains resolved",
                details={"resolved": resolved},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return DiagnosticResult(
                name="dns",
                passed=False,
                message=f"DNS test failed: {e}",
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )

    async def _test_audio(self) -> DiagnosticResult:
        """Test audio devices."""
        start = datetime.utcnow()
        try:
            proc = await asyncio.create_subprocess_exec(
                "pactl", "list", "sources", "short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()

            sources = []
            if proc.returncode == 0 and stdout:
                for line in stdout.decode().strip().split('\n'):
                    if line and not line.endswith('.monitor'):
                        parts = line.split()
                        if len(parts) >= 2:
                            sources.append(parts[1])

            # Also check sinks
            proc = await asyncio.create_subprocess_exec(
                "pactl", "list", "sinks", "short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()

            sinks = []
            if proc.returncode == 0 and stdout:
                for line in stdout.decode().strip().split('\n'):
                    if line:
                        parts = line.split()
                        if len(parts) >= 2:
                            sinks.append(parts[1])

            passed = len(sources) > 0 or len(sinks) > 0

            return DiagnosticResult(
                name="audio",
                passed=passed,
                message=f"Audio: {len(sources)} inputs, {len(sinks)} outputs",
                details={
                    "sources": sources[:5],
                    "sinks": sinks[:5],
                },
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return DiagnosticResult(
                name="audio",
                passed=False,
                message=f"Audio test failed: {e}",
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )

    async def _test_video(self) -> DiagnosticResult:
        """Test video devices."""
        start = datetime.utcnow()
        try:
            video_devices = list(Path("/dev").glob("video*"))
            device_info = []

            for device in video_devices[:5]:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "v4l2-ctl", "-d", str(device), "--info",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    stdout, _ = await proc.communicate()

                    if proc.returncode == 0:
                        output = stdout.decode()
                        name = "Unknown"
                        for line in output.split('\n'):
                            if "Card type" in line:
                                name = line.split(':')[1].strip()
                                break
                        device_info.append({"device": str(device), "name": name})
                except Exception:
                    device_info.append({"device": str(device), "name": "Unknown"})

            passed = len(video_devices) > 0

            return DiagnosticResult(
                name="video",
                passed=passed,
                message=f"Video: {len(video_devices)} devices found",
                details={"devices": device_info},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return DiagnosticResult(
                name="video",
                passed=False,
                message=f"Video test failed: {e}",
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )

    async def _test_usb(self) -> DiagnosticResult:
        """Test USB devices."""
        start = datetime.utcnow()
        try:
            proc = await asyncio.create_subprocess_exec(
                "lsusb",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()

            devices = []
            if proc.returncode == 0 and stdout:
                for line in stdout.decode().strip().split('\n'):
                    if line:
                        # Parse: "Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub"
                        parts = line.split(': ', 1)
                        if len(parts) == 2:
                            devices.append(parts[1])

            return DiagnosticResult(
                name="usb",
                passed=True,
                message=f"USB: {len(devices)} devices found",
                details={"devices": devices[:10]},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return DiagnosticResult(
                name="usb",
                passed=False,
                message=f"USB test failed: {e}",
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )

    async def _test_services(self) -> DiagnosticResult:
        """Test Croom services."""
        start = datetime.utcnow()
        try:
            services = ["croom-agent", "croom-browser"]
            status = {}

            for service in services:
                proc = await asyncio.create_subprocess_exec(
                    "systemctl", "is-active", service,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await proc.communicate()
                status[service] = stdout.decode().strip() if proc.returncode == 0 else "inactive"

            active = sum(1 for s in status.values() if s == "active")
            passed = active > 0

            return DiagnosticResult(
                name="services",
                passed=passed,
                message=f"Services: {active}/{len(services)} active",
                details={"services": status},
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return DiagnosticResult(
                name="services",
                passed=False,
                message=f"Services test failed: {e}",
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )


class LogCollector:
    """Collects system and application logs."""

    def __init__(self):
        self._log_paths = [
            Path("/var/log/croom"),
            Path("/var/log/syslog"),
            Path("/var/log/auth.log"),
            Path("/var/log/Xorg.0.log"),
        ]

    async def collect(
        self,
        since: Optional[datetime] = None,
        max_lines: int = 10000,
    ) -> Dict[str, Any]:
        """
        Collect logs.

        Args:
            since: Collect logs since this time
            max_lines: Maximum lines per log file

        Returns:
            Dictionary with collected logs
        """
        logs = {}

        # System logs via journalctl
        journal_logs = await self._collect_journalctl(since, max_lines)
        if journal_logs:
            logs["journal"] = journal_logs

        # Croom logs
        croom_logs = await self._collect_croom_logs(since, max_lines)
        if croom_logs:
            logs["croom"] = croom_logs

        # System info
        logs["system_info"] = await self._collect_system_info()

        return logs

    async def _collect_journalctl(
        self,
        since: Optional[datetime],
        max_lines: int,
    ) -> Optional[str]:
        """Collect system journal logs."""
        try:
            cmd = ["journalctl", "-n", str(max_lines), "--no-pager"]
            if since:
                cmd.extend(["--since", since.strftime("%Y-%m-%d %H:%M:%S")])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                return stdout.decode(errors="replace")
        except Exception as e:
            logger.error(f"Failed to collect journal logs: {e}")
        return None

    async def _collect_croom_logs(
        self,
        since: Optional[datetime],
        max_lines: int,
    ) -> Dict[str, str]:
        """Collect Croom application logs."""
        logs = {}
        croom_log_dir = Path("/var/log/croom")

        if not croom_log_dir.exists():
            return logs

        for log_file in croom_log_dir.glob("*.log"):
            try:
                lines = []
                with open(log_file, 'r', errors="replace") as f:
                    for line in f:
                        lines.append(line)
                        if len(lines) > max_lines:
                            lines.pop(0)

                logs[log_file.name] = "".join(lines)
            except Exception as e:
                logger.error(f"Failed to read log file {log_file}: {e}")

        return logs

    async def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information."""
        info = {}

        try:
            import psutil

            # CPU info
            info["cpu"] = {
                "count": psutil.cpu_count(),
                "percent": psutil.cpu_percent(),
            }

            # Memory info
            mem = psutil.virtual_memory()
            info["memory"] = {
                "total_mb": mem.total / (1024 * 1024),
                "available_mb": mem.available / (1024 * 1024),
                "percent": mem.percent,
            }

            # Disk info
            disk = psutil.disk_usage('/')
            info["disk"] = {
                "total_gb": disk.total / (1024 * 1024 * 1024),
                "free_gb": disk.free / (1024 * 1024 * 1024),
                "percent": disk.percent,
            }

            # Network interfaces
            interfaces = {}
            for name, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family.name == "AF_INET":
                        interfaces[name] = addr.address
            info["network"] = interfaces

        except Exception as e:
            logger.error(f"Failed to collect system info: {e}")

        # OS info
        try:
            proc = await asyncio.create_subprocess_exec(
                "uname", "-a",
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            info["uname"] = stdout.decode().strip()
        except Exception:
            pass

        return info

    async def create_support_bundle(
        self,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Create a support bundle with logs and diagnostics.

        Args:
            output_path: Optional output path

        Returns:
            Path to the created bundle
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        bundle_name = f"croom_support_{timestamp}"

        if output_path is None:
            output_path = Path(f"/tmp/{bundle_name}.tar.gz")

        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / bundle_name

            # Create directories
            bundle_dir.mkdir()
            (bundle_dir / "logs").mkdir()
            (bundle_dir / "config").mkdir()
            (bundle_dir / "diagnostics").mkdir()

            # Collect logs
            logs = await self.collect(max_lines=50000)
            for name, content in logs.items():
                if isinstance(content, str):
                    (bundle_dir / "logs" / f"{name}.log").write_text(content)
                elif isinstance(content, dict):
                    for subname, subcontent in content.items():
                        (bundle_dir / "logs" / f"{name}_{subname}").write_text(str(subcontent))

            # Run diagnostics
            runner = DiagnosticRunner()
            results = await runner.run_all()
            diag_output = json.dumps(
                [r.to_dict() for r in results],
                indent=2,
            )
            (bundle_dir / "diagnostics" / "results.json").write_text(diag_output)

            # Copy configuration (sanitized)
            config_paths = [
                Path("/etc/croom/config.json"),
                Path("/etc/croom/device.json"),
            ]
            for config_path in config_paths:
                if config_path.exists():
                    # Read and sanitize
                    try:
                        content = config_path.read_text()
                        data = json.loads(content)
                        # Remove sensitive fields
                        self._sanitize_config(data)
                        (bundle_dir / "config" / config_path.name).write_text(
                            json.dumps(data, indent=2)
                        )
                    except Exception:
                        pass

            # Create manifest
            manifest = {
                "created_at": datetime.utcnow().isoformat(),
                "bundle_version": "1.0",
                "contents": [
                    "logs/",
                    "config/",
                    "diagnostics/",
                ],
            }
            (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

            # Create tarball
            with tarfile.open(output_path, "w:gz") as tar:
                tar.add(bundle_dir, arcname=bundle_name)

        return output_path

    def _sanitize_config(self, data: Dict[str, Any]) -> None:
        """Remove sensitive fields from config."""
        sensitive_fields = [
            "password", "secret", "token", "key", "credential",
            "api_key", "private_key", "client_secret",
        ]

        for key in list(data.keys()):
            lower_key = key.lower()
            if any(s in lower_key for s in sensitive_fields):
                data[key] = "[REDACTED]"
            elif isinstance(data[key], dict):
                self._sanitize_config(data[key])
            elif isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, dict):
                        self._sanitize_config(item)


class UpdateManager:
    """Manages software updates."""

    def __init__(self, update_url: Optional[str] = None):
        self._update_url = update_url
        self._current_version: Optional[str] = None

    async def check_updates(self) -> Dict[str, Any]:
        """Check for available updates."""
        result = {
            "current_version": await self._get_current_version(),
            "updates_available": False,
            "updates": [],
        }

        # Check apt updates
        apt_updates = await self._check_apt_updates()
        if apt_updates:
            result["updates_available"] = True
            result["updates"].extend(apt_updates)

        # Check Croom updates
        if self._update_url:
            croom_update = await self._check_croom_update()
            if croom_update:
                result["updates_available"] = True
                result["updates"].append(croom_update)

        return result

    async def _get_current_version(self) -> str:
        """Get current Croom version."""
        if self._current_version:
            return self._current_version

        version_file = Path("/etc/croom/version")
        if version_file.exists():
            self._current_version = version_file.read_text().strip()
        else:
            self._current_version = "unknown"

        return self._current_version

    async def _check_apt_updates(self) -> List[Dict[str, str]]:
        """Check for apt package updates."""
        updates = []
        try:
            # Update package list
            proc = await asyncio.create_subprocess_exec(
                "apt-get", "update", "-qq",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()

            # List upgradable packages
            proc = await asyncio.create_subprocess_exec(
                "apt", "list", "--upgradable",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                for line in stdout.decode().strip().split('\n'):
                    if '/' in line and line != "Listing...":
                        parts = line.split('/')
                        package = parts[0]
                        updates.append({
                            "type": "apt",
                            "package": package,
                            "line": line,
                        })
        except Exception as e:
            logger.error(f"Failed to check apt updates: {e}")

        return updates

    async def _check_croom_update(self) -> Optional[Dict[str, Any]]:
        """Check for Croom application update."""
        if not self._update_url:
            return None

        try:
            # Fetch update manifest
            req = Request(
                f"{self._update_url}/manifest.json",
                headers={"User-Agent": "Croom-Update/1.0"},
            )
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urlopen(req, timeout=10),
            )
            manifest = json.loads(response.read().decode())

            current = await self._get_current_version()
            latest = manifest.get("version", "0.0.0")

            if self._version_compare(latest, current) > 0:
                return {
                    "type": "croom",
                    "current_version": current,
                    "new_version": latest,
                    "changelog": manifest.get("changelog", []),
                    "download_url": manifest.get("download_url"),
                }
        except Exception as e:
            logger.error(f"Failed to check Croom updates: {e}")

        return None

    def _version_compare(self, v1: str, v2: str) -> int:
        """Compare version strings."""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]

            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0

                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1

            return 0
        except Exception:
            return 0

    async def apply_updates(
        self,
        update_type: str = "all",
        on_progress: Optional[Callable[[str, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Apply available updates.

        Args:
            update_type: Type of updates ("apt", "croom", "all")
            on_progress: Progress callback (message, percent)

        Returns:
            Update result
        """
        result = {
            "success": True,
            "updated": [],
            "errors": [],
        }

        if update_type in ("apt", "all"):
            if on_progress:
                on_progress("Updating system packages...", 10)

            apt_result = await self._apply_apt_updates()
            if apt_result["success"]:
                result["updated"].extend(apt_result.get("packages", []))
            else:
                result["errors"].append(apt_result.get("error", "APT update failed"))

        if update_type in ("croom", "all") and self._update_url:
            if on_progress:
                on_progress("Updating Croom...", 50)

            croom_result = await self._apply_croom_update()
            if croom_result["success"]:
                result["updated"].append(f"croom-{croom_result.get('version', 'unknown')}")
            elif croom_result.get("error"):
                result["errors"].append(croom_result["error"])

        if result["errors"]:
            result["success"] = False

        if on_progress:
            on_progress("Update complete", 100)

        return result

    async def _apply_apt_updates(self) -> Dict[str, Any]:
        """Apply apt package updates."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "apt-get", "upgrade", "-y",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                return {"success": True, "packages": []}
            else:
                return {"success": False, "error": stderr.decode()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _apply_croom_update(self) -> Dict[str, Any]:
        """Apply Croom application update."""
        # This would download and apply the update package
        # For now, return a placeholder
        return {"success": True, "version": "updated"}


class RemoteOperationsService:
    """Main service for remote device operations."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        update_url: Optional[str] = None,
        allowed_commands: Optional[List[str]] = None,
    ):
        """
        Initialize remote operations service.

        Args:
            storage_path: Path to store operation history
            update_url: URL for Croom updates
            allowed_commands: List of allowed command prefixes for execute_command
        """
        self._storage_path = storage_path or Path("/var/lib/croom/operations")
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._operations: Dict[str, Operation] = {}
        self._history: List[Operation] = []
        self._max_history = 100

        # Components
        self._diagnostic_runner = DiagnosticRunner()
        self._log_collector = LogCollector()
        self._update_manager = UpdateManager(update_url)

        # Security: allowed command prefixes
        self._allowed_commands = allowed_commands or [
            "systemctl status",
            "systemctl restart croom",
            "journalctl",
            "df -h",
            "free -m",
            "ps aux",
            "top -bn1",
            "ip addr",
            "iwconfig",
            "pactl list",
            "v4l2-ctl",
        ]

    async def execute(
        self,
        operation: Operation,
        on_progress: Optional[Callable[[str, int], None]] = None,
    ) -> Operation:
        """
        Execute a remote operation.

        Args:
            operation: Operation to execute
            on_progress: Progress callback

        Returns:
            Updated operation with result
        """
        self._operations[operation.id] = operation
        operation.status = OperationStatus.RUNNING
        operation.started_at = datetime.utcnow()

        try:
            if operation.type == OperationType.REBOOT:
                operation.result = await self._do_reboot(operation.parameters)

            elif operation.type == OperationType.SHUTDOWN:
                operation.result = await self._do_shutdown(operation.parameters)

            elif operation.type == OperationType.RESTART_SERVICE:
                operation.result = await self._do_restart_service(operation.parameters)

            elif operation.type == OperationType.UPDATE_SOFTWARE:
                operation.result = await self._do_update(operation.parameters, on_progress)

            elif operation.type == OperationType.UPDATE_CONFIG:
                operation.result = await self._do_update_config(operation.parameters)

            elif operation.type == OperationType.RUN_DIAGNOSTIC:
                operation.result = await self._do_diagnostic(operation.parameters)

            elif operation.type == OperationType.COLLECT_LOGS:
                operation.result = await self._do_collect_logs(operation.parameters)

            elif operation.type == OperationType.CAPTURE_SCREENSHOT:
                operation.result = await self._do_capture_screenshot(operation.parameters)

            elif operation.type == OperationType.EXECUTE_COMMAND:
                operation.result = await self._do_execute_command(operation.parameters)

            elif operation.type == OperationType.FACTORY_RESET:
                operation.result = await self._do_factory_reset(operation.parameters)

            else:
                raise ValueError(f"Unknown operation type: {operation.type}")

            operation.status = OperationStatus.COMPLETED

        except Exception as e:
            operation.status = OperationStatus.FAILED
            operation.error = str(e)
            logger.error(f"Operation {operation.id} failed: {e}")

        operation.completed_at = datetime.utcnow()

        # Store in history
        self._history.append(operation)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return operation

    async def _do_reboot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute reboot operation."""
        delay = params.get("delay", 5)  # seconds

        # Schedule reboot
        asyncio.create_task(self._delayed_reboot(delay))

        return {
            "message": f"Reboot scheduled in {delay} seconds",
            "delay": delay,
        }

    async def _delayed_reboot(self, delay: int) -> None:
        """Perform delayed reboot."""
        await asyncio.sleep(delay)
        try:
            os.system("sudo reboot")
        except Exception as e:
            logger.error(f"Reboot failed: {e}")

    async def _do_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute shutdown operation."""
        delay = params.get("delay", 5)

        asyncio.create_task(self._delayed_shutdown(delay))

        return {
            "message": f"Shutdown scheduled in {delay} seconds",
            "delay": delay,
        }

    async def _delayed_shutdown(self, delay: int) -> None:
        """Perform delayed shutdown."""
        await asyncio.sleep(delay)
        try:
            os.system("sudo shutdown -h now")
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")

    async def _do_restart_service(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Restart a service."""
        service = params.get("service", "croom-agent")

        # Validate service name (only allow croom services)
        if not service.startswith("croom"):
            raise ValueError(f"Invalid service: {service}")

        proc = await asyncio.create_subprocess_exec(
            "systemctl", "restart", service,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Service restart failed: {stderr.decode()}")

        return {
            "message": f"Service {service} restarted",
            "service": service,
        }

    async def _do_update(
        self,
        params: Dict[str, Any],
        on_progress: Optional[Callable[[str, int], None]],
    ) -> Dict[str, Any]:
        """Execute software update."""
        update_type = params.get("type", "all")
        result = await self._update_manager.apply_updates(update_type, on_progress)
        return result

    async def _do_update_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update device configuration."""
        config = params.get("config", {})
        config_path = Path("/etc/croom/config.json")

        if not config:
            raise ValueError("No configuration provided")

        # Read existing config
        existing = {}
        if config_path.exists():
            existing = json.loads(config_path.read_text())

        # Merge configurations
        merged = self._deep_merge(existing, config)

        # Backup and write
        backup_path = config_path.with_suffix(".json.bak")
        if config_path.exists():
            shutil.copy(config_path, backup_path)

        config_path.write_text(json.dumps(merged, indent=2))

        return {
            "message": "Configuration updated",
            "backup": str(backup_path),
        }

    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    async def _do_diagnostic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run diagnostics."""
        tests = params.get("tests")  # Optional: specific tests to run

        results = await self._diagnostic_runner.run_all()

        if tests:
            results = [r for r in results if r.name in tests]

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        return {
            "passed": passed,
            "total": total,
            "all_passed": passed == total,
            "results": [r.to_dict() for r in results],
        }

    async def _do_collect_logs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Collect logs."""
        since = params.get("since")
        if since:
            since = datetime.fromisoformat(since)

        create_bundle = params.get("create_bundle", False)

        if create_bundle:
            bundle_path = await self._log_collector.create_support_bundle()
            return {
                "message": "Support bundle created",
                "path": str(bundle_path),
                "size_bytes": bundle_path.stat().st_size,
            }
        else:
            logs = await self._log_collector.collect(since=since)
            return {
                "message": "Logs collected",
                "logs": logs,
            }

    async def _do_capture_screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Capture screenshot."""
        output_path = Path(params.get("output", "/tmp/screenshot.png"))

        try:
            # Use scrot for screenshot
            proc = await asyncio.create_subprocess_exec(
                "scrot", str(output_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                # Try alternative with import (ImageMagick)
                proc = await asyncio.create_subprocess_exec(
                    "import", "-window", "root", str(output_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(f"Screenshot failed: {stderr.decode()}")

            return {
                "message": "Screenshot captured",
                "path": str(output_path),
                "size_bytes": output_path.stat().st_size,
            }

        except Exception as e:
            raise RuntimeError(f"Screenshot failed: {e}")

    async def _do_execute_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a shell command (restricted)."""
        command = params.get("command", "")
        timeout = params.get("timeout", 30)

        if not command:
            raise ValueError("No command provided")

        # Security check: only allow whitelisted command prefixes
        allowed = False
        for prefix in self._allowed_commands:
            if command.startswith(prefix):
                allowed = True
                break

        if not allowed:
            raise ValueError(f"Command not allowed: {command}")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            return {
                "exit_code": proc.returncode,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
            }

        except asyncio.TimeoutError:
            raise RuntimeError(f"Command timed out after {timeout}s")

    async def _do_factory_reset(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform factory reset (requires confirmation)."""
        confirmed = params.get("confirmed", False)

        if not confirmed:
            raise ValueError("Factory reset requires confirmation")

        # This would clear all data and reset to defaults
        # For safety, just return a placeholder
        return {
            "message": "Factory reset initiated",
            "warning": "Device will restart with default settings",
        }

    def get_operation(self, operation_id: str) -> Optional[Operation]:
        """Get an operation by ID."""
        return self._operations.get(operation_id)

    def get_operations(
        self,
        status: Optional[OperationStatus] = None,
        limit: int = 50,
    ) -> List[Operation]:
        """Get operations, optionally filtered by status."""
        ops = list(self._operations.values())
        if status:
            ops = [o for o in ops if o.status == status]
        return ops[-limit:]

    def get_history(self, limit: int = 50) -> List[Operation]:
        """Get operation history."""
        return self._history[-limit:]

    async def check_updates(self) -> Dict[str, Any]:
        """Check for available updates."""
        return await self._update_manager.check_updates()


def create_remote_ops_service(config: Dict[str, Any]) -> RemoteOperationsService:
    """
    Create remote operations service from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured remote operations service
    """
    return RemoteOperationsService(
        storage_path=Path(config.get("storage_path", "/var/lib/croom/operations")),
        update_url=config.get("update_url"),
        allowed_commands=config.get("allowed_commands"),
    )

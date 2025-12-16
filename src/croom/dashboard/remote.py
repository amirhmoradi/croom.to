"""
Remote operations for Croom dashboard.

Provides remote device management capabilities including screenshots,
shell access, diagnostics, and device control.
"""

import asyncio
import base64
import io
import logging
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Remote operation types."""
    SCREENSHOT = "screenshot"
    SHELL = "shell"
    RESTART_DEVICE = "restart_device"
    RESTART_SERVICE = "restart_service"
    UPDATE_SOFTWARE = "update_software"
    CLEAR_CACHE = "clear_cache"
    FACTORY_RESET = "factory_reset"
    NETWORK_DIAGNOSTICS = "network_diagnostics"
    AUDIO_TEST = "audio_test"
    VIDEO_TEST = "video_test"
    SYSTEM_INFO = "system_info"
    LOG_COLLECTION = "log_collection"


class OperationState(Enum):
    """Operation execution state."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RemoteOperation:
    """Remote operation record."""
    id: str
    operation_type: OperationType
    device_id: str
    params: Dict[str, Any] = field(default_factory=dict)
    state: OperationState = OperationState.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    requested_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "operation_type": self.operation_type.value,
            "device_id": self.device_id,
            "params": self.params,
            "state": self.state.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "requested_by": self.requested_by,
        }


class ScreenshotService:
    """Service for capturing device screenshots."""

    async def capture(self, display: int = 0) -> Optional[bytes]:
        """
        Capture a screenshot of the display.

        Args:
            display: Display number to capture

        Returns:
            PNG image bytes or None on failure
        """
        # Try different methods
        methods = [
            self._capture_scrot,
            self._capture_import,
            self._capture_gnome,
            self._capture_x11,
        ]

        for method in methods:
            try:
                result = await method(display)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"Screenshot method failed: {e}")
                continue

        logger.error("All screenshot methods failed")
        return None

    async def _capture_scrot(self, display: int) -> Optional[bytes]:
        """Capture using scrot."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            temp_path = f.name

        try:
            env = os.environ.copy()
            env['DISPLAY'] = f':{display}'

            proc = await asyncio.create_subprocess_exec(
                'scrot', '-o', temp_path,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.wait(), timeout=10)

            if proc.returncode == 0 and Path(temp_path).exists():
                return Path(temp_path).read_bytes()

        finally:
            Path(temp_path).unlink(missing_ok=True)

        return None

    async def _capture_import(self, display: int) -> Optional[bytes]:
        """Capture using ImageMagick import."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            temp_path = f.name

        try:
            env = os.environ.copy()
            env['DISPLAY'] = f':{display}'

            proc = await asyncio.create_subprocess_exec(
                'import', '-window', 'root', temp_path,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.wait(), timeout=10)

            if proc.returncode == 0 and Path(temp_path).exists():
                return Path(temp_path).read_bytes()

        finally:
            Path(temp_path).unlink(missing_ok=True)

        return None

    async def _capture_gnome(self, display: int) -> Optional[bytes]:
        """Capture using gnome-screenshot."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            temp_path = f.name

        try:
            env = os.environ.copy()
            env['DISPLAY'] = f':{display}'

            proc = await asyncio.create_subprocess_exec(
                'gnome-screenshot', '-f', temp_path,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.wait(), timeout=10)

            if proc.returncode == 0 and Path(temp_path).exists():
                return Path(temp_path).read_bytes()

        finally:
            Path(temp_path).unlink(missing_ok=True)

        return None

    async def _capture_x11(self, display: int) -> Optional[bytes]:
        """Capture using python-xlib."""
        try:
            from Xlib import X, display as xdisplay
            from PIL import Image

            d = xdisplay.Display(f':{display}')
            screen = d.screen()
            root = screen.root

            geometry = root.get_geometry()
            raw = root.get_image(
                0, 0,
                geometry.width, geometry.height,
                X.ZPixmap, 0xffffffff
            )

            image = Image.frombytes(
                'RGB',
                (geometry.width, geometry.height),
                raw.data,
                'raw',
                'BGRX',
            )

            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            return buffer.getvalue()

        except ImportError:
            return None


class ShellService:
    """Service for executing shell commands."""

    def __init__(self, allowed_commands: Optional[List[str]] = None):
        """
        Initialize shell service.

        Args:
            allowed_commands: List of allowed command prefixes for security
        """
        self._allowed_commands = allowed_commands or [
            'ls', 'cat', 'head', 'tail', 'grep', 'df', 'free', 'uptime',
            'ps', 'top', 'htop', 'netstat', 'ss', 'ip', 'ping', 'traceroute',
            'dig', 'nslookup', 'systemctl status', 'journalctl', 'dmesg',
            'vcgencmd', 'raspi-config', 'apt', 'pip',
        ]
        self._command_history: List[Dict[str, Any]] = []

    async def execute(
        self,
        command: str,
        timeout: int = 30,
        cwd: Optional[str] = None,
    ) -> Tuple[int, str, str]:
        """
        Execute a shell command.

        Args:
            command: Command to execute
            timeout: Execution timeout in seconds
            cwd: Working directory

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        # Security check
        if not self._is_allowed(command):
            return (-1, "", f"Command not allowed: {command.split()[0]}")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            result = (
                proc.returncode,
                stdout.decode('utf-8', errors='replace'),
                stderr.decode('utf-8', errors='replace'),
            )

            # Log command
            self._command_history.append({
                'command': command,
                'return_code': result[0],
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })

            return result

        except asyncio.TimeoutError:
            return (-1, "", f"Command timed out after {timeout}s")
        except Exception as e:
            return (-1, "", str(e))

    def _is_allowed(self, command: str) -> bool:
        """Check if command is in the allowed list."""
        if not self._allowed_commands:
            return True

        cmd_start = command.strip().split()[0] if command.strip() else ""

        for allowed in self._allowed_commands:
            if command.strip().startswith(allowed):
                return True
            if cmd_start == allowed.split()[0]:
                return True

        return False

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get command history."""
        return self._command_history[-limit:]


class DiagnosticsService:
    """Service for running device diagnostics."""

    async def run_network_diagnostics(
        self,
        targets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run network diagnostics.

        Args:
            targets: List of hosts to test

        Returns:
            Diagnostic results
        """
        targets = targets or ['8.8.8.8', '1.1.1.1', 'google.com']
        results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'connectivity': {},
            'dns': {},
            'interfaces': {},
        }

        # Ping tests
        for target in targets:
            results['connectivity'][target] = await self._ping(target)

        # DNS resolution
        for host in ['google.com', 'cloudflare.com']:
            results['dns'][host] = await self._resolve_dns(host)

        # Network interfaces
        results['interfaces'] = await self._get_interfaces()

        return results

    async def _ping(self, host: str, count: int = 3) -> Dict[str, Any]:
        """Ping a host."""
        try:
            proc = await asyncio.create_subprocess_exec(
                'ping', '-c', str(count), '-W', '2', host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            output = stdout.decode('utf-8')

            # Parse results
            import re
            match = re.search(r'(\d+) packets transmitted, (\d+) received', output)
            if match:
                transmitted = int(match.group(1))
                received = int(match.group(2))
                loss = ((transmitted - received) / transmitted) * 100

                # Parse RTT
                rtt_match = re.search(r'rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)', output)
                rtt = None
                if rtt_match:
                    rtt = {
                        'min': float(rtt_match.group(1)),
                        'avg': float(rtt_match.group(2)),
                        'max': float(rtt_match.group(3)),
                    }

                return {
                    'success': received > 0,
                    'transmitted': transmitted,
                    'received': received,
                    'packet_loss': loss,
                    'rtt': rtt,
                }

        except Exception as e:
            logger.error(f"Ping error: {e}")

        return {'success': False, 'error': 'Ping failed'}

    async def _resolve_dns(self, hostname: str) -> Dict[str, Any]:
        """Resolve DNS for a hostname."""
        try:
            import socket
            loop = asyncio.get_event_loop()

            start = asyncio.get_event_loop().time()
            addrs = await loop.run_in_executor(
                None,
                lambda: socket.getaddrinfo(hostname, None, socket.AF_INET)
            )
            duration = (asyncio.get_event_loop().time() - start) * 1000

            ips = list(set(addr[4][0] for addr in addrs))

            return {
                'success': True,
                'addresses': ips,
                'resolution_time_ms': round(duration, 2),
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _get_interfaces(self) -> Dict[str, Any]:
        """Get network interface information."""
        interfaces = {}

        try:
            import socket
            import fcntl
            import struct

            # Get interface list
            proc = await asyncio.create_subprocess_exec(
                'ip', '-j', 'addr',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            import json
            data = json.loads(stdout.decode('utf-8'))

            for iface in data:
                name = iface.get('ifname', '')
                if name == 'lo':
                    continue

                info = {
                    'operstate': iface.get('operstate', 'unknown'),
                    'mac': iface.get('address', ''),
                    'addresses': [],
                }

                for addr_info in iface.get('addr_info', []):
                    info['addresses'].append({
                        'address': addr_info.get('local', ''),
                        'prefix': addr_info.get('prefixlen', 0),
                        'family': addr_info.get('family', ''),
                    })

                interfaces[name] = info

        except Exception as e:
            logger.error(f"Interface error: {e}")

        return interfaces

    async def run_audio_test(self) -> Dict[str, Any]:
        """Run audio device test."""
        results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'input_devices': [],
            'output_devices': [],
            'test_results': {},
        }

        try:
            # List audio devices using arecord/aplay
            proc = await asyncio.create_subprocess_exec(
                'arecord', '-l',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            results['input_devices'] = self._parse_alsa_devices(stdout.decode('utf-8'))

            proc = await asyncio.create_subprocess_exec(
                'aplay', '-l',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            results['output_devices'] = self._parse_alsa_devices(stdout.decode('utf-8'))

        except Exception as e:
            results['error'] = str(e)

        return results

    def _parse_alsa_devices(self, output: str) -> List[Dict[str, str]]:
        """Parse ALSA device list output."""
        devices = []
        import re

        for line in output.split('\n'):
            match = re.match(r'card (\d+): (\w+) \[([^\]]+)\]', line)
            if match:
                devices.append({
                    'card': match.group(1),
                    'id': match.group(2),
                    'name': match.group(3),
                })

        return devices

    async def run_video_test(self) -> Dict[str, Any]:
        """Run video device test."""
        results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'devices': [],
        }

        try:
            # Find video devices
            for i in range(10):
                device = f'/dev/video{i}'
                if Path(device).exists():
                    info = await self._get_video_device_info(device)
                    if info:
                        results['devices'].append(info)

        except Exception as e:
            results['error'] = str(e)

        return results

    async def _get_video_device_info(self, device: str) -> Optional[Dict[str, Any]]:
        """Get video device information using v4l2."""
        try:
            proc = await asyncio.create_subprocess_exec(
                'v4l2-ctl', '-d', device, '--all',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode('utf-8')

            info = {'device': device}

            # Parse output
            import re
            name_match = re.search(r'Card type\s+:\s+(.+)', output)
            if name_match:
                info['name'] = name_match.group(1).strip()

            driver_match = re.search(r'Driver name\s+:\s+(.+)', output)
            if driver_match:
                info['driver'] = driver_match.group(1).strip()

            return info

        except Exception:
            return None

    async def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        info = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'platform': {},
            'cpu': {},
            'memory': {},
            'disk': {},
            'network': {},
            'software': {},
        }

        # Platform info
        info['platform'] = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'hostname': platform.node(),
        }

        # CPU info
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()

            import re
            model_match = re.search(r'model name\s+:\s+(.+)', cpuinfo)
            if model_match:
                info['cpu']['model'] = model_match.group(1)

            cores = len(re.findall(r'^processor\s+:', cpuinfo, re.MULTILINE))
            info['cpu']['cores'] = cores

        except Exception:
            pass

        # Memory info
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal'):
                        info['memory']['total_kb'] = int(line.split()[1])
                    elif line.startswith('MemAvailable'):
                        info['memory']['available_kb'] = int(line.split()[1])
        except Exception:
            pass

        # Disk info
        try:
            stat = os.statvfs('/')
            info['disk'] = {
                'total_bytes': stat.f_blocks * stat.f_frsize,
                'free_bytes': stat.f_bfree * stat.f_frsize,
                'available_bytes': stat.f_bavail * stat.f_frsize,
            }
        except Exception:
            pass

        # Software versions
        try:
            proc = await asyncio.create_subprocess_exec(
                'python3', '--version',
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            info['software']['python'] = stdout.decode('utf-8').strip()
        except Exception:
            pass

        return info

    async def collect_logs(
        self,
        services: Optional[List[str]] = None,
        lines: int = 100,
    ) -> Dict[str, str]:
        """
        Collect system and service logs.

        Args:
            services: List of systemd services to collect logs for
            lines: Number of log lines to collect per service

        Returns:
            Dictionary of service name to log content
        """
        services = services or ['croom', 'croom-ui']
        logs = {}

        # System journal
        try:
            proc = await asyncio.create_subprocess_exec(
                'journalctl', '-n', str(lines), '--no-pager',
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            logs['system'] = stdout.decode('utf-8', errors='replace')
        except Exception:
            pass

        # Service logs
        for service in services:
            try:
                proc = await asyncio.create_subprocess_exec(
                    'journalctl', '-u', service, '-n', str(lines), '--no-pager',
                    stdout=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                logs[service] = stdout.decode('utf-8', errors='replace')
            except Exception:
                logs[service] = "Failed to collect logs"

        return logs


class DeviceControlService:
    """Service for device control operations."""

    async def restart_device(self, delay: int = 5) -> bool:
        """
        Restart the device.

        Args:
            delay: Delay before restart in seconds

        Returns:
            True if restart initiated
        """
        try:
            # Schedule reboot
            proc = await asyncio.create_subprocess_exec(
                'sudo', 'shutdown', '-r', f'+{delay // 60}',
                f'Scheduled restart in {delay} seconds',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            return proc.returncode == 0

        except Exception as e:
            logger.error(f"Restart failed: {e}")
            return False

    async def restart_service(self, service: str) -> bool:
        """
        Restart a systemd service.

        Args:
            service: Service name

        Returns:
            True if restart successful
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                'sudo', 'systemctl', 'restart', service,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"Service restart failed: {stderr.decode()}")
                return False

            return True

        except Exception as e:
            logger.error(f"Service restart failed: {e}")
            return False

    async def clear_cache(self) -> Dict[str, bool]:
        """
        Clear various caches.

        Returns:
            Dictionary of cache type to success status
        """
        results = {}

        # Browser cache
        cache_paths = [
            Path.home() / '.cache' / 'chromium',
            Path.home() / '.cache' / 'google-chrome',
            Path.home() / '.cache' / 'croom',
            Path('/tmp') / 'croom-cache',
        ]

        for cache_path in cache_paths:
            try:
                if cache_path.exists():
                    shutil.rmtree(cache_path)
                    results[str(cache_path)] = True
                    logger.info(f"Cleared cache: {cache_path}")
            except Exception as e:
                results[str(cache_path)] = False
                logger.error(f"Failed to clear cache {cache_path}: {e}")

        return results

    async def update_software(
        self,
        package: str = "croom",
    ) -> Tuple[bool, str]:
        """
        Update software packages.

        Args:
            package: Package to update

        Returns:
            Tuple of (success, output)
        """
        try:
            # Update package lists
            proc = await asyncio.create_subprocess_exec(
                'sudo', 'apt-get', 'update',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            # Upgrade package
            proc = await asyncio.create_subprocess_exec(
                'sudo', 'apt-get', 'install', '-y', package,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            output = stdout.decode('utf-8') + stderr.decode('utf-8')
            return proc.returncode == 0, output

        except Exception as e:
            return False, str(e)


class RemoteOperationsManager:
    """
    Manager for remote device operations.

    Coordinates operation execution, tracking, and audit logging.
    """

    def __init__(self):
        self._screenshot = ScreenshotService()
        self._shell = ShellService()
        self._diagnostics = DiagnosticsService()
        self._control = DeviceControlService()

        self._operations: Dict[str, RemoteOperation] = {}
        self._callbacks: List[Callable[[RemoteOperation], None]] = []

    async def execute(
        self,
        operation_type: OperationType,
        device_id: str,
        params: Optional[Dict[str, Any]] = None,
        requested_by: str = "",
    ) -> RemoteOperation:
        """
        Execute a remote operation.

        Args:
            operation_type: Type of operation
            device_id: Target device ID
            params: Operation parameters
            requested_by: User who requested the operation

        Returns:
            RemoteOperation with results
        """
        import uuid
        operation_id = str(uuid.uuid4())[:8]

        operation = RemoteOperation(
            id=operation_id,
            operation_type=operation_type,
            device_id=device_id,
            params=params or {},
            requested_by=requested_by,
        )

        self._operations[operation_id] = operation
        operation.state = OperationState.RUNNING
        operation.started_at = datetime.now(timezone.utc)

        try:
            result = await self._execute_operation(operation_type, params or {})
            operation.state = OperationState.COMPLETED
            operation.result = result

        except Exception as e:
            operation.state = OperationState.FAILED
            operation.error = str(e)
            logger.error(f"Operation {operation_id} failed: {e}")

        operation.completed_at = datetime.now(timezone.utc)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(operation)
            except Exception as e:
                logger.error(f"Operation callback error: {e}")

        return operation

    async def _execute_operation(
        self,
        operation_type: OperationType,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute the actual operation."""
        if operation_type == OperationType.SCREENSHOT:
            data = await self._screenshot.capture(params.get('display', 0))
            if data:
                return {
                    'image_base64': base64.b64encode(data).decode('utf-8'),
                    'size_bytes': len(data),
                }
            raise Exception("Screenshot capture failed")

        elif operation_type == OperationType.SHELL:
            returncode, stdout, stderr = await self._shell.execute(
                params.get('command', ''),
                params.get('timeout', 30),
                params.get('cwd'),
            )
            return {
                'returncode': returncode,
                'stdout': stdout,
                'stderr': stderr,
            }

        elif operation_type == OperationType.NETWORK_DIAGNOSTICS:
            return await self._diagnostics.run_network_diagnostics(
                params.get('targets')
            )

        elif operation_type == OperationType.AUDIO_TEST:
            return await self._diagnostics.run_audio_test()

        elif operation_type == OperationType.VIDEO_TEST:
            return await self._diagnostics.run_video_test()

        elif operation_type == OperationType.SYSTEM_INFO:
            return await self._diagnostics.get_system_info()

        elif operation_type == OperationType.LOG_COLLECTION:
            return await self._diagnostics.collect_logs(
                params.get('services'),
                params.get('lines', 100),
            )

        elif operation_type == OperationType.RESTART_DEVICE:
            success = await self._control.restart_device(params.get('delay', 5))
            return {'success': success}

        elif operation_type == OperationType.RESTART_SERVICE:
            success = await self._control.restart_service(params.get('service', 'croom'))
            return {'success': success}

        elif operation_type == OperationType.CLEAR_CACHE:
            return await self._control.clear_cache()

        elif operation_type == OperationType.UPDATE_SOFTWARE:
            success, output = await self._control.update_software(
                params.get('package', 'croom')
            )
            return {'success': success, 'output': output}

        else:
            raise ValueError(f"Unknown operation type: {operation_type}")

    def on_operation_complete(self, callback: Callable[[RemoteOperation], None]) -> None:
        """Register callback for operation completion."""
        self._callbacks.append(callback)

    def get_operation(self, operation_id: str) -> Optional[RemoteOperation]:
        """Get operation by ID."""
        return self._operations.get(operation_id)

    def get_operations(
        self,
        device_id: Optional[str] = None,
        state: Optional[OperationState] = None,
        limit: int = 100,
    ) -> List[RemoteOperation]:
        """Get operations with optional filters."""
        operations = list(self._operations.values())

        if device_id:
            operations = [o for o in operations if o.device_id == device_id]

        if state:
            operations = [o for o in operations if o.state == state]

        # Sort by started_at descending
        operations.sort(key=lambda o: o.started_at or datetime.min, reverse=True)

        return operations[:limit]

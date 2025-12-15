"""
Dashboard enrollment for PiMeet devices.

Handles device registration with the management dashboard.
"""

import asyncio
import logging
import platform
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Check for aiohttp
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


class EnrollmentStatus(Enum):
    """Device enrollment status."""
    NOT_ENROLLED = "not_enrolled"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass
class DeviceIdentity:
    """Device identity information."""
    device_id: str
    mac_address: str
    serial_number: str
    hostname: str
    model: str
    os_version: str


@dataclass
class EnrollmentResult:
    """Result of enrollment attempt."""
    status: EnrollmentStatus
    message: str
    device_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class DashboardEnrollment:
    """
    Handles device enrollment with management dashboard.

    Supports:
    - Automatic registration on first boot
    - Enrollment token validation
    - Pending approval workflow
    - Configuration push after approval
    """

    def __init__(
        self,
        dashboard_url: str,
        enrollment_token: Optional[str] = None
    ):
        """
        Initialize dashboard enrollment.

        Args:
            dashboard_url: Dashboard base URL
            enrollment_token: Pre-shared enrollment token
        """
        self._dashboard_url = dashboard_url.rstrip('/')
        self._enrollment_token = enrollment_token
        self._device_identity: Optional[DeviceIdentity] = None
        self._status = EnrollmentStatus.NOT_ENROLLED

    @property
    def status(self) -> EnrollmentStatus:
        """Current enrollment status."""
        return self._status

    async def get_device_identity(self) -> DeviceIdentity:
        """
        Collect device identity information.

        Returns:
            DeviceIdentity with hardware/software info
        """
        if self._device_identity:
            return self._device_identity

        device_id = await self._get_device_id()
        mac_address = await self._get_mac_address()
        serial_number = await self._get_serial_number()

        self._device_identity = DeviceIdentity(
            device_id=device_id,
            mac_address=mac_address,
            serial_number=serial_number,
            hostname=platform.node(),
            model=await self._get_model(),
            os_version=platform.release(),
        )

        return self._device_identity

    async def _get_device_id(self) -> str:
        """Generate unique device ID."""
        # Try Pi serial first
        serial = await self._get_serial_number()
        if serial and serial != "unknown":
            return f"pimeet-{serial[-8:]}"

        # Fallback to MAC-based ID
        mac = await self._get_mac_address()
        if mac:
            return f"pimeet-{mac.replace(':', '')[-12:]}"

        # Last resort: UUID
        return f"pimeet-{uuid.uuid4().hex[:12]}"

    async def _get_mac_address(self) -> str:
        """Get primary network interface MAC address."""
        try:
            # Try to get wlan0 MAC
            with open('/sys/class/net/wlan0/address', 'r') as f:
                return f.read().strip()
        except Exception:
            pass

        try:
            # Try eth0
            with open('/sys/class/net/eth0/address', 'r') as f:
                return f.read().strip()
        except Exception:
            pass

        return "00:00:00:00:00:00"

    async def _get_serial_number(self) -> str:
        """Get Raspberry Pi serial number."""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        return line.split(':')[1].strip()
        except Exception:
            pass

        return "unknown"

    async def _get_model(self) -> str:
        """Get device model."""
        try:
            with open('/proc/device-tree/model', 'r') as f:
                return f.read().strip().replace('\x00', '')
        except Exception:
            pass

        return platform.machine()

    async def enroll(self) -> EnrollmentResult:
        """
        Attempt to enroll device with dashboard.

        Returns:
            EnrollmentResult with status and configuration
        """
        if not AIOHTTP_AVAILABLE:
            return EnrollmentResult(
                status=EnrollmentStatus.ERROR,
                message="aiohttp not installed"
            )

        identity = await self.get_device_identity()

        try:
            async with aiohttp.ClientSession() as session:
                # Prepare enrollment request
                payload = {
                    "device_id": identity.device_id,
                    "mac_address": identity.mac_address,
                    "serial_number": identity.serial_number,
                    "hostname": identity.hostname,
                    "model": identity.model,
                    "os_version": identity.os_version,
                    "enrollment_token": self._enrollment_token,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                # Send enrollment request
                url = f"{self._dashboard_url}/api/devices/enroll"

                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    data = await response.json()

                    if response.status == 200:
                        # Enrollment successful
                        self._status = EnrollmentStatus.APPROVED
                        return EnrollmentResult(
                            status=EnrollmentStatus.APPROVED,
                            message="Device enrolled successfully",
                            device_id=data.get('device_id'),
                            config=data.get('config'),
                        )

                    elif response.status == 202:
                        # Pending approval
                        self._status = EnrollmentStatus.PENDING
                        return EnrollmentResult(
                            status=EnrollmentStatus.PENDING,
                            message=data.get('message', 'Waiting for admin approval'),
                            device_id=data.get('device_id'),
                        )

                    elif response.status == 401:
                        # Invalid token
                        self._status = EnrollmentStatus.REJECTED
                        return EnrollmentResult(
                            status=EnrollmentStatus.REJECTED,
                            message="Invalid enrollment token",
                        )

                    elif response.status == 403:
                        # Rejected
                        self._status = EnrollmentStatus.REJECTED
                        return EnrollmentResult(
                            status=EnrollmentStatus.REJECTED,
                            message=data.get('message', 'Enrollment rejected'),
                        )

                    else:
                        self._status = EnrollmentStatus.ERROR
                        return EnrollmentResult(
                            status=EnrollmentStatus.ERROR,
                            message=f"Enrollment failed: {response.status}",
                        )

        except aiohttp.ClientError as e:
            logger.error(f"Enrollment request failed: {e}")
            self._status = EnrollmentStatus.ERROR
            return EnrollmentResult(
                status=EnrollmentStatus.ERROR,
                message=f"Connection failed: {e}",
            )

        except Exception as e:
            logger.error(f"Enrollment error: {e}")
            self._status = EnrollmentStatus.ERROR
            return EnrollmentResult(
                status=EnrollmentStatus.ERROR,
                message=str(e),
            )

    async def check_status(self) -> EnrollmentResult:
        """
        Check current enrollment status with dashboard.

        Returns:
            EnrollmentResult with current status
        """
        if not AIOHTTP_AVAILABLE:
            return EnrollmentResult(
                status=EnrollmentStatus.ERROR,
                message="aiohttp not installed"
            )

        identity = await self.get_device_identity()

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self._dashboard_url}/api/devices/{identity.device_id}/status"

                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        status_str = data.get('status', 'pending')
                        status_map = {
                            'approved': EnrollmentStatus.APPROVED,
                            'pending': EnrollmentStatus.PENDING,
                            'rejected': EnrollmentStatus.REJECTED,
                        }
                        self._status = status_map.get(status_str, EnrollmentStatus.PENDING)

                        return EnrollmentResult(
                            status=self._status,
                            message=data.get('message', ''),
                            device_id=identity.device_id,
                            config=data.get('config'),
                        )

                    elif response.status == 404:
                        self._status = EnrollmentStatus.NOT_ENROLLED
                        return EnrollmentResult(
                            status=EnrollmentStatus.NOT_ENROLLED,
                            message="Device not registered",
                        )

                    else:
                        return EnrollmentResult(
                            status=EnrollmentStatus.ERROR,
                            message=f"Status check failed: {response.status}",
                        )

        except Exception as e:
            logger.error(f"Status check error: {e}")
            return EnrollmentResult(
                status=EnrollmentStatus.ERROR,
                message=str(e),
            )

    async def poll_for_approval(
        self,
        interval: int = 30,
        max_attempts: int = 60
    ) -> EnrollmentResult:
        """
        Poll dashboard until device is approved or rejected.

        Args:
            interval: Seconds between checks
            max_attempts: Maximum polling attempts

        Returns:
            Final EnrollmentResult
        """
        for attempt in range(max_attempts):
            result = await self.check_status()

            if result.status == EnrollmentStatus.APPROVED:
                logger.info("Device enrollment approved")
                return result

            elif result.status == EnrollmentStatus.REJECTED:
                logger.warning("Device enrollment rejected")
                return result

            elif result.status == EnrollmentStatus.ERROR:
                logger.error(f"Enrollment check error: {result.message}")
                # Continue trying on errors

            logger.debug(f"Waiting for approval (attempt {attempt + 1}/{max_attempts})")
            await asyncio.sleep(interval)

        return EnrollmentResult(
            status=EnrollmentStatus.PENDING,
            message="Approval timeout",
        )

    async def fetch_configuration(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device configuration from dashboard.

        Returns:
            Configuration dict or None
        """
        if not AIOHTTP_AVAILABLE:
            return None

        identity = await self.get_device_identity()

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self._dashboard_url}/api/devices/{identity.device_id}/config"

                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        return await response.json()

                    logger.error(f"Config fetch failed: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Config fetch error: {e}")
            return None

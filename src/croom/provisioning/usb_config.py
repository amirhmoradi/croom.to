"""
USB configuration reader for Croom provisioning.

Reads device configuration from USB drives on boot.
"""

import asyncio
import logging
import os
import yaml
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from cryptography.fernet import Fernet
import base64
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class DeviceConfig:
    """Parsed device configuration."""
    # Device identity
    name: str = "Conference Room"
    location: str = ""
    timezone: str = "UTC"

    # Network
    wifi_ssid: Optional[str] = None
    wifi_password: Optional[str] = None
    wifi_hidden: bool = False
    wifi_enterprise: bool = False
    wifi_eap_method: Optional[str] = None
    wifi_identity: Optional[str] = None
    use_ethernet: bool = False
    static_ip: Optional[str] = None
    gateway: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)

    # Meeting platform
    platform: str = "google_meet"
    platform_email: Optional[str] = None
    platform_password: Optional[str] = None

    # Dashboard
    dashboard_url: Optional[str] = None
    enrollment_token: Optional[str] = None

    # Calendar
    calendar_provider: Optional[str] = None
    calendar_id: Optional[str] = None


class USBConfigReader:
    """
    Reads configuration from USB drives.

    Supports encrypted credentials via Fernet.
    """

    CONFIG_FILENAMES = [
        "croom-config.yaml",
        "croom-config.yml",
        "croom-config.json",
        "croom.yaml",
        "croom.yml",
        "croom.json",
    ]

    USB_MOUNT_PATHS = [
        "/media",
        "/mnt",
        "/run/media",
    ]

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize USB config reader.

        Args:
            encryption_key: Key for decrypting credentials (optional)
        """
        self._encryption_key = encryption_key
        self._fernet: Optional[Fernet] = None

        if encryption_key:
            # Derive Fernet key from password
            key = hashlib.pbkdf2_hmac(
                'sha256',
                encryption_key.encode(),
                b'croom-usb-config',
                100000
            )
            self._fernet = Fernet(base64.urlsafe_b64encode(key[:32]))

    async def detect_usb_drives(self) -> List[Path]:
        """
        Detect mounted USB drives.

        Returns:
            List of USB mount points
        """
        drives = []

        for base_path in self.USB_MOUNT_PATHS:
            base = Path(base_path)
            if not base.exists():
                continue

            # Check subdirectories (where USB drives are typically mounted)
            for mount in base.iterdir():
                if mount.is_dir() and self._is_usb_mount(mount):
                    drives.append(mount)

        logger.debug(f"Found {len(drives)} USB drives")
        return drives

    def _is_usb_mount(self, path: Path) -> bool:
        """Check if a path is a USB mount point."""
        try:
            # Check /proc/mounts for USB devices
            with open('/proc/mounts', 'r') as f:
                mounts = f.read()

            # Look for this path in mounts
            path_str = str(path)
            for line in mounts.split('\n'):
                if path_str in line:
                    # Check if it's a USB device
                    device = line.split()[0]
                    if '/usb' in device or 'sd' in device:
                        return True

            # Fallback: check if directory has files
            return any(path.iterdir())

        except Exception:
            return path.exists() and any(path.iterdir())

    async def find_config_file(self) -> Optional[Path]:
        """
        Find configuration file on any USB drive.

        Returns:
            Path to config file or None
        """
        drives = await self.detect_usb_drives()

        for drive in drives:
            for filename in self.CONFIG_FILENAMES:
                config_path = drive / filename
                if config_path.exists():
                    logger.info(f"Found config file: {config_path}")
                    return config_path

        logger.debug("No USB config file found")
        return None

    async def read_config(self, config_path: Optional[Path] = None) -> Optional[DeviceConfig]:
        """
        Read and parse configuration file.

        Args:
            config_path: Path to config file (auto-detect if None)

        Returns:
            Parsed DeviceConfig or None
        """
        if config_path is None:
            config_path = await self.find_config_file()

        if config_path is None:
            return None

        try:
            content = config_path.read_text()

            # Parse based on extension
            if config_path.suffix in ('.yaml', '.yml'):
                data = yaml.safe_load(content)
            elif config_path.suffix == '.json':
                data = json.loads(content)
            else:
                # Try YAML first, then JSON
                try:
                    data = yaml.safe_load(content)
                except Exception:
                    data = json.loads(content)

            return self._parse_config(data)

        except Exception as e:
            logger.error(f"Failed to read config file: {e}")
            return None

    def _parse_config(self, data: Dict[str, Any]) -> DeviceConfig:
        """Parse raw config data into DeviceConfig."""
        config = DeviceConfig()

        # Device section
        device = data.get('device', {})
        config.name = device.get('name', config.name)
        config.location = device.get('location', config.location)
        config.timezone = device.get('timezone', config.timezone)

        # Network section
        network = data.get('network', {})

        wifi = network.get('wifi', {})
        if wifi:
            config.wifi_ssid = wifi.get('ssid')
            config.wifi_password = self._decrypt_value(wifi.get('password'))
            config.wifi_hidden = wifi.get('hidden', False)

            # Enterprise WiFi
            if wifi.get('enterprise'):
                config.wifi_enterprise = True
                config.wifi_eap_method = wifi.get('eap_method', 'peap')
                config.wifi_identity = wifi.get('identity')

        config.use_ethernet = network.get('ethernet', False)

        # Static IP
        if 'static' in network:
            static = network['static']
            config.static_ip = static.get('ip')
            config.gateway = static.get('gateway')
            config.dns_servers = static.get('dns', [])

        # Meeting section
        meeting = data.get('meeting', {})
        config.platform = meeting.get('platform', 'google_meet')

        credentials = meeting.get('credentials', {})
        config.platform_email = credentials.get('email')
        config.platform_password = self._decrypt_value(credentials.get('password'))

        # Dashboard section
        dashboard = data.get('dashboard', {})
        config.dashboard_url = dashboard.get('url')
        config.enrollment_token = dashboard.get('enrollment_token')

        # Calendar section
        calendar = data.get('calendar', {})
        config.calendar_provider = calendar.get('provider')
        config.calendar_id = calendar.get('calendar_id')

        return config

    def _decrypt_value(self, value: Optional[str]) -> Optional[str]:
        """Decrypt a value if it's encrypted."""
        if value is None:
            return None

        # Check for encryption prefix
        if value.startswith('encrypted:'):
            if self._fernet is None:
                logger.warning("Encrypted value found but no encryption key provided")
                return None

            try:
                encrypted_data = value[10:]  # Remove 'encrypted:' prefix
                decrypted = self._fernet.decrypt(encrypted_data.encode())
                return decrypted.decode()
            except Exception as e:
                logger.error(f"Failed to decrypt value: {e}")
                return None

        return value

    async def write_error_log(self, config_path: Path, error: str) -> None:
        """
        Write error log to USB drive for troubleshooting.

        Args:
            config_path: Path to config file
            error: Error message
        """
        try:
            error_path = config_path.parent / "croom-error.log"
            with open(error_path, 'a') as f:
                from datetime import datetime
                f.write(f"[{datetime.now().isoformat()}] {error}\n")
            logger.info(f"Error written to {error_path}")
        except Exception as e:
            logger.error(f"Failed to write error log: {e}")

    async def eject_drive(self, config_path: Path) -> bool:
        """
        Safely eject the USB drive.

        Args:
            config_path: Path to a file on the drive

        Returns:
            True if ejected successfully
        """
        try:
            mount_point = config_path.parent

            # Sync filesystem
            process = await asyncio.create_subprocess_exec(
                "sync",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.wait()

            # Unmount
            process = await asyncio.create_subprocess_exec(
                "umount", str(mount_point),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.wait()

            logger.info(f"Ejected USB drive: {mount_point}")
            return process.returncode == 0

        except Exception as e:
            logger.error(f"Failed to eject drive: {e}")
            return False


def create_sample_config() -> str:
    """
    Create a sample configuration file.

    Returns:
        Sample YAML configuration
    """
    return """# Croom USB Configuration
# Place this file on a USB drive as 'croom-config.yaml'

version: 1

device:
  name: "Conference Room A"
  location: "Building 1, Floor 2"
  timezone: "America/Los_Angeles"

network:
  wifi:
    ssid: "YourWiFiNetwork"
    password: "your-wifi-password"
    # For encrypted passwords, use: password: "encrypted:xxxxx"
    hidden: false

  # For enterprise WiFi (802.1X):
  # wifi:
  #   ssid: "CorpWiFi"
  #   enterprise: true
  #   eap_method: "peap"  # or "tls", "ttls"
  #   identity: "username"
  #   password: "password"

  # For Ethernet only:
  # ethernet: true

  # Static IP (optional):
  # static:
  #   ip: "192.168.1.100/24"
  #   gateway: "192.168.1.1"
  #   dns:
  #     - "8.8.8.8"
  #     - "8.8.4.4"

meeting:
  platform: "google_meet"  # or "teams", "zoom"
  credentials:
    email: "room-a@company.com"
    password: "your-account-password"

dashboard:
  url: "https://croom.yourcompany.com"
  enrollment_token: "your-enrollment-token"

calendar:
  provider: "google"  # or "microsoft"
  calendar_id: "primary"
"""

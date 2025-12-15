"""
Captive portal for Croom device provisioning.

Creates a WiFi access point with a web-based setup wizard.
"""

import asyncio
import logging
import subprocess
import secrets
import string
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class APConfig:
    """Access point configuration."""
    ssid_prefix: str = "Croom-Setup"
    password_length: int = 8
    channel: int = 6
    interface: str = "wlan0"
    ip_address: str = "192.168.4.1"
    dhcp_range_start: str = "192.168.4.10"
    dhcp_range_end: str = "192.168.4.100"
    setup_timeout: int = 1800  # 30 minutes


class CaptivePortal:
    """
    WiFi captive portal for device setup.

    Creates a temporary WiFi access point that redirects
    all traffic to the setup wizard.
    """

    def __init__(self, config: Optional[APConfig] = None):
        self.config = config or APConfig()
        self._running = False
        self._ssid: str = ""
        self._password: str = ""
        self._hostapd_proc: Optional[asyncio.subprocess.Process] = None
        self._dnsmasq_proc: Optional[asyncio.subprocess.Process] = None
        self._timeout_task: Optional[asyncio.Task] = None

        # Callbacks
        self._on_timeout: Optional[Callable] = None

    @property
    def ssid(self) -> str:
        """Get the AP SSID."""
        return self._ssid

    @property
    def password(self) -> str:
        """Get the AP password."""
        return self._password

    @property
    def ip_address(self) -> str:
        """Get the AP IP address."""
        return self.config.ip_address

    @property
    def is_running(self) -> bool:
        """Whether the AP is running."""
        return self._running

    def _generate_password(self) -> str:
        """Generate a random numeric password."""
        return ''.join(
            secrets.choice(string.digits)
            for _ in range(self.config.password_length)
        )

    def _generate_ssid(self) -> str:
        """Generate a unique SSID."""
        suffix = ''.join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(4)
        )
        return f"{self.config.ssid_prefix}-{suffix}"

    async def start(self) -> bool:
        """
        Start the captive portal.

        Returns:
            True if started successfully
        """
        if self._running:
            return True

        try:
            # Generate credentials
            self._ssid = self._generate_ssid()
            self._password = self._generate_password()

            logger.info(f"Starting captive portal: {self._ssid}")

            # Configure network interface
            if not await self._configure_interface():
                return False

            # Start hostapd
            if not await self._start_hostapd():
                await self.stop()
                return False

            # Start dnsmasq
            if not await self._start_dnsmasq():
                await self.stop()
                return False

            self._running = True

            # Start timeout
            if self.config.setup_timeout > 0:
                self._timeout_task = asyncio.create_task(self._timeout_handler())

            logger.info(f"Captive portal started: SSID={self._ssid}, Password={self._password}")
            return True

        except Exception as e:
            logger.error(f"Failed to start captive portal: {e}")
            await self.stop()
            return False

    async def stop(self) -> None:
        """Stop the captive portal."""
        logger.info("Stopping captive portal")

        # Cancel timeout
        if self._timeout_task:
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass
            self._timeout_task = None

        # Stop dnsmasq
        if self._dnsmasq_proc:
            self._dnsmasq_proc.terminate()
            try:
                await asyncio.wait_for(self._dnsmasq_proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._dnsmasq_proc.kill()
            self._dnsmasq_proc = None

        # Stop hostapd
        if self._hostapd_proc:
            self._hostapd_proc.terminate()
            try:
                await asyncio.wait_for(self._hostapd_proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._hostapd_proc.kill()
            self._hostapd_proc = None

        # Restore network interface
        await self._restore_interface()

        self._running = False
        logger.info("Captive portal stopped")

    async def _configure_interface(self) -> bool:
        """Configure the WiFi interface for AP mode."""
        interface = self.config.interface

        try:
            # Stop NetworkManager for this interface
            await self._run_command(
                "nmcli", "device", "set", interface, "managed", "no"
            )

            # Bring interface down
            await self._run_command("ip", "link", "set", interface, "down")

            # Assign IP address
            await self._run_command(
                "ip", "addr", "flush", "dev", interface
            )
            await self._run_command(
                "ip", "addr", "add",
                f"{self.config.ip_address}/24",
                "dev", interface
            )

            # Bring interface up
            await self._run_command("ip", "link", "set", interface, "up")

            return True

        except Exception as e:
            logger.error(f"Interface configuration error: {e}")
            return False

    async def _restore_interface(self) -> None:
        """Restore the WiFi interface to normal mode."""
        interface = self.config.interface

        try:
            # Re-enable NetworkManager
            await self._run_command(
                "nmcli", "device", "set", interface, "managed", "yes"
            )

        except Exception as e:
            logger.error(f"Interface restoration error: {e}")

    async def _start_hostapd(self) -> bool:
        """Start hostapd for WiFi AP."""
        config_path = Path("/tmp/croom-hostapd.conf")

        # Write hostapd configuration
        config_content = f"""interface={self.config.interface}
driver=nl80211
ssid={self._ssid}
hw_mode=g
channel={self.config.channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={self._password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
        config_path.write_text(config_content)

        try:
            self._hostapd_proc = await asyncio.create_subprocess_exec(
                "hostapd", str(config_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for startup
            await asyncio.sleep(2)

            if self._hostapd_proc.returncode is not None:
                stderr = await self._hostapd_proc.stderr.read()
                logger.error(f"hostapd failed: {stderr.decode()}")
                return False

            logger.info("hostapd started")
            return True

        except FileNotFoundError:
            logger.error("hostapd not installed: apt install hostapd")
            return False
        except Exception as e:
            logger.error(f"hostapd error: {e}")
            return False

    async def _start_dnsmasq(self) -> bool:
        """Start dnsmasq for DHCP and DNS."""
        interface = self.config.interface

        try:
            self._dnsmasq_proc = await asyncio.create_subprocess_exec(
                "dnsmasq",
                f"--interface={interface}",
                f"--dhcp-range={self.config.dhcp_range_start},{self.config.dhcp_range_end},12h",
                f"--address=/#/{self.config.ip_address}",  # Redirect all DNS to portal
                "--no-daemon",
                "--no-resolv",
                "--no-poll",
                "--log-queries",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for startup
            await asyncio.sleep(1)

            if self._dnsmasq_proc.returncode is not None:
                stderr = await self._dnsmasq_proc.stderr.read()
                logger.error(f"dnsmasq failed: {stderr.decode()}")
                return False

            logger.info("dnsmasq started")
            return True

        except FileNotFoundError:
            logger.error("dnsmasq not installed: apt install dnsmasq")
            return False
        except Exception as e:
            logger.error(f"dnsmasq error: {e}")
            return False

    async def _run_command(self, *args) -> Optional[str]:
        """Run a command and return output."""
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10.0,
            )
            return stdout.decode() if process.returncode == 0 else None
        except Exception:
            return None

    async def _timeout_handler(self) -> None:
        """Handle setup timeout."""
        try:
            await asyncio.sleep(self.config.setup_timeout)
            logger.warning("Captive portal timed out")

            if self._on_timeout:
                self._on_timeout()

            await self.stop()

        except asyncio.CancelledError:
            pass

    def on_timeout(self, callback: Callable) -> None:
        """Register callback for timeout event."""
        self._on_timeout = callback

    def get_display_info(self) -> Dict[str, Any]:
        """
        Get info to display on TV screen during setup.

        Returns:
            Dict with SSID, password, IP, and timeout
        """
        return {
            "ssid": self._ssid,
            "password": self._password,
            "ip": self.config.ip_address,
            "setup_url": f"http://{self.config.ip_address}:8080/setup",
            "timeout_seconds": self.config.setup_timeout,
        }

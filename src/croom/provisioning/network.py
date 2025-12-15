"""
Network configuration for Croom provisioning.

Manages WiFi and Ethernet configuration using NetworkManager.
"""

import asyncio
import logging
import subprocess
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class WiFiSecurity(Enum):
    """WiFi security types."""
    OPEN = "open"
    WPA_PSK = "wpa-psk"        # WPA/WPA2 Personal
    WPA_EAP = "wpa-eap"        # WPA/WPA2 Enterprise (802.1X)
    WPA3_SAE = "sae"           # WPA3 Personal


class EAPMethod(Enum):
    """EAP authentication methods for 802.1X."""
    PEAP = "peap"              # Username/password
    TLS = "tls"                # Certificate-based
    TTLS = "ttls"              # Tunneled TLS


@dataclass
class WiFiNetwork:
    """Discovered WiFi network information."""
    ssid: str
    bssid: str
    signal_strength: int      # 0-100
    frequency: int            # MHz
    security: WiFiSecurity
    is_connected: bool = False


@dataclass
class WiFiConfig:
    """WiFi configuration."""
    ssid: str
    password: Optional[str] = None
    security: WiFiSecurity = WiFiSecurity.WPA_PSK
    hidden: bool = False

    # Enterprise WiFi (802.1X)
    eap_method: Optional[EAPMethod] = None
    identity: Optional[str] = None          # Username
    anonymous_identity: Optional[str] = None
    ca_cert: Optional[str] = None           # Path to CA certificate
    client_cert: Optional[str] = None       # Path to client certificate
    private_key: Optional[str] = None       # Path to private key
    private_key_password: Optional[str] = None


@dataclass
class NetworkConfig:
    """Complete network configuration."""
    wifi: Optional[WiFiConfig] = None
    use_ethernet: bool = False
    static_ip: Optional[str] = None
    gateway: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)
    proxy_url: Optional[str] = None


class NetworkManager:
    """
    Network configuration manager.

    Uses NetworkManager (nmcli) for WiFi and Ethernet configuration.
    """

    def __init__(self):
        self._nm_available = False

    async def initialize(self) -> bool:
        """Check if NetworkManager is available."""
        try:
            result = await self._run_command("nmcli", "--version")
            if result:
                self._nm_available = True
                logger.info("NetworkManager available")
                return True
        except Exception as e:
            logger.warning(f"NetworkManager not available: {e}")

        return False

    async def _run_command(
        self,
        *args,
        input_text: Optional[str] = None
    ) -> Optional[str]:
        """Run a command and return output."""
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE if input_text else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_text.encode() if input_text else None),
                timeout=30.0,
            )

            if process.returncode != 0:
                logger.debug(f"Command failed: {stderr.decode()}")
                return None

            return stdout.decode()

        except asyncio.TimeoutError:
            logger.error("Command timeout")
            return None
        except Exception as e:
            logger.error(f"Command error: {e}")
            return None

    async def scan_wifi_networks(self) -> List[WiFiNetwork]:
        """
        Scan for available WiFi networks.

        Returns:
            List of discovered networks
        """
        if not self._nm_available:
            return []

        try:
            # Trigger rescan
            await self._run_command("nmcli", "device", "wifi", "rescan")
            await asyncio.sleep(2)  # Wait for scan

            # Get results
            output = await self._run_command(
                "nmcli", "-t", "-f", "SSID,BSSID,SIGNAL,FREQ,SECURITY,ACTIVE",
                "device", "wifi", "list"
            )

            if not output:
                return []

            networks = []
            seen_ssids = set()

            for line in output.strip().split('\n'):
                if not line:
                    continue

                parts = line.split(':')
                if len(parts) < 6:
                    continue

                ssid = parts[0]
                if not ssid or ssid in seen_ssids:
                    continue

                seen_ssids.add(ssid)

                # Parse security
                security_str = parts[4].lower()
                if 'wpa3' in security_str or 'sae' in security_str:
                    security = WiFiSecurity.WPA3_SAE
                elif 'wpa' in security_str and 'eap' in security_str:
                    security = WiFiSecurity.WPA_EAP
                elif 'wpa' in security_str:
                    security = WiFiSecurity.WPA_PSK
                else:
                    security = WiFiSecurity.OPEN

                networks.append(WiFiNetwork(
                    ssid=ssid,
                    bssid=parts[1],
                    signal_strength=int(parts[2]) if parts[2].isdigit() else 0,
                    frequency=int(parts[3].replace(' MHz', '')) if parts[3] else 0,
                    security=security,
                    is_connected=parts[5].lower() == 'yes',
                ))

            # Sort by signal strength
            networks.sort(key=lambda n: n.signal_strength, reverse=True)

            logger.info(f"Found {len(networks)} WiFi networks")
            return networks

        except Exception as e:
            logger.error(f"WiFi scan error: {e}")
            return []

    async def connect_wifi(self, config: WiFiConfig) -> bool:
        """
        Connect to a WiFi network.

        Args:
            config: WiFi configuration

        Returns:
            True if connected successfully
        """
        if not self._nm_available:
            return False

        try:
            # Check if connection already exists
            existing = await self._run_command(
                "nmcli", "-t", "-f", "NAME,TYPE",
                "connection", "show"
            )

            connection_name = f"croom-{config.ssid}"

            if existing and connection_name in existing:
                # Delete existing connection
                await self._run_command(
                    "nmcli", "connection", "delete", connection_name
                )

            # Build connection command based on security type
            if config.security == WiFiSecurity.OPEN:
                result = await self._run_command(
                    "nmcli", "device", "wifi", "connect", config.ssid,
                    "name", connection_name,
                    "hidden", "yes" if config.hidden else "no",
                )

            elif config.security in (WiFiSecurity.WPA_PSK, WiFiSecurity.WPA3_SAE):
                result = await self._run_command(
                    "nmcli", "device", "wifi", "connect", config.ssid,
                    "password", config.password,
                    "name", connection_name,
                    "hidden", "yes" if config.hidden else "no",
                )

            elif config.security == WiFiSecurity.WPA_EAP:
                result = await self._connect_enterprise_wifi(config, connection_name)

            else:
                logger.error(f"Unsupported security type: {config.security}")
                return False

            if result is None:
                return False

            # Verify connection
            await asyncio.sleep(3)
            return await self.is_connected()

        except Exception as e:
            logger.error(f"WiFi connection error: {e}")
            return False

    async def _connect_enterprise_wifi(
        self,
        config: WiFiConfig,
        connection_name: str
    ) -> Optional[str]:
        """Connect to 802.1X enterprise WiFi."""

        # Create connection
        cmd = [
            "nmcli", "connection", "add",
            "type", "wifi",
            "con-name", connection_name,
            "ssid", config.ssid,
            "wifi-sec.key-mgmt", "wpa-eap",
        ]

        # Add EAP settings
        if config.eap_method == EAPMethod.PEAP:
            cmd.extend([
                "802-1x.eap", "peap",
                "802-1x.phase2-auth", "mschapv2",
                "802-1x.identity", config.identity,
                "802-1x.password", config.password,
            ])

        elif config.eap_method == EAPMethod.TLS:
            cmd.extend([
                "802-1x.eap", "tls",
                "802-1x.identity", config.identity,
                "802-1x.client-cert", config.client_cert,
                "802-1x.private-key", config.private_key,
            ])
            if config.private_key_password:
                cmd.extend(["802-1x.private-key-password", config.private_key_password])

        elif config.eap_method == EAPMethod.TTLS:
            cmd.extend([
                "802-1x.eap", "ttls",
                "802-1x.phase2-auth", "pap",
                "802-1x.identity", config.identity,
                "802-1x.password", config.password,
            ])

        # Add CA certificate if provided
        if config.ca_cert:
            cmd.extend(["802-1x.ca-cert", config.ca_cert])

        # Add anonymous identity if provided
        if config.anonymous_identity:
            cmd.extend(["802-1x.anonymous-identity", config.anonymous_identity])

        result = await self._run_command(*cmd)
        if result is None:
            return None

        # Activate connection
        return await self._run_command(
            "nmcli", "connection", "up", connection_name
        )

    async def disconnect_wifi(self) -> bool:
        """Disconnect from current WiFi."""
        if not self._nm_available:
            return False

        try:
            # Get active WiFi connection
            output = await self._run_command(
                "nmcli", "-t", "-f", "NAME,TYPE,DEVICE",
                "connection", "show", "--active"
            )

            if not output:
                return True

            for line in output.strip().split('\n'):
                parts = line.split(':')
                if len(parts) >= 3 and parts[1] == '802-11-wireless':
                    await self._run_command(
                        "nmcli", "connection", "down", parts[0]
                    )

            return True

        except Exception as e:
            logger.error(f"WiFi disconnect error: {e}")
            return False

    async def is_connected(self) -> bool:
        """Check if connected to any network."""
        if not self._nm_available:
            return False

        try:
            output = await self._run_command(
                "nmcli", "-t", "-f", "STATE",
                "networking", "connectivity"
            )

            return output and 'full' in output.lower()

        except Exception:
            return False

    async def get_current_ip(self) -> Optional[str]:
        """Get current IP address."""
        try:
            output = await self._run_command(
                "hostname", "-I"
            )

            if output:
                ips = output.strip().split()
                return ips[0] if ips else None

            return None

        except Exception:
            return None

    async def configure_static_ip(
        self,
        connection_name: str,
        ip_address: str,
        gateway: str,
        dns_servers: List[str]
    ) -> bool:
        """Configure static IP for a connection."""
        if not self._nm_available:
            return False

        try:
            # Set to manual
            await self._run_command(
                "nmcli", "connection", "modify", connection_name,
                "ipv4.method", "manual",
                "ipv4.addresses", ip_address,
                "ipv4.gateway", gateway,
                "ipv4.dns", ",".join(dns_servers),
            )

            # Restart connection
            await self._run_command(
                "nmcli", "connection", "down", connection_name
            )
            await self._run_command(
                "nmcli", "connection", "up", connection_name
            )

            return True

        except Exception as e:
            logger.error(f"Static IP configuration error: {e}")
            return False

    async def test_connection(self, target: str = "8.8.8.8") -> bool:
        """Test network connectivity."""
        try:
            result = await self._run_command(
                "ping", "-c", "1", "-W", "5", target
            )
            return result is not None
        except Exception:
            return False

    async def test_dns(self, hostname: str = "google.com") -> bool:
        """Test DNS resolution."""
        try:
            result = await self._run_command(
                "host", hostname
            )
            return result is not None and "has address" in result
        except Exception:
            return False

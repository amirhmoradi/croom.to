"""
Device discovery service for Croom dashboard.

Provides network-based device discovery using mDNS/Zeroconf and SSDP.
"""

import asyncio
import logging
import socket
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class DiscoveryProtocol(Enum):
    """Discovery protocol types."""
    MDNS = "mdns"
    SSDP = "ssdp"
    MANUAL = "manual"


@dataclass
class DiscoveredDevice:
    """Discovered device information."""
    device_id: str
    ip_address: str
    hostname: str = ""
    port: int = 3000
    protocol: DiscoveryProtocol = DiscoveryProtocol.MANUAL
    device_type: str = "croom"
    name: str = ""
    version: str = ""
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "hostname": self.hostname,
            "port": self.port,
            "protocol": self.protocol.value,
            "device_type": self.device_type,
            "name": self.name,
            "version": self.version,
            "discovered_at": self.discovered_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "properties": self.properties,
        }


class MDNSBrowser:
    """
    mDNS/Zeroconf browser for discovering Croom devices.

    Uses the zeroconf library to browse for _croom._tcp.local. services.
    """

    SERVICE_TYPE = "_croom._tcp.local."

    def __init__(self):
        self._zeroconf = None
        self._browser = None
        self._devices: Dict[str, DiscoveredDevice] = {}
        self._callbacks: List[Callable[[DiscoveredDevice, bool], None]] = []

    async def start(self) -> bool:
        """Start mDNS browsing."""
        try:
            from zeroconf import Zeroconf, ServiceBrowser
        except ImportError:
            logger.error("zeroconf library not installed. Install with: pip install zeroconf")
            return False

        try:
            loop = asyncio.get_event_loop()
            self._zeroconf = await loop.run_in_executor(None, Zeroconf)
            self._browser = await loop.run_in_executor(
                None,
                lambda: ServiceBrowser(self._zeroconf, self.SERVICE_TYPE, self)
            )
            logger.info("mDNS browser started")
            return True
        except Exception as e:
            logger.error(f"Failed to start mDNS browser: {e}")
            return False

    async def stop(self) -> None:
        """Stop mDNS browsing."""
        if self._browser:
            self._browser.cancel()
            self._browser = None

        if self._zeroconf:
            await asyncio.get_event_loop().run_in_executor(
                None, self._zeroconf.close
            )
            self._zeroconf = None

        logger.info("mDNS browser stopped")

    def add_service(self, zeroconf, service_type: str, name: str) -> None:
        """Callback when service is discovered (zeroconf interface)."""
        asyncio.create_task(self._handle_service_added(zeroconf, service_type, name))

    def remove_service(self, zeroconf, service_type: str, name: str) -> None:
        """Callback when service is removed (zeroconf interface)."""
        asyncio.create_task(self._handle_service_removed(name))

    def update_service(self, zeroconf, service_type: str, name: str) -> None:
        """Callback when service is updated (zeroconf interface)."""
        asyncio.create_task(self._handle_service_added(zeroconf, service_type, name))

    async def _handle_service_added(self, zeroconf, service_type: str, name: str) -> None:
        """Handle service discovery."""
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: zeroconf.get_service_info(service_type, name)
            )

            if not info:
                return

            # Parse service info
            ip_bytes = info.addresses[0] if info.addresses else None
            if not ip_bytes:
                return

            ip_address = socket.inet_ntoa(ip_bytes)
            hostname = info.server.rstrip('.')
            port = info.port

            # Get device ID from name or properties
            device_id = name.split('.')[0]
            properties = {}

            for key, value in info.properties.items():
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                properties[key] = value

            device = DiscoveredDevice(
                device_id=device_id,
                ip_address=ip_address,
                hostname=hostname,
                port=port,
                protocol=DiscoveryProtocol.MDNS,
                name=properties.get('name', device_id),
                version=properties.get('version', ''),
                properties=properties,
            )

            self._devices[device_id] = device
            logger.info(f"Discovered device via mDNS: {device_id} at {ip_address}")

            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(device, True)  # True = added
                except Exception as e:
                    logger.error(f"Discovery callback error: {e}")

        except Exception as e:
            logger.error(f"Error handling mDNS service: {e}")

    async def _handle_service_removed(self, name: str) -> None:
        """Handle service removal."""
        device_id = name.split('.')[0]
        device = self._devices.pop(device_id, None)

        if device:
            logger.info(f"Device removed: {device_id}")
            for callback in self._callbacks:
                try:
                    callback(device, False)  # False = removed
                except Exception as e:
                    logger.error(f"Discovery callback error: {e}")

    def on_device_change(self, callback: Callable[[DiscoveredDevice, bool], None]) -> None:
        """Register callback for device discovery/removal."""
        self._callbacks.append(callback)

    def get_devices(self) -> List[DiscoveredDevice]:
        """Get all discovered devices."""
        return list(self._devices.values())


class SSDPBrowser:
    """
    SSDP (Simple Service Discovery Protocol) browser.

    Used for discovering UPnP devices on the network.
    """

    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    SEARCH_TARGET = "urn:croom:device:conferenceroom:1"

    def __init__(self):
        self._devices: Dict[str, DiscoveredDevice] = {}
        self._callbacks: List[Callable[[DiscoveredDevice, bool], None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._socket: Optional[socket.socket] = None

    async def start(self) -> bool:
        """Start SSDP browsing."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
            self._socket.settimeout(0.5)

            self._running = True
            self._task = asyncio.create_task(self._browse_loop())

            logger.info("SSDP browser started")
            return True

        except Exception as e:
            logger.error(f"Failed to start SSDP browser: {e}")
            return False

    async def stop(self) -> None:
        """Stop SSDP browsing."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._socket:
            self._socket.close()
            self._socket = None

        logger.info("SSDP browser stopped")

    async def _browse_loop(self) -> None:
        """Background browsing loop."""
        while self._running:
            try:
                await self._send_discovery()
                await self._receive_responses()
                await asyncio.sleep(30)  # Discover every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"SSDP browse error: {e}")
                await asyncio.sleep(5)

    async def _send_discovery(self) -> None:
        """Send SSDP M-SEARCH request."""
        search_request = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n"
            "MAN: \"ssdp:discover\"\r\n"
            "MX: 3\r\n"
            f"ST: {self.SEARCH_TARGET}\r\n"
            "\r\n"
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._socket.sendto(
                search_request.encode('utf-8'),
                (self.SSDP_ADDR, self.SSDP_PORT)
            )
        )

    async def _receive_responses(self) -> None:
        """Receive SSDP responses."""
        loop = asyncio.get_event_loop()

        for _ in range(10):  # Check for responses
            try:
                data, addr = await loop.run_in_executor(
                    None,
                    lambda: self._socket.recvfrom(1024)
                )

                await self._parse_response(data.decode('utf-8'), addr[0])

            except socket.timeout:
                break
            except Exception as e:
                logger.debug(f"SSDP receive error: {e}")
                break

    async def _parse_response(self, response: str, ip_address: str) -> None:
        """Parse SSDP response."""
        lines = response.split('\r\n')
        headers = {}

        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.upper().strip()] = value.strip()

        # Check if it's a Croom device
        if self.SEARCH_TARGET not in headers.get('ST', ''):
            return

        # Parse device info
        usn = headers.get('USN', '')
        device_id = usn.split('::')[0].replace('uuid:', '') if '::' in usn else ip_address

        location = headers.get('LOCATION', '')
        port = 3000
        if location:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(location)
                port = parsed.port or 3000
            except Exception:
                pass

        device = DiscoveredDevice(
            device_id=device_id,
            ip_address=ip_address,
            port=port,
            protocol=DiscoveryProtocol.SSDP,
            name=headers.get('SERVER', device_id),
            properties={
                'location': location,
                'cache_control': headers.get('CACHE-CONTROL', ''),
            },
        )

        if device_id not in self._devices:
            self._devices[device_id] = device
            logger.info(f"Discovered device via SSDP: {device_id} at {ip_address}")

            for callback in self._callbacks:
                try:
                    callback(device, True)
                except Exception as e:
                    logger.error(f"Discovery callback error: {e}")
        else:
            # Update last seen
            self._devices[device_id].last_seen = datetime.now(timezone.utc)

    def on_device_change(self, callback: Callable[[DiscoveredDevice, bool], None]) -> None:
        """Register callback for device discovery/removal."""
        self._callbacks.append(callback)

    def get_devices(self) -> List[DiscoveredDevice]:
        """Get all discovered devices."""
        return list(self._devices.values())


class NetworkScanner:
    """
    Network scanner for manual device discovery.

    Scans IP ranges for Croom devices by checking known ports.
    """

    DEFAULT_PORT = 3000

    def __init__(self):
        self._devices: Dict[str, DiscoveredDevice] = {}

    async def scan_range(
        self,
        network: str = "192.168.1.0/24",
        port: int = DEFAULT_PORT,
        timeout: float = 1.0,
        on_found: Optional[Callable[[DiscoveredDevice], None]] = None,
    ) -> List[DiscoveredDevice]:
        """
        Scan an IP range for Croom devices.

        Args:
            network: CIDR network range (e.g., "192.168.1.0/24")
            port: Port to scan
            timeout: Connection timeout
            on_found: Callback for each found device

        Returns:
            List of discovered devices
        """
        import ipaddress

        try:
            net = ipaddress.ip_network(network, strict=False)
        except ValueError as e:
            logger.error(f"Invalid network: {e}")
            return []

        tasks = []
        for ip in net.hosts():
            tasks.append(self._check_host(str(ip), port, timeout, on_found))

        await asyncio.gather(*tasks, return_exceptions=True)

        return list(self._devices.values())

    async def scan_single(
        self,
        ip_address: str,
        port: int = DEFAULT_PORT,
        timeout: float = 2.0,
    ) -> Optional[DiscoveredDevice]:
        """
        Scan a single IP address for a Croom device.

        Args:
            ip_address: IP address to check
            port: Port to scan
            timeout: Connection timeout

        Returns:
            DiscoveredDevice if found, None otherwise
        """
        await self._check_host(ip_address, port, timeout, None)
        return self._devices.get(ip_address)

    async def _check_host(
        self,
        ip_address: str,
        port: int,
        timeout: float,
        on_found: Optional[Callable],
    ) -> None:
        """Check if a host has a Croom device."""
        try:
            # Try TCP connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip_address, port),
                timeout=timeout,
            )
            writer.close()
            await writer.wait_closed()

            # Connection succeeded - try to get device info
            device = await self._get_device_info(ip_address, port, timeout)

            if device:
                self._devices[ip_address] = device
                logger.info(f"Found device: {device.device_id} at {ip_address}")

                if on_found:
                    try:
                        on_found(device)
                    except Exception as e:
                        logger.error(f"Scan callback error: {e}")

        except asyncio.TimeoutError:
            pass
        except ConnectionRefusedError:
            pass
        except Exception:
            pass

    async def _get_device_info(
        self,
        ip_address: str,
        port: int,
        timeout: float,
    ) -> Optional[DiscoveredDevice]:
        """Get device info via HTTP API."""
        try:
            import aiohttp

            url = f"http://{ip_address}:{port}/api/device/info"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        return DiscoveredDevice(
                            device_id=data.get('device_id', ip_address),
                            ip_address=ip_address,
                            hostname=data.get('hostname', ''),
                            port=port,
                            protocol=DiscoveryProtocol.MANUAL,
                            device_type=data.get('device_type', 'croom'),
                            name=data.get('name', ''),
                            version=data.get('version', ''),
                            properties=data,
                        )

        except Exception:
            # Device doesn't have API or error occurred
            return DiscoveredDevice(
                device_id=ip_address,
                ip_address=ip_address,
                port=port,
                protocol=DiscoveryProtocol.MANUAL,
            )

        return None


class DeviceDiscoveryService:
    """
    Unified device discovery service.

    Combines mDNS, SSDP, and manual scanning for comprehensive discovery.
    """

    def __init__(self):
        self._mdns = MDNSBrowser()
        self._ssdp = SSDPBrowser()
        self._scanner = NetworkScanner()
        self._devices: Dict[str, DiscoveredDevice] = {}
        self._callbacks: List[Callable[[DiscoveredDevice, bool], None]] = []

        # Register internal callbacks
        self._mdns.on_device_change(self._on_device_change)
        self._ssdp.on_device_change(self._on_device_change)

    async def start(self) -> None:
        """Start all discovery mechanisms."""
        await self._mdns.start()
        await self._ssdp.start()
        logger.info("Device discovery service started")

    async def stop(self) -> None:
        """Stop all discovery mechanisms."""
        await self._mdns.stop()
        await self._ssdp.stop()
        logger.info("Device discovery service stopped")

    def _on_device_change(self, device: DiscoveredDevice, added: bool) -> None:
        """Handle device discovery/removal."""
        if added:
            self._devices[device.device_id] = device
        else:
            self._devices.pop(device.device_id, None)

        for callback in self._callbacks:
            try:
                callback(device, added)
            except Exception as e:
                logger.error(f"Discovery callback error: {e}")

    def on_device_change(self, callback: Callable[[DiscoveredDevice, bool], None]) -> None:
        """Register callback for device discovery/removal."""
        self._callbacks.append(callback)

    def get_devices(self) -> List[DiscoveredDevice]:
        """Get all discovered devices."""
        return list(self._devices.values())

    def get_device(self, device_id: str) -> Optional[DiscoveredDevice]:
        """Get device by ID."""
        return self._devices.get(device_id)

    async def scan_network(
        self,
        network: str,
        port: int = 3000,
    ) -> List[DiscoveredDevice]:
        """Scan network for devices."""
        devices = await self._scanner.scan_range(
            network,
            port,
            on_found=lambda d: self._on_device_change(d, True),
        )
        return devices

    async def add_device_manually(
        self,
        ip_address: str,
        port: int = 3000,
        name: str = "",
    ) -> Optional[DiscoveredDevice]:
        """Add a device manually."""
        device = await self._scanner.scan_single(ip_address, port)

        if device:
            if name:
                device.name = name
            self._devices[device.device_id] = device
            self._on_device_change(device, True)

        return device

    def remove_device(self, device_id: str) -> bool:
        """Remove a device."""
        device = self._devices.pop(device_id, None)
        if device:
            self._on_device_change(device, False)
            return True
        return False

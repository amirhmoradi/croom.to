"""
Tests for croom.dashboard.discovery module.
"""

import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

import pytest

from croom.dashboard.discovery import (
    DiscoveredDevice,
    DiscoveryProtocol,
    MDNSBrowser,
    SSDPBrowser,
    NetworkScanner,
    DeviceDiscoveryService,
)


class TestDiscoveryProtocol:
    """Tests for DiscoveryProtocol enum."""

    def test_values(self):
        """Test discovery protocol enum values."""
        assert DiscoveryProtocol.MDNS.value == "mdns"
        assert DiscoveryProtocol.SSDP.value == "ssdp"
        assert DiscoveryProtocol.MANUAL.value == "manual"


class TestDiscoveredDevice:
    """Tests for DiscoveredDevice dataclass."""

    def test_creation(self):
        """Test creating a discovered device."""
        device = DiscoveredDevice(
            device_id="croom-001",
            ip_address="192.168.1.100",
            hostname="croom-room-101",
            port=3000,
            protocol=DiscoveryProtocol.MDNS,
        )

        assert device.device_id == "croom-001"
        assert device.hostname == "croom-room-101"
        assert device.ip_address == "192.168.1.100"
        assert device.port == 3000
        assert device.protocol == DiscoveryProtocol.MDNS

    def test_default_values(self):
        """Test default field values."""
        device = DiscoveredDevice(
            device_id="croom-001",
            ip_address="192.168.1.100",
        )

        assert device.hostname == ""
        assert device.port == 3000
        assert device.protocol == DiscoveryProtocol.MANUAL
        assert device.device_type == "croom"
        assert device.name == ""
        assert device.version == ""

    def test_to_dict(self):
        """Test converting device to dictionary."""
        device = DiscoveredDevice(
            device_id="croom-001",
            ip_address="192.168.1.100",
            name="Conference Room",
        )
        result = device.to_dict()

        assert result["device_id"] == "croom-001"
        assert result["ip_address"] == "192.168.1.100"
        assert result["name"] == "Conference Room"
        assert "discovered_at" in result
        assert "last_seen" in result


class TestMDNSBrowser:
    """Tests for MDNSBrowser class."""

    def test_init(self):
        """Test mDNS browser initialization."""
        browser = MDNSBrowser()

        assert browser._zeroconf is None
        assert browser._browser is None
        assert len(browser._devices) == 0

    def test_service_type(self):
        """Test mDNS service type."""
        assert MDNSBrowser.SERVICE_TYPE == "_croom._tcp.local."

    @pytest.mark.asyncio
    async def test_start_no_zeroconf(self):
        """Test start without zeroconf library."""
        browser = MDNSBrowser()

        with patch.dict("sys.modules", {"zeroconf": None}):
            with patch("builtins.__import__", side_effect=ImportError()):
                result = await browser.start()
                assert result is False

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stopping mDNS browser."""
        browser = MDNSBrowser()
        mock_browser_obj = MagicMock()
        mock_browser_obj.cancel = MagicMock()
        browser._browser = mock_browser_obj
        mock_zeroconf = MagicMock()
        mock_zeroconf.close = MagicMock()
        browser._zeroconf = mock_zeroconf

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock()
            await browser.stop()

            # Verify browser was stopped
            assert browser._browser is None or mock_browser_obj.cancel.called

    def test_get_devices(self):
        """Test getting discovered devices."""
        browser = MDNSBrowser()
        browser._devices = {
            "device1": DiscoveredDevice(device_id="device1", ip_address="192.168.1.100"),
            "device2": DiscoveredDevice(device_id="device2", ip_address="192.168.1.101"),
        }

        devices = browser.get_devices()
        assert len(devices) == 2

    def test_on_device_change_callback(self):
        """Test registering device change callback."""
        browser = MDNSBrowser()
        callback = MagicMock()

        browser.on_device_change(callback)

        assert callback in browser._callbacks


class TestSSDPBrowser:
    """Tests for SSDPBrowser class."""

    def test_init(self):
        """Test SSDP browser initialization."""
        browser = SSDPBrowser()

        assert len(browser._devices) == 0
        assert browser._running is False

    def test_constants(self):
        """Test SSDP constants."""
        assert SSDPBrowser.SSDP_ADDR == "239.255.255.250"
        assert SSDPBrowser.SSDP_PORT == 1900

    @pytest.mark.asyncio
    async def test_start(self):
        """Test starting SSDP browser."""
        browser = SSDPBrowser()

        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            result = await browser.start()

            assert result is True
            assert browser._running is True

            # Clean up
            await browser.stop()

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stopping SSDP browser."""
        browser = SSDPBrowser()
        browser._running = True
        browser._task = asyncio.create_task(asyncio.sleep(10))
        mock_socket = MagicMock()
        browser._socket = mock_socket

        await browser.stop()

        assert browser._running is False
        mock_socket.close.assert_called_once()

    def test_get_devices(self):
        """Test getting discovered devices."""
        browser = SSDPBrowser()
        browser._devices = {
            "device1": DiscoveredDevice(device_id="device1", ip_address="192.168.1.100"),
        }

        devices = browser.get_devices()
        assert len(devices) == 1

    def test_on_device_change_callback(self):
        """Test registering device change callback."""
        browser = SSDPBrowser()
        callback = MagicMock()

        browser.on_device_change(callback)

        assert callback in browser._callbacks


class TestNetworkScanner:
    """Tests for NetworkScanner class."""

    def test_init(self):
        """Test network scanner initialization."""
        scanner = NetworkScanner()

        assert len(scanner._devices) == 0

    def test_default_port(self):
        """Test default port constant."""
        assert NetworkScanner.DEFAULT_PORT == 3000

    @pytest.mark.asyncio
    async def test_scan_single_not_found(self):
        """Test scanning single IP that doesn't respond."""
        scanner = NetworkScanner()

        with patch("asyncio.open_connection", side_effect=asyncio.TimeoutError()):
            result = await scanner.scan_single("192.168.1.100", timeout=0.1)
            assert result is None

    @pytest.mark.asyncio
    async def test_scan_single_found(self):
        """Test scanning single IP that responds."""
        scanner = NetworkScanner()

        with patch("asyncio.open_connection") as mock_connect:
            mock_reader = AsyncMock()
            mock_writer = MagicMock()
            mock_writer.close = MagicMock()
            mock_writer.wait_closed = AsyncMock()
            mock_connect.return_value = (mock_reader, mock_writer)

            with patch.object(scanner, "_get_device_info", new_callable=AsyncMock) as mock_get_info:
                mock_device = DiscoveredDevice(
                    device_id="192.168.1.100",
                    ip_address="192.168.1.100",
                )
                mock_get_info.return_value = mock_device

                result = await scanner.scan_single("192.168.1.100", timeout=1)
                assert result is not None
                assert result.ip_address == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_scan_range_invalid_network(self):
        """Test scanning invalid network range."""
        scanner = NetworkScanner()

        result = await scanner.scan_range("invalid-network")
        assert result == []


class TestDeviceDiscoveryService:
    """Tests for DeviceDiscoveryService class."""

    def test_init(self):
        """Test discovery service initialization."""
        service = DeviceDiscoveryService()

        assert isinstance(service._mdns, MDNSBrowser)
        assert isinstance(service._ssdp, SSDPBrowser)
        assert isinstance(service._scanner, NetworkScanner)
        assert len(service._devices) == 0

    @pytest.mark.asyncio
    async def test_start(self):
        """Test starting discovery service."""
        service = DeviceDiscoveryService()

        with patch.object(service._mdns, "start", new_callable=AsyncMock) as mock_mdns:
            with patch.object(service._ssdp, "start", new_callable=AsyncMock) as mock_ssdp:
                await service.start()
                mock_mdns.assert_called_once()
                mock_ssdp.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stopping discovery service."""
        service = DeviceDiscoveryService()

        with patch.object(service._mdns, "stop", new_callable=AsyncMock) as mock_mdns:
            with patch.object(service._ssdp, "stop", new_callable=AsyncMock) as mock_ssdp:
                await service.stop()
                mock_mdns.assert_called_once()
                mock_ssdp.assert_called_once()

    def test_get_devices(self):
        """Test getting all discovered devices."""
        service = DeviceDiscoveryService()
        service._devices = {
            "device1": DiscoveredDevice(device_id="device1", ip_address="192.168.1.100"),
            "device2": DiscoveredDevice(device_id="device2", ip_address="192.168.1.101"),
        }

        devices = service.get_devices()
        assert len(devices) == 2

    def test_get_device(self):
        """Test getting device by ID."""
        service = DeviceDiscoveryService()
        device = DiscoveredDevice(device_id="device1", ip_address="192.168.1.100")
        service._devices["device1"] = device

        result = service.get_device("device1")
        assert result == device

        result = service.get_device("nonexistent")
        assert result is None

    def test_remove_device(self):
        """Test removing a device."""
        service = DeviceDiscoveryService()
        device = DiscoveredDevice(device_id="device1", ip_address="192.168.1.100")
        service._devices["device1"] = device

        result = service.remove_device("device1")
        assert result is True
        assert "device1" not in service._devices

        result = service.remove_device("nonexistent")
        assert result is False

    def test_on_device_change_callback(self):
        """Test registering device change callback."""
        service = DeviceDiscoveryService()
        callback = MagicMock()

        service.on_device_change(callback)

        assert callback in service._callbacks

    @pytest.mark.asyncio
    async def test_add_device_manually(self):
        """Test adding device manually."""
        service = DeviceDiscoveryService()

        with patch.object(service._scanner, "scan_single", new_callable=AsyncMock) as mock_scan:
            mock_device = DiscoveredDevice(
                device_id="192.168.1.100",
                ip_address="192.168.1.100",
            )
            mock_scan.return_value = mock_device

            result = await service.add_device_manually("192.168.1.100", name="Test Device")

            assert result is not None
            assert result.name == "Test Device"
            assert "192.168.1.100" in service._devices

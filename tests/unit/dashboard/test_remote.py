"""
Tests for croom.dashboard.remote module.
"""

import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

import pytest

from croom.dashboard.remote import (
    ScreenshotService,
    ShellService,
    DiagnosticsService,
    DeviceControlService,
    RemoteOperationsManager,
)


class TestScreenshotService:
    """Tests for ScreenshotService class."""

    def test_init(self):
        """Test screenshot service initialization."""
        service = ScreenshotService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_capture_no_display(self):
        """Test capture when no display tools available."""
        service = ScreenshotService()

        with patch("shutil.which", return_value=None):
            result = await service.capture()
            # Should return None when no screenshot tool is available
            assert result is None

    @pytest.mark.asyncio
    async def test_capture_with_scrot(self):
        """Test capture using scrot."""
        service = ScreenshotService()

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: "/usr/bin/scrot" if x == "scrot" else None

            with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"", b"")
                mock_exec.return_value = mock_process

                with patch("builtins.open", MagicMock()):
                    with patch("os.path.exists", return_value=True):
                        with patch("os.remove"):
                            result = await service.capture()
                            # Scrot was called
                            mock_exec.assert_called()

    def test_get_supported_tools(self):
        """Test getting list of supported screenshot tools."""
        service = ScreenshotService()
        tools = service.get_supported_tools()

        assert "scrot" in tools
        assert "import" in tools
        assert "gnome-screenshot" in tools


class TestShellService:
    """Tests for ShellService class."""

    def test_init(self):
        """Test shell service initialization."""
        service = ShellService()
        assert service is not None
        assert len(service._allowed_commands) > 0

    def test_command_whitelist(self):
        """Test command whitelist contains expected commands."""
        service = ShellService()

        assert "systemctl" in service._allowed_commands
        assert "journalctl" in service._allowed_commands
        assert "df" in service._allowed_commands
        assert "free" in service._allowed_commands

    def test_is_allowed_command(self):
        """Test checking if command is allowed."""
        service = ShellService()

        assert service._is_allowed("systemctl status croom") is True
        assert service._is_allowed("rm -rf /") is False
        assert service._is_allowed("df -h") is True

    @pytest.mark.asyncio
    async def test_execute_allowed_command(self):
        """Test executing allowed command."""
        service = ShellService()

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"output", b"")
            mock_exec.return_value = mock_process

            result = await service.execute("df -h")

            assert result["success"] is True
            assert result["stdout"] == "output"
            assert result["return_code"] == 0

    @pytest.mark.asyncio
    async def test_execute_blocked_command(self):
        """Test executing blocked command."""
        service = ShellService()

        result = await service.execute("rm -rf /")

        assert result["success"] is False
        assert "not allowed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """Test command execution with timeout."""
        service = ShellService()

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.side_effect = asyncio.TimeoutError()
            mock_process.kill = MagicMock()
            mock_exec.return_value = mock_process

            result = await service.execute("df -h", timeout=1)

            assert result["success"] is False
            assert "timeout" in result["error"].lower()


class TestDiagnosticsService:
    """Tests for DiagnosticsService class."""

    def test_init(self):
        """Test diagnostics service initialization."""
        service = DiagnosticsService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_get_system_info(self):
        """Test getting system information."""
        service = DiagnosticsService()

        with patch("platform.system", return_value="Linux"):
            with patch("platform.release", return_value="5.10.0"):
                with patch("platform.machine", return_value="aarch64"):
                    with patch("psutil.cpu_percent", return_value=25.0):
                        with patch("psutil.virtual_memory") as mock_mem:
                            mock_mem.return_value.percent = 50.0
                            mock_mem.return_value.total = 8 * 1024**3
                            mock_mem.return_value.available = 4 * 1024**3

                            with patch("psutil.disk_usage") as mock_disk:
                                mock_disk.return_value.percent = 30.0
                                mock_disk.return_value.total = 100 * 1024**3
                                mock_disk.return_value.free = 70 * 1024**3

                                info = await service.get_system_info()

                                assert "os" in info
                                assert "cpu" in info
                                assert "memory" in info
                                assert "disk" in info

    @pytest.mark.asyncio
    async def test_run_network_diagnostics(self):
        """Test running network diagnostics."""
        service = DiagnosticsService()

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"PING success", b"")
            mock_exec.return_value = mock_process

            result = await service.run_network_diagnostics(
                targets=["8.8.8.8", "google.com"]
            )

            assert "ping_results" in result
            assert "dns_resolution" in result

    @pytest.mark.asyncio
    async def test_run_audio_test(self):
        """Test running audio diagnostics."""
        service = DiagnosticsService()

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"card 0: Audio", b"")
            mock_exec.return_value = mock_process

            result = await service.run_audio_test()

            assert "devices" in result
            assert "playback_test" in result
            assert "capture_test" in result

    @pytest.mark.asyncio
    async def test_run_video_test(self):
        """Test running video diagnostics."""
        service = DiagnosticsService()

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"/dev/video0", b"")
            mock_exec.return_value = mock_process

            result = await service.run_video_test()

            assert "devices" in result
            assert "capture_test" in result

    @pytest.mark.asyncio
    async def test_collect_logs(self):
        """Test collecting system logs."""
        service = DiagnosticsService()

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"Log line 1\nLog line 2", b"")
            mock_exec.return_value = mock_process

            result = await service.collect_logs(services=["croom"], lines=100)

            assert "croom" in result
            assert len(result["croom"]) > 0


class TestDeviceControlService:
    """Tests for DeviceControlService class."""

    def test_init(self):
        """Test device control service initialization."""
        service = DeviceControlService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_restart_device(self):
        """Test device restart."""
        service = DeviceControlService()

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await service.restart_device(delay=0)
            assert result is True

    @pytest.mark.asyncio
    async def test_restart_service(self):
        """Test service restart."""
        service = DeviceControlService()

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await service.restart_service("croom")
            assert result is True

    @pytest.mark.asyncio
    async def test_restart_invalid_service(self):
        """Test restart of invalid service."""
        service = DeviceControlService()

        result = await service.restart_service("malicious-service")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing cache."""
        service = DeviceControlService()

        with patch("shutil.rmtree") as mock_rmtree:
            with patch("os.path.exists", return_value=True):
                result = await service.clear_cache()
                assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_update_software(self):
        """Test software update."""
        service = DeviceControlService()

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"Updated", b"")
            mock_exec.return_value = mock_process

            success, message = await service.update_software("croom")
            assert success is True

    @pytest.mark.asyncio
    async def test_update_invalid_package(self):
        """Test update of invalid package."""
        service = DeviceControlService()

        success, message = await service.update_software("malicious-package")
        assert success is False


class TestRemoteOperationsManager:
    """Tests for RemoteOperationsManager class."""

    def test_init(self):
        """Test manager initialization."""
        manager = RemoteOperationsManager()

        assert isinstance(manager.screenshot, ScreenshotService)
        assert isinstance(manager.shell, ShellService)
        assert isinstance(manager.diagnostics, DiagnosticsService)
        assert isinstance(manager.control, DeviceControlService)

    @pytest.mark.asyncio
    async def test_full_diagnostics(self):
        """Test running full diagnostics."""
        manager = RemoteOperationsManager()

        with patch.object(manager.diagnostics, "get_system_info", new_callable=AsyncMock) as mock_sys:
            mock_sys.return_value = {"os": "Linux"}

            with patch.object(manager.diagnostics, "run_network_diagnostics", new_callable=AsyncMock) as mock_net:
                mock_net.return_value = {"ping_results": {}}

                with patch.object(manager.diagnostics, "run_audio_test", new_callable=AsyncMock) as mock_audio:
                    mock_audio.return_value = {"devices": []}

                    with patch.object(manager.diagnostics, "run_video_test", new_callable=AsyncMock) as mock_video:
                        mock_video.return_value = {"devices": []}

                        result = await manager.run_full_diagnostics()

                        assert "system" in result
                        assert "network" in result
                        assert "audio" in result
                        assert "video" in result

    @pytest.mark.asyncio
    async def test_get_health_status(self):
        """Test getting health status."""
        manager = RemoteOperationsManager()

        with patch.object(manager.diagnostics, "get_system_info", new_callable=AsyncMock) as mock_sys:
            mock_sys.return_value = {
                "cpu": {"percent": 25.0},
                "memory": {"percent": 50.0},
                "disk": {"percent": 30.0},
            }

            status = await manager.get_health_status()

            assert "healthy" in status
            assert "cpu_ok" in status
            assert "memory_ok" in status
            assert "disk_ok" in status

    def test_add_allowed_command(self):
        """Test adding allowed command."""
        manager = RemoteOperationsManager()

        manager.add_allowed_command("custom-cmd")
        assert "custom-cmd" in manager.shell._allowed_commands

    def test_remove_allowed_command(self):
        """Test removing allowed command."""
        manager = RemoteOperationsManager()

        manager.add_allowed_command("custom-cmd")
        manager.remove_allowed_command("custom-cmd")
        assert "custom-cmd" not in manager.shell._allowed_commands

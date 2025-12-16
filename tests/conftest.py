"""
Pytest configuration and shared fixtures for Croom tests.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ============================================================================
# Async Event Loop Fixture
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_config_file(temp_dir: Path) -> Path:
    """Create a temporary config file."""
    config_path = temp_dir / "config.yaml"
    config_path.write_text("""
version: 2
platform_type: auto
room:
  name: Test Room
  location: Building A
  timezone: UTC
meeting:
  platforms: [google_meet, teams, zoom]
  default_platform: auto
ai:
  enabled: true
  backend: auto
""")
    return config_path


# ============================================================================
# Mock Hardware Fixtures
# ============================================================================

@pytest.fixture
def mock_gpio():
    """Mock GPIO for testing on non-Pi systems."""
    with patch.dict(sys.modules, {'RPi': MagicMock(), 'RPi.GPIO': MagicMock()}):
        yield


@pytest.fixture
def mock_platform_rpi5():
    """Mock platform detection as Raspberry Pi 5."""
    with patch('croom.platform.detector.PlatformDetector') as mock:
        instance = mock.return_value
        instance.device_type = MagicMock()
        instance.device_type.value = "rpi5"
        instance.architecture = MagicMock()
        instance.architecture.value = "aarch64"
        instance.is_raspberry_pi = True
        instance.has_gpio = True
        instance.has_cec = True
        yield instance


@pytest.fixture
def mock_platform_x86():
    """Mock platform detection as x86_64 PC."""
    with patch('croom.platform.detector.PlatformDetector') as mock:
        instance = mock.return_value
        instance.device_type = MagicMock()
        instance.device_type.value = "pc"
        instance.architecture = MagicMock()
        instance.architecture.value = "amd64"
        instance.is_raspberry_pi = False
        instance.has_gpio = False
        instance.has_cec = False
        instance.has_ddc = True
        yield instance


# ============================================================================
# Mock Network/External Service Fixtures
# ============================================================================

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession for network tests."""
    with patch('aiohttp.ClientSession') as mock:
        session = AsyncMock()
        mock.return_value.__aenter__.return_value = session
        yield session


@pytest.fixture
def mock_playwright():
    """Mock Playwright browser for meeting tests."""
    with patch('playwright.async_api.async_playwright') as mock:
        playwright = AsyncMock()
        browser = AsyncMock()
        page = AsyncMock()

        playwright.chromium.launch.return_value = browser
        browser.new_page.return_value = page
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.click = AsyncMock()

        mock.return_value.__aenter__.return_value = playwright
        yield {"playwright": playwright, "browser": browser, "page": page}


# ============================================================================
# Mock AI Backend Fixtures
# ============================================================================

@pytest.fixture
def mock_onnx_runtime():
    """Mock ONNX Runtime for AI tests."""
    with patch.dict(sys.modules, {'onnxruntime': MagicMock()}):
        yield


@pytest.fixture
def mock_opencv():
    """Mock OpenCV for video processing tests."""
    mock_cv2 = MagicMock()
    mock_cv2.VideoCapture.return_value.isOpened.return_value = True
    mock_cv2.VideoCapture.return_value.read.return_value = (True, MagicMock())
    with patch.dict(sys.modules, {'cv2': mock_cv2}):
        yield mock_cv2


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def sample_config():
    """Return a sample configuration dictionary."""
    return {
        "version": 2,
        "platform_type": "auto",
        "room": {
            "name": "Test Conference Room",
            "location": "Floor 2, Building A",
            "timezone": "America/New_York",
        },
        "meeting": {
            "platforms": ["google_meet", "teams", "zoom", "webex"],
            "default_platform": "auto",
            "join_early_minutes": 2,
            "auto_leave": True,
            "camera_default_on": True,
            "mic_default_on": False,
        },
        "ai": {
            "enabled": True,
            "backend": "auto",
            "person_detection": True,
            "noise_reduction": True,
            "auto_framing": True,
        },
        "dashboard": {
            "enabled": True,
            "url": "https://dashboard.example.com",
            "heartbeat_interval_seconds": 30,
        },
        "security": {
            "require_encryption": True,
            "ssh_enabled": True,
        },
    }


# ============================================================================
# Meeting URL Fixtures
# ============================================================================

@pytest.fixture
def google_meet_url():
    """Return a sample Google Meet URL."""
    return "https://meet.google.com/abc-defg-hij"


@pytest.fixture
def teams_url():
    """Return a sample Microsoft Teams URL."""
    return "https://teams.microsoft.com/l/meetup-join/19%3ameeting_abc123"


@pytest.fixture
def zoom_url():
    """Return a sample Zoom URL."""
    return "https://zoom.us/j/1234567890?pwd=abc123"


@pytest.fixture
def webex_url():
    """Return a sample Webex URL."""
    return "https://example.webex.com/meet/testroom"


# ============================================================================
# Device/Hardware Info Fixtures
# ============================================================================

@pytest.fixture
def sample_device_info():
    """Return sample device information."""
    return {
        "device_id": "croom-test-001",
        "hostname": "croom-room-101",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "ip_address": "192.168.1.100",
        "platform": "rpi5",
        "os_version": "Raspberry Pi OS 12",
        "croom_version": "2.0.0",
        "ai_backend": "hailo",
        "capabilities": {
            "has_ai": True,
            "has_touch": True,
            "has_cec": True,
        },
    }


@pytest.fixture
def sample_camera_info():
    """Return sample camera information."""
    return {
        "device_path": "/dev/video0",
        "name": "Logitech C920",
        "vendor_id": "046d",
        "product_id": "082d",
        "capabilities": ["video_capture", "streaming"],
        "formats": ["YUYV", "MJPG"],
        "resolutions": ["1920x1080", "1280x720", "640x480"],
    }


# ============================================================================
# Async Test Helpers
# ============================================================================

@pytest.fixture
def async_mock():
    """Factory for creating AsyncMock objects."""
    def _create_async_mock(*args, **kwargs):
        return AsyncMock(*args, **kwargs)
    return _create_async_mock


# ============================================================================
# Clean Environment Fixture
# ============================================================================

@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Ensure clean environment for each test."""
    # Remove any Croom-specific env vars that might interfere
    for key in list(os.environ.keys()):
        if key.startswith("CROOM_"):
            monkeypatch.delenv(key, raising=False)

"""
Tests for croom.platform.profiles module.
"""

from unittest.mock import MagicMock, patch

import pytest

from croom.platform.profiles import (
    PerformanceTier,
    AIProfile,
    DisplayProfile,
    AudioProfile,
    VideoProfile,
    HardwareProfile,
    ProfileManager,
    PROFILES,
)
from croom.platform.detector import DeviceType, Architecture


class TestPerformanceTier:
    """Tests for PerformanceTier enum."""

    def test_values(self):
        """Test performance tier values."""
        assert PerformanceTier.MINIMAL.value == "minimal"
        assert PerformanceTier.LOW.value == "low"
        assert PerformanceTier.MEDIUM.value == "medium"
        assert PerformanceTier.HIGH.value == "high"
        assert PerformanceTier.ULTRA.value == "ultra"


class TestAIProfile:
    """Tests for AIProfile dataclass."""

    def test_default_values(self):
        """Test default AI profile values."""
        profile = AIProfile()
        assert profile.preferred_backend == "cpu"
        assert profile.fallback_backends == ["cpu"]
        assert profile.max_inference_fps == 10
        assert profile.batch_size == 1
        assert profile.precision == "fp32"

    def test_custom_values(self):
        """Test custom AI profile."""
        profile = AIProfile(
            preferred_backend="cuda",
            fallback_backends=["tensorrt", "cpu"],
            max_inference_fps=60,
            batch_size=4,
            precision="fp16",
        )
        assert profile.preferred_backend == "cuda"
        assert profile.max_inference_fps == 60
        assert profile.batch_size == 4


class TestDisplayProfile:
    """Tests for DisplayProfile dataclass."""

    def test_default_values(self):
        """Test default display profile values."""
        profile = DisplayProfile()
        assert profile.default_resolution == (1920, 1080)
        assert profile.hdmi_cec_supported is False
        assert profile.ddc_ci_supported is False
        assert profile.touch_supported is False

    def test_custom_values(self):
        """Test custom display profile."""
        profile = DisplayProfile(
            default_resolution=(3840, 2160),
            hdmi_cec_supported=True,
            touch_supported=True,
        )
        assert profile.default_resolution == (3840, 2160)
        assert profile.hdmi_cec_supported is True


class TestAudioProfile:
    """Tests for AudioProfile dataclass."""

    def test_default_values(self):
        """Test default audio profile values."""
        profile = AudioProfile()
        assert profile.preferred_backend == "auto"
        assert profile.sample_rate == 48000
        assert profile.channels == 2
        assert profile.echo_cancellation is True


class TestVideoProfile:
    """Tests for VideoProfile dataclass."""

    def test_default_values(self):
        """Test default video profile values."""
        profile = VideoProfile()
        assert profile.preferred_backend == "auto"
        assert profile.default_resolution == (1920, 1080)
        assert profile.default_fps == 30
        assert profile.auto_exposure is True


class TestHardwareProfile:
    """Tests for HardwareProfile dataclass."""

    def test_creation(self):
        """Test hardware profile creation."""
        profile = HardwareProfile(
            name="Test Profile",
            device_type=DeviceType.PC,
            architecture=Architecture.AMD64,
            performance_tier=PerformanceTier.MEDIUM,
        )
        assert profile.name == "Test Profile"
        assert profile.device_type == DeviceType.PC
        assert profile.architecture == Architecture.AMD64

    def test_predefined_profiles_exist(self):
        """Test predefined profiles are defined."""
        assert len(PROFILES) > 0

    def test_profiles_have_required_fields(self):
        """Test that profiles have required fields."""
        for device_type, profile in PROFILES.items():
            assert isinstance(profile, HardwareProfile)
            assert profile.name
            assert profile.device_type
            assert profile.architecture


class TestProfileManager:
    """Tests for ProfileManager class."""

    def test_manager_creation(self):
        """Test profile manager can be created."""
        manager = ProfileManager()
        assert manager is not None

    def test_initialize(self):
        """Test profile manager initialization."""
        manager = ProfileManager()
        profile = manager.initialize()
        assert isinstance(profile, HardwareProfile)

    def test_profile_property(self):
        """Test getting profile property."""
        manager = ProfileManager()
        profile = manager.profile
        assert isinstance(profile, HardwareProfile)

    def test_get_ai_config(self):
        """Test getting AI config from profile."""
        manager = ProfileManager()
        config = manager.get_ai_config()
        assert "backend" in config
        assert "fallback_backends" in config
        assert "max_fps" in config

    def test_get_display_config(self):
        """Test getting display config from profile."""
        manager = ProfileManager()
        config = manager.get_display_config()
        assert "resolution" in config
        assert "cec_enabled" in config

    def test_get_video_config(self):
        """Test getting video config from profile."""
        manager = ProfileManager()
        config = manager.get_video_config()
        assert "backend" in config
        assert "resolution" in config

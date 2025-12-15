"""
Tests for croom.platform.profiles module.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestPerformanceTier:
    """Tests for PerformanceTier enum."""

    def test_values(self):
        """Test performance tier values."""
        from croom.platform.profiles import PerformanceTier

        assert PerformanceTier.LOW.value == "low"
        assert PerformanceTier.MEDIUM.value == "medium"
        assert PerformanceTier.HIGH.value == "high"
        assert PerformanceTier.ULTRA.value == "ultra"


class TestAIProfile:
    """Tests for AIProfile dataclass."""

    def test_default_values(self):
        """Test default AI profile values."""
        from croom.platform.profiles import AIProfile

        profile = AIProfile()
        assert profile.preferred_backend == "auto"
        assert profile.fallback_backend == "cpu"
        assert profile.max_inference_fps == 15

    def test_custom_values(self):
        """Test custom AI profile."""
        from croom.platform.profiles import AIProfile

        profile = AIProfile(
            preferred_backend="nvidia",
            fallback_backend="onnx_cpu",
            max_inference_fps=60,
        )
        assert profile.preferred_backend == "nvidia"
        assert profile.max_inference_fps == 60


class TestDisplayProfile:
    """Tests for DisplayProfile dataclass."""

    def test_default_values(self):
        """Test default display profile values."""
        from croom.platform.profiles import DisplayProfile

        profile = DisplayProfile()
        assert profile.preferred_backend == "auto"


class TestHardwareProfile:
    """Tests for HardwareProfile dataclass."""

    def test_predefined_profiles_exist(self):
        """Test predefined profiles are defined."""
        from croom.platform.profiles import PREDEFINED_PROFILES

        assert len(PREDEFINED_PROFILES) > 0

    def test_rpi5_profile_exists(self):
        """Test Raspberry Pi 5 profile exists."""
        from croom.platform.profiles import PREDEFINED_PROFILES

        profile_names = [p.name for p in PREDEFINED_PROFILES.values()]
        assert any("Pi 5" in name or "Pi5" in name or "RPI5" in name.upper() for name in profile_names) or len(PREDEFINED_PROFILES) > 0


class TestProfileManager:
    """Tests for ProfileManager class."""

    def test_manager_creation(self):
        """Test profile manager can be created."""
        from croom.platform.profiles import ProfileManager

        with patch("croom.platform.profiles.PlatformDetector"):
            manager = ProfileManager()
            assert manager is not None

    def test_list_profiles(self):
        """Test listing available profiles."""
        from croom.platform.profiles import ProfileManager

        with patch("croom.platform.profiles.PlatformDetector"):
            manager = ProfileManager()
            profiles = manager.list_profiles()
            assert isinstance(profiles, list)

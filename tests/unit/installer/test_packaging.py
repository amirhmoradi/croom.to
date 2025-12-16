"""
Tests for croom.installer.packaging module.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestArchitecture:
    """Tests for Architecture enum."""

    def test_values(self):
        """Test architecture enum values."""
        from croom.installer.packaging import Architecture

        assert Architecture.ARM64.value == "arm64"
        assert Architecture.ARMHF.value == "armhf"
        assert Architecture.AMD64.value == "amd64"


class TestDistribution:
    """Tests for Distribution enum."""

    def test_raspberry_pi_os_values(self):
        """Test Raspberry Pi OS distribution values."""
        from croom.installer.packaging import Distribution

        assert Distribution.BOOKWORM.value == "bookworm"
        assert Distribution.BULLSEYE.value == "bullseye"

    def test_ubuntu_values(self):
        """Test Ubuntu distribution values."""
        from croom.installer.packaging import Distribution

        assert Distribution.JAMMY.value == "jammy"
        assert Distribution.NOBLE.value == "noble"


class TestPackageType:
    """Tests for PackageType enum."""

    def test_values(self):
        """Test package type enum values."""
        from croom.installer.packaging import PackageType

        assert PackageType.CORE.value == "croom-core"
        assert PackageType.UI.value == "croom-ui"
        assert PackageType.AI.value == "croom-ai"
        assert PackageType.FULL.value == "croom"


class TestPackageInfo:
    """Tests for PackageInfo dataclass."""

    def test_basic_package(self):
        """Test basic package info."""
        from croom.installer.packaging import PackageInfo, Architecture

        info = PackageInfo(
            name="croom-core",
            version="2.0.0",
            architecture=Architecture.ARM64,
        )
        assert info.name == "croom-core"
        assert info.version == "2.0.0"
        assert info.architecture == Architecture.ARM64


class TestPackageDefinitions:
    """Tests for package definitions."""

    def test_arm64_definitions_exist(self):
        """Test ARM64 package definitions exist."""
        from croom.installer.packaging import PACKAGE_DEFINITIONS_ARM64, PackageType

        assert PackageType.CORE in PACKAGE_DEFINITIONS_ARM64
        assert PackageType.UI in PACKAGE_DEFINITIONS_ARM64

    def test_amd64_definitions_exist(self):
        """Test AMD64 package definitions exist."""
        from croom.installer.packaging import PACKAGE_DEFINITIONS_AMD64, PackageType

        assert PackageType.CORE in PACKAGE_DEFINITIONS_AMD64

    def test_get_package_definitions_arm64(self):
        """Test getting ARM64 package definitions."""
        from croom.installer.packaging import get_package_definitions, Architecture

        defs = get_package_definitions(Architecture.ARM64)
        assert defs is not None
        assert len(defs) > 0

    def test_get_package_definitions_amd64(self):
        """Test getting AMD64 package definitions."""
        from croom.installer.packaging import get_package_definitions, Architecture

        defs = get_package_definitions(Architecture.AMD64)
        assert defs is not None
        assert len(defs) > 0

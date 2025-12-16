"""
Tests for croom.provisioning module.
"""

import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


class TestEnrollmentState:
    """Tests for EnrollmentState enum."""

    def test_values(self):
        """Test enrollment state enum values."""
        from croom.provisioning.enrollment import EnrollmentState

        assert EnrollmentState.NOT_ENROLLED.value == "not_enrolled"
        assert EnrollmentState.PENDING.value == "pending"
        assert EnrollmentState.ENROLLED.value == "enrolled"


class TestDeviceIdentity:
    """Tests for DeviceIdentity dataclass."""

    def test_creation(self):
        """Test device identity creation."""
        from croom.provisioning.enrollment import DeviceIdentity

        identity = DeviceIdentity(
            device_id="device-123",
            hardware_id="hw-abc",
        )
        assert identity.device_id == "device-123"
        assert identity.hardware_id == "hw-abc"


class TestEnrollmentService:
    """Tests for EnrollmentService class."""

    def test_service_creation(self):
        """Test enrollment service can be created."""
        from croom.provisioning.enrollment import EnrollmentService

        service = EnrollmentService()
        assert service is not None

    def test_initial_state(self):
        """Test initial enrollment state."""
        from croom.provisioning.enrollment import EnrollmentService, EnrollmentState

        service = EnrollmentService()
        assert service.state == EnrollmentState.NOT_ENROLLED

    def test_generate_device_id(self):
        """Test device ID generation."""
        from croom.provisioning.enrollment import EnrollmentService

        service = EnrollmentService()
        device_id = service._generate_device_id()

        assert device_id is not None
        assert len(device_id) > 0

    @pytest.mark.asyncio
    async def test_generate_enrollment_qr(self):
        """Test QR code generation."""
        from croom.provisioning.enrollment import EnrollmentService

        service = EnrollmentService()
        qr_data = service.generate_enrollment_qr(
            dashboard_url="https://dashboard.example.com"
        )

        assert qr_data is not None

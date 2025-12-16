"""
Tests for croom.integrations.vexa module.
"""

from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

import pytest

from croom.integrations.vexa import (
    VexaConfig,
    TranscriptionSegment,
    MeetingSummary,
    VexaClient,
)


class TestVexaConfig:
    """Tests for VexaConfig dataclass."""

    def test_default_values(self):
        """Test default Vexa config values."""
        config = VexaConfig(server_url="ws://localhost:8080/ws/transcribe")
        assert config.server_url == "ws://localhost:8080/ws/transcribe"
        assert config.api_key is None
        assert config.enable_summarization is True

    def test_custom_values(self):
        """Test custom Vexa config values."""
        config = VexaConfig(
            server_url="wss://vexa.example.com/ws/transcribe",
            api_url="https://vexa.example.com/api",
            api_key="secret-key",
            enable_translation=True,
            enable_summarization=False,
        )
        assert config.api_key == "secret-key"
        assert config.enable_summarization is False
        assert config.enable_translation is True

    def test_for_local_deployment(self):
        """Test factory method for local deployment."""
        config = VexaConfig.for_local_deployment()
        assert "localhost" in config.server_url
        assert "8000" in config.server_url


class TestTranscriptionSegment:
    """Tests for TranscriptionSegment dataclass."""

    def test_segment_creation(self):
        """Test transcription segment creation."""
        segment = TranscriptionSegment(
            segment_id="seg-001",
            text="Hello, welcome to the meeting.",
            start_time=0.0,
            end_time=2.5,
            speaker_name="Speaker 1",
            confidence=0.95,
        )
        assert segment.text == "Hello, welcome to the meeting."
        assert segment.start_time == 0.0
        assert segment.speaker_name == "Speaker 1"

    def test_to_dict(self):
        """Test segment to_dict method."""
        segment = TranscriptionSegment(
            segment_id="seg-002",
            text="Test",
            start_time=1.0,
            end_time=3.5,
        )
        data = segment.to_dict()
        assert data["segment_id"] == "seg-002"
        assert data["text"] == "Test"


class TestMeetingSummary:
    """Tests for MeetingSummary dataclass."""

    def test_summary_creation(self):
        """Test meeting summary creation."""
        summary = MeetingSummary(
            summary_id="summary-123",
            title="Project Review",
            summary="This meeting covered project updates and next steps.",
            key_points=["point 1", "point 2"],
            duration=3600.0,
        )
        assert summary.summary_id == "summary-123"
        assert summary.title == "Project Review"
        assert len(summary.key_points) == 2


class TestVexaClient:
    """Tests for VexaClient class."""

    @pytest.fixture
    def vexa_client(self):
        """Create a Vexa client instance."""
        config = VexaConfig(
            server_url="ws://localhost:8080/ws/transcribe",
            api_url="http://localhost:8080/api",
        )
        return VexaClient(config)

    def test_initial_state(self, vexa_client):
        """Test initial client state."""
        # Check connected property
        assert vexa_client._connected is False

    def test_config_property(self, vexa_client):
        """Test config is stored (as _config)."""
        assert vexa_client._config is not None
        assert vexa_client._config.server_url == "ws://localhost:8080/ws/transcribe"

    def test_is_connected_property(self, vexa_client):
        """Test is_connected property."""
        assert vexa_client.is_connected is False


class TestVexaClientConnection:
    """Tests for Vexa client connection."""

    @pytest.fixture
    def vexa_client(self):
        """Create a Vexa client instance."""
        config = VexaConfig(
            server_url="ws://localhost:8080/ws/transcribe",
            api_url="http://localhost:8080/api",
        )
        return VexaClient(config)

    def test_client_creation(self, vexa_client):
        """Test client can be created."""
        assert vexa_client is not None

    def test_config_accessible(self, vexa_client):
        """Test config is accessible via _config."""
        assert vexa_client._config.api_url == "http://localhost:8080/api"


class TestVexaClientTranslation:
    """Tests for Vexa translation features."""

    @pytest.fixture
    def vexa_client(self):
        """Create a Vexa client instance with translation enabled."""
        config = VexaConfig(
            server_url="ws://localhost:8080/ws/transcribe",
            api_url="http://localhost:8080/api",
            enable_translation=True,
        )
        return VexaClient(config)

    def test_translation_enabled(self, vexa_client):
        """Test translation is enabled in config."""
        assert vexa_client._config.enable_translation is True

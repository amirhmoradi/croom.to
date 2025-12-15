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
        config = VexaConfig(
            server_url="http://localhost:8080",
        )
        assert config.server_url == "http://localhost:8080"
        assert config.api_key is None
        assert config.enable_transcription is True
        assert config.enable_summarization is True

    def test_custom_values(self):
        """Test custom Vexa config values."""
        config = VexaConfig(
            server_url="https://vexa.example.com",
            api_key="secret-key",
            enable_transcription=True,
            enable_summarization=False,
            language="fr",
        )
        assert config.api_key == "secret-key"
        assert config.enable_summarization is False
        assert config.language == "fr"


class TestTranscriptionSegment:
    """Tests for TranscriptionSegment dataclass."""

    def test_segment_creation(self):
        """Test transcription segment creation."""
        segment = TranscriptionSegment(
            text="Hello, welcome to the meeting.",
            start_time=0.0,
            end_time=2.5,
            speaker="Speaker 1",
            confidence=0.95,
        )
        assert segment.text == "Hello, welcome to the meeting."
        assert segment.start_time == 0.0
        assert segment.speaker == "Speaker 1"

    def test_segment_duration(self):
        """Test segment duration calculation."""
        segment = TranscriptionSegment(
            text="Test",
            start_time=1.0,
            end_time=3.5,
        )
        assert segment.duration == 2.5


class TestMeetingSummary:
    """Tests for MeetingSummary dataclass."""

    def test_summary_creation(self):
        """Test meeting summary creation."""
        summary = MeetingSummary(
            meeting_id="meeting-123",
            summary_text="This meeting covered project updates and next steps.",
            action_items=["Review proposal", "Schedule follow-up"],
            key_topics=["project updates", "timeline"],
            duration_seconds=3600,
        )
        assert summary.meeting_id == "meeting-123"
        assert len(summary.action_items) == 2
        assert "project updates" in summary.key_topics


class TestVexaClient:
    """Tests for VexaClient class."""

    @pytest.fixture
    def vexa_client(self):
        """Create a Vexa client instance."""
        config = VexaConfig(server_url="http://localhost:8080")
        return VexaClient(config)

    def test_initial_state(self, vexa_client):
        """Test initial client state."""
        assert vexa_client.is_connected is False
        assert vexa_client.is_transcribing is False

    @pytest.mark.asyncio
    async def test_connect(self, vexa_client):
        """Test connecting to Vexa server."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_ws = AsyncMock()
            mock_session.return_value.__aenter__.return_value.ws_connect.return_value.__aenter__.return_value = mock_ws

            result = await vexa_client.connect()

            assert result is True

    @pytest.mark.asyncio
    async def test_disconnect(self, vexa_client):
        """Test disconnecting from Vexa server."""
        vexa_client._connected = True
        vexa_client._websocket = AsyncMock()

        await vexa_client.disconnect()

        assert vexa_client.is_connected is False

    @pytest.mark.asyncio
    async def test_start_transcription(self, vexa_client):
        """Test starting transcription."""
        vexa_client._connected = True
        vexa_client._websocket = AsyncMock()

        result = await vexa_client.start_transcription(meeting_id="meeting-123")

        assert result is True
        assert vexa_client.is_transcribing is True

    @pytest.mark.asyncio
    async def test_stop_transcription(self, vexa_client):
        """Test stopping transcription."""
        vexa_client._connected = True
        vexa_client._transcribing = True
        vexa_client._websocket = AsyncMock()

        result = await vexa_client.stop_transcription()

        assert result is True
        assert vexa_client.is_transcribing is False

    @pytest.mark.asyncio
    async def test_send_audio(self, vexa_client):
        """Test sending audio data for transcription."""
        vexa_client._connected = True
        vexa_client._transcribing = True
        vexa_client._websocket = AsyncMock()

        audio_data = bytes([0] * 1024)  # Dummy audio
        result = await vexa_client.send_audio(audio_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_get_summary(self, vexa_client):
        """Test getting meeting summary."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "meeting_id": "meeting-123",
                    "summary": "Meeting summary text",
                    "action_items": ["Action 1", "Action 2"],
                    "key_topics": ["Topic 1"],
                }
            )
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

            summary = await vexa_client.get_summary("meeting-123")

            assert summary is not None
            assert summary.meeting_id == "meeting-123"

    def test_register_transcription_callback(self, vexa_client):
        """Test registering transcription callback."""
        callback = MagicMock()
        vexa_client.on_transcription(callback)

        assert callback in vexa_client._transcription_callbacks

    def test_get_transcription_history(self, vexa_client):
        """Test getting transcription history."""
        vexa_client._segments = [
            TranscriptionSegment("Hello", 0.0, 1.0),
            TranscriptionSegment("World", 1.0, 2.0),
        ]

        history = vexa_client.get_transcription_history()

        assert len(history) == 2
        assert history[0].text == "Hello"


class TestVexaClientHealthCheck:
    """Tests for Vexa client health check."""

    @pytest.fixture
    def vexa_client(self):
        """Create a Vexa client instance."""
        config = VexaConfig(server_url="http://localhost:8080")
        return VexaClient(config)

    @pytest.mark.asyncio
    async def test_health_check_success(self, vexa_client):
        """Test successful health check."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

            is_healthy = await vexa_client.health_check()

            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, vexa_client):
        """Test failed health check."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = Exception("Connection error")

            is_healthy = await vexa_client.health_check()

            assert is_healthy is False


class TestVexaClientTranslation:
    """Tests for Vexa translation features."""

    @pytest.fixture
    def vexa_client(self):
        """Create a Vexa client instance."""
        config = VexaConfig(
            server_url="http://localhost:8080",
            enable_translation=True,
        )
        return VexaClient(config)

    @pytest.mark.asyncio
    async def test_enable_translation(self, vexa_client):
        """Test enabling real-time translation."""
        vexa_client._connected = True
        vexa_client._websocket = AsyncMock()

        result = await vexa_client.enable_translation(
            source_language="en",
            target_language="fr",
        )

        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_disable_translation(self, vexa_client):
        """Test disabling translation."""
        vexa_client._connected = True
        vexa_client._translating = True
        vexa_client._websocket = AsyncMock()

        result = await vexa_client.disable_translation()

        assert isinstance(result, bool)

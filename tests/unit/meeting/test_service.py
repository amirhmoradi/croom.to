"""
Tests for croom.meeting.service module.
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

import pytest

from croom.meeting.providers.base import MeetingState, MeetingInfo
from croom.meeting.service import MeetingService


class TestMeetingState:
    """Tests for MeetingState enum."""

    def test_values(self):
        """Test meeting state enum values."""
        assert MeetingState.IDLE.value == "idle"
        assert MeetingState.JOINING.value == "joining"
        assert MeetingState.IN_LOBBY.value == "in_lobby"
        assert MeetingState.CONNECTED.value == "connected"
        assert MeetingState.LEAVING.value == "leaving"
        assert MeetingState.ERROR.value == "error"


class TestMeetingInfo:
    """Tests for MeetingInfo dataclass."""

    def test_default_values(self):
        """Test default meeting info values."""
        info = MeetingInfo(
            meeting_id="abc-defg-hij",
            platform="google_meet",
            meeting_url="https://meet.google.com/abc-defg-hij",
        )
        assert info.meeting_id == "abc-defg-hij"
        assert info.platform == "google_meet"
        assert info.title == ""
        assert info.start_time is None
        assert info.state == MeetingState.IDLE

    def test_with_schedule(self):
        """Test meeting info with scheduled time."""
        start_time = datetime.now() + timedelta(hours=1)
        info = MeetingInfo(
            meeting_id="123",
            platform="teams",
            meeting_url="https://teams.microsoft.com/...",
            title="Team Standup",
            start_time=start_time,
            end_time=start_time + timedelta(hours=1),
        )
        assert info.title == "Team Standup"
        assert info.start_time == start_time

    def test_to_dict(self):
        """Test converting meeting info to dict."""
        info = MeetingInfo(
            meeting_id="test-123",
            platform="zoom",
            meeting_url="https://zoom.us/j/test-123",
        )
        result = info.to_dict()
        assert "meeting_id" in result
        assert "platform" in result
        assert "meeting_url" in result


class TestMeetingServiceBasic:
    """Tests for MeetingService class basic functionality."""

    def test_service_creation(self):
        """Test meeting service can be created."""
        mock_config = MagicMock()
        mock_config.meeting.platforms = []
        service = MeetingService(mock_config)
        assert service is not None
        assert service.name == "meeting"

    def test_service_has_providers_dict(self):
        """Test service has providers dictionary."""
        mock_config = MagicMock()
        mock_config.meeting.platforms = []
        service = MeetingService(mock_config)
        assert hasattr(service, "_providers")
        assert isinstance(service._providers, dict)


class TestMeetingPlatformDetection:
    """Tests for meeting platform detection."""

    def test_detect_google_meet(self):
        """Test detection of Google Meet URL."""
        from croom.meeting.providers.base import detect_platform

        url = "https://meet.google.com/abc-defg-hij"
        platform = detect_platform(url)
        assert platform == "google_meet"

    def test_detect_teams(self):
        """Test detection of Microsoft Teams URL."""
        from croom.meeting.providers.base import detect_platform

        url = "https://teams.microsoft.com/l/meetup-join/123"
        platform = detect_platform(url)
        assert platform == "teams"

    def test_detect_zoom(self):
        """Test detection of Zoom URL."""
        from croom.meeting.providers.base import detect_platform

        url = "https://zoom.us/j/123456789"
        platform = detect_platform(url)
        assert platform == "zoom"

    def test_detect_webex(self):
        """Test detection of Webex URL."""
        from croom.meeting.providers.base import detect_platform

        url = "https://company.webex.com/meet/username"
        platform = detect_platform(url)
        assert platform == "webex"

    def test_detect_unknown(self):
        """Test detection of unknown URL."""
        from croom.meeting.providers.base import detect_platform

        url = "https://unknown-meeting.com/join"
        platform = detect_platform(url)
        assert platform is None or platform == "unknown"


class TestMeetingProviders:
    """Tests for meeting providers."""

    def test_get_all_providers(self):
        """Test getting all provider types."""
        from croom.meeting.providers import get_all_providers

        providers = get_all_providers()
        assert isinstance(providers, dict)

    def test_get_provider(self):
        """Test getting a specific provider class."""
        from croom.meeting.providers import get_provider

        # Try to get Google Meet provider
        provider_cls = get_provider("google_meet")
        # May return None if not configured, just verify no exception
        assert provider_cls is None or callable(provider_cls)

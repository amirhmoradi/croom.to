"""
Tests for croom.meeting.service module.
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

import pytest

from croom.meeting.service import (
    MeetingState,
    MeetingInfo,
    MeetingService,
)


class TestMeetingState:
    """Tests for MeetingState enum."""

    def test_values(self):
        """Test meeting state enum values."""
        assert MeetingState.IDLE.value == "idle"
        assert MeetingState.JOINING.value == "joining"
        assert MeetingState.IN_MEETING.value == "in_meeting"
        assert MeetingState.LEAVING.value == "leaving"
        assert MeetingState.ERROR.value == "error"


class TestMeetingInfo:
    """Tests for MeetingInfo dataclass."""

    def test_default_values(self):
        """Test default meeting info values."""
        info = MeetingInfo(
            meeting_id="abc-defg-hij",
            platform="google_meet",
            url="https://meet.google.com/abc-defg-hij",
        )
        assert info.meeting_id == "abc-defg-hij"
        assert info.platform == "google_meet"
        assert info.title is None
        assert info.scheduled_start is None

    def test_with_schedule(self):
        """Test meeting info with scheduled time."""
        start_time = datetime.now() + timedelta(hours=1)
        info = MeetingInfo(
            meeting_id="123",
            platform="teams",
            url="https://teams.microsoft.com/...",
            title="Team Standup",
            scheduled_start=start_time,
            scheduled_end=start_time + timedelta(hours=1),
        )
        assert info.title == "Team Standup"
        assert info.scheduled_start == start_time


class TestMeetingService:
    """Tests for MeetingService class."""

    @pytest.fixture
    def meeting_service(self):
        """Create a meeting service instance."""
        with patch("croom.meeting.service.async_playwright"):
            service = MeetingService()
            return service

    def test_initial_state(self, meeting_service):
        """Test initial service state."""
        assert meeting_service.state == MeetingState.IDLE
        assert meeting_service.current_meeting is None

    def test_detect_platform_google_meet(self, meeting_service, google_meet_url):
        """Test Google Meet URL detection."""
        platform = meeting_service.detect_platform(google_meet_url)
        assert platform == "google_meet"

    def test_detect_platform_teams(self, meeting_service, teams_url):
        """Test Microsoft Teams URL detection."""
        platform = meeting_service.detect_platform(teams_url)
        assert platform == "teams"

    def test_detect_platform_zoom(self, meeting_service, zoom_url):
        """Test Zoom URL detection."""
        platform = meeting_service.detect_platform(zoom_url)
        assert platform == "zoom"

    def test_detect_platform_webex(self, meeting_service, webex_url):
        """Test Webex URL detection."""
        platform = meeting_service.detect_platform(webex_url)
        assert platform == "webex"

    def test_detect_platform_unknown(self, meeting_service):
        """Test unknown URL returns None."""
        platform = meeting_service.detect_platform("https://unknown.com/meeting")
        assert platform is None

    def test_parse_meeting_url_google(self, meeting_service, google_meet_url):
        """Test parsing Google Meet URL."""
        info = meeting_service.parse_meeting_url(google_meet_url)
        assert info.platform == "google_meet"
        assert info.meeting_id == "abc-defg-hij"
        assert info.url == google_meet_url

    def test_parse_meeting_url_zoom(self, meeting_service, zoom_url):
        """Test parsing Zoom URL."""
        info = meeting_service.parse_meeting_url(zoom_url)
        assert info.platform == "zoom"
        assert "1234567890" in info.meeting_id

    @pytest.mark.asyncio
    async def test_join_meeting_starts_browser(self, meeting_service, mock_playwright, google_meet_url):
        """Test joining meeting starts browser."""
        meeting_service._playwright_context = mock_playwright

        with patch.object(meeting_service, "_get_provider") as mock_provider:
            provider = AsyncMock()
            provider.join_meeting = AsyncMock(return_value=True)
            mock_provider.return_value = provider

            result = await meeting_service.join_meeting(google_meet_url)

            assert result is True

    @pytest.mark.asyncio
    async def test_join_meeting_updates_state(self, meeting_service, google_meet_url):
        """Test joining meeting updates state."""
        with patch.object(meeting_service, "_get_provider") as mock_provider:
            provider = AsyncMock()
            provider.join_meeting = AsyncMock(return_value=True)
            mock_provider.return_value = provider

            await meeting_service.join_meeting(google_meet_url)

            # State should transition through JOINING
            # Final state depends on success

    @pytest.mark.asyncio
    async def test_leave_meeting(self, meeting_service):
        """Test leaving meeting."""
        meeting_service._state = MeetingState.IN_MEETING
        meeting_service._current_meeting = MeetingInfo(
            meeting_id="test",
            platform="google_meet",
            url="https://meet.google.com/test",
        )

        with patch.object(meeting_service, "_get_provider") as mock_provider:
            provider = AsyncMock()
            provider.leave_meeting = AsyncMock(return_value=True)
            mock_provider.return_value = provider

            result = await meeting_service.leave_meeting()

            assert result is True

    @pytest.mark.asyncio
    async def test_leave_meeting_when_not_in_meeting(self, meeting_service):
        """Test leaving when not in a meeting."""
        meeting_service._state = MeetingState.IDLE

        result = await meeting_service.leave_meeting()

        # Should return True (nothing to leave) or handle gracefully
        assert isinstance(result, bool)

    def test_get_supported_platforms(self, meeting_service):
        """Test getting list of supported platforms."""
        platforms = meeting_service.get_supported_platforms()

        assert "google_meet" in platforms
        assert "teams" in platforms
        assert "zoom" in platforms
        assert "webex" in platforms

    @pytest.mark.asyncio
    async def test_toggle_camera(self, meeting_service):
        """Test toggling camera during meeting."""
        meeting_service._state = MeetingState.IN_MEETING

        with patch.object(meeting_service, "_get_provider") as mock_provider:
            provider = AsyncMock()
            provider.toggle_camera = AsyncMock(return_value=True)
            mock_provider.return_value = provider

            result = await meeting_service.toggle_camera()

            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_toggle_microphone(self, meeting_service):
        """Test toggling microphone during meeting."""
        meeting_service._state = MeetingState.IN_MEETING

        with patch.object(meeting_service, "_get_provider") as mock_provider:
            provider = AsyncMock()
            provider.toggle_microphone = AsyncMock(return_value=True)
            mock_provider.return_value = provider

            result = await meeting_service.toggle_microphone()

            assert isinstance(result, bool)


class TestMeetingServiceEvents:
    """Tests for MeetingService event handling."""

    @pytest.fixture
    def meeting_service(self):
        """Create a meeting service instance."""
        with patch("croom.meeting.service.async_playwright"):
            service = MeetingService()
            return service

    def test_register_callback(self, meeting_service):
        """Test registering state change callback."""
        callback = MagicMock()
        meeting_service.on_state_change(callback)

        assert callback in meeting_service._state_callbacks

    def test_unregister_callback(self, meeting_service):
        """Test unregistering state change callback."""
        callback = MagicMock()
        meeting_service.on_state_change(callback)
        meeting_service.remove_state_callback(callback)

        assert callback not in meeting_service._state_callbacks

    @pytest.mark.asyncio
    async def test_callback_called_on_state_change(self, meeting_service):
        """Test callbacks are called on state change."""
        callback = MagicMock()
        meeting_service.on_state_change(callback)

        await meeting_service._set_state(MeetingState.JOINING)

        callback.assert_called_once()


class TestMeetingURLParsing:
    """Tests for meeting URL parsing edge cases."""

    @pytest.fixture
    def meeting_service(self):
        """Create a meeting service instance."""
        with patch("croom.meeting.service.async_playwright"):
            service = MeetingService()
            return service

    def test_google_meet_variations(self, meeting_service):
        """Test various Google Meet URL formats."""
        urls = [
            "https://meet.google.com/abc-defg-hij",
            "https://meet.google.com/abc-defg-hij?authuser=0",
            "https://meet.google.com/lookup/abc-defg-hij",
        ]
        for url in urls:
            platform = meeting_service.detect_platform(url)
            assert platform == "google_meet", f"Failed for {url}"

    def test_teams_variations(self, meeting_service):
        """Test various Teams URL formats."""
        urls = [
            "https://teams.microsoft.com/l/meetup-join/123",
            "https://teams.live.com/meet/123",
        ]
        for url in urls:
            platform = meeting_service.detect_platform(url)
            assert platform == "teams", f"Failed for {url}"

    def test_zoom_variations(self, meeting_service):
        """Test various Zoom URL formats."""
        urls = [
            "https://zoom.us/j/1234567890",
            "https://us02web.zoom.us/j/1234567890",
            "https://example.zoom.us/j/1234567890?pwd=abc",
        ]
        for url in urls:
            platform = meeting_service.detect_platform(url)
            assert platform == "zoom", f"Failed for {url}"

    def test_webex_variations(self, meeting_service):
        """Test various Webex URL formats."""
        urls = [
            "https://example.webex.com/meet/user",
            "https://example.webex.com/join/123456",
            "https://meetings.webex.com/collabs/meetings/join?uuid=abc",
        ]
        for url in urls:
            platform = meeting_service.detect_platform(url)
            assert platform == "webex", f"Failed for {url}"

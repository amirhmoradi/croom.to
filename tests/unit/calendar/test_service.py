"""
Tests for croom.calendar.service module.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from croom.calendar.service import (
    CalendarEvent,
    CalendarService,
)


class TestCalendarEvent:
    """Tests for CalendarEvent dataclass."""

    def test_basic_event(self):
        """Test basic calendar event creation."""
        start = datetime.now() + timedelta(hours=1)
        end = start + timedelta(hours=1)

        event = CalendarEvent(
            event_id="event-123",
            title="Team Meeting",
            start_time=start,
            end_time=end,
        )

        assert event.event_id == "event-123"
        assert event.title == "Team Meeting"
        assert event.meeting_url is None

    def test_event_with_meeting(self):
        """Test calendar event with meeting URL."""
        start = datetime.now() + timedelta(hours=1)
        end = start + timedelta(hours=1)

        event = CalendarEvent(
            event_id="event-123",
            title="Video Call",
            start_time=start,
            end_time=end,
            meeting_url="https://meet.google.com/abc-defg-hij",
            meeting_platform="google_meet",
        )

        assert event.meeting_url == "https://meet.google.com/abc-defg-hij"
        assert event.meeting_platform == "google_meet"

    def test_event_is_happening_now(self):
        """Test checking if event is currently happening."""
        start = datetime.now() - timedelta(minutes=30)
        end = datetime.now() + timedelta(minutes=30)

        event = CalendarEvent(
            event_id="event-123",
            title="Current Meeting",
            start_time=start,
            end_time=end,
        )

        assert event.is_happening_now() is True

    def test_event_not_happening_now(self):
        """Test checking if future event is not happening."""
        start = datetime.now() + timedelta(hours=2)
        end = start + timedelta(hours=1)

        event = CalendarEvent(
            event_id="event-123",
            title="Future Meeting",
            start_time=start,
            end_time=end,
        )

        assert event.is_happening_now() is False

    def test_event_time_until_start(self):
        """Test calculating time until event starts."""
        start = datetime.now() + timedelta(minutes=30)
        end = start + timedelta(hours=1)

        event = CalendarEvent(
            event_id="event-123",
            title="Soon Meeting",
            start_time=start,
            end_time=end,
        )

        time_until = event.time_until_start()
        assert time_until.total_seconds() > 0
        assert time_until.total_seconds() < 1900  # ~31 minutes


class TestCalendarService:
    """Tests for CalendarService class."""

    @pytest.fixture
    def calendar_service(self):
        """Create a calendar service instance."""
        return CalendarService()

    def test_initial_state(self, calendar_service):
        """Test initial calendar service state."""
        assert len(calendar_service._events) == 0
        assert len(calendar_service._providers) == 0

    @pytest.mark.asyncio
    async def test_add_provider(self, calendar_service):
        """Test adding calendar provider."""
        mock_provider = MagicMock()
        mock_provider.name = "google"

        await calendar_service.add_provider(mock_provider)

        assert "google" in calendar_service._providers

    @pytest.mark.asyncio
    async def test_remove_provider(self, calendar_service):
        """Test removing calendar provider."""
        mock_provider = MagicMock()
        mock_provider.name = "google"

        await calendar_service.add_provider(mock_provider)
        await calendar_service.remove_provider("google")

        assert "google" not in calendar_service._providers

    @pytest.mark.asyncio
    async def test_sync_events(self, calendar_service):
        """Test syncing events from providers."""
        mock_provider = MagicMock()
        mock_provider.name = "google"
        mock_provider.fetch_events = AsyncMock(
            return_value=[
                CalendarEvent(
                    event_id="event-1",
                    title="Meeting 1",
                    start_time=datetime.now(),
                    end_time=datetime.now() + timedelta(hours=1),
                ),
            ]
        )

        await calendar_service.add_provider(mock_provider)
        await calendar_service.sync_events()

        assert len(calendar_service._events) > 0

    def test_get_upcoming_events(self, calendar_service):
        """Test getting upcoming events."""
        now = datetime.now()
        calendar_service._events = [
            CalendarEvent("e1", "Past", now - timedelta(hours=2), now - timedelta(hours=1)),
            CalendarEvent("e2", "Soon", now + timedelta(minutes=30), now + timedelta(hours=1)),
            CalendarEvent("e3", "Later", now + timedelta(hours=3), now + timedelta(hours=4)),
        ]

        upcoming = calendar_service.get_upcoming_events(hours=2)

        assert len(upcoming) == 1
        assert upcoming[0].title == "Soon"

    def test_get_next_meeting(self, calendar_service):
        """Test getting next meeting with URL."""
        now = datetime.now()
        calendar_service._events = [
            CalendarEvent("e1", "No URL", now + timedelta(minutes=10), now + timedelta(hours=1)),
            CalendarEvent(
                "e2",
                "With URL",
                now + timedelta(minutes=30),
                now + timedelta(hours=1),
                meeting_url="https://meet.google.com/abc",
            ),
        ]

        next_meeting = calendar_service.get_next_meeting()

        assert next_meeting is not None
        assert next_meeting.title == "With URL"
        assert next_meeting.meeting_url is not None

    def test_get_events_for_day(self, calendar_service):
        """Test getting events for a specific day."""
        target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        calendar_service._events = [
            CalendarEvent(
                "e1",
                "Today",
                target_date + timedelta(hours=10),
                target_date + timedelta(hours=11),
            ),
            CalendarEvent(
                "e2",
                "Tomorrow",
                target_date + timedelta(days=1, hours=10),
                target_date + timedelta(days=1, hours=11),
            ),
        ]

        today_events = calendar_service.get_events_for_day(target_date)

        assert len(today_events) == 1
        assert today_events[0].title == "Today"

    def test_find_event_by_id(self, calendar_service):
        """Test finding event by ID."""
        calendar_service._events = [
            CalendarEvent("e1", "Event 1", datetime.now(), datetime.now() + timedelta(hours=1)),
            CalendarEvent("e2", "Event 2", datetime.now(), datetime.now() + timedelta(hours=1)),
        ]

        event = calendar_service.find_event("e2")

        assert event is not None
        assert event.title == "Event 2"

    def test_find_nonexistent_event(self, calendar_service):
        """Test finding non-existent event returns None."""
        event = calendar_service.find_event("nonexistent")
        assert event is None


class TestCalendarServiceAutoJoin:
    """Tests for calendar auto-join functionality."""

    @pytest.fixture
    def calendar_service(self):
        """Create a calendar service instance."""
        return CalendarService()

    @pytest.mark.asyncio
    async def test_start_auto_join_monitor(self, calendar_service):
        """Test starting auto-join monitor."""
        with patch("asyncio.create_task") as mock_task:
            await calendar_service.start_auto_join_monitor()
            # Should create monitoring task

    @pytest.mark.asyncio
    async def test_stop_auto_join_monitor(self, calendar_service):
        """Test stopping auto-join monitor."""
        calendar_service._auto_join_task = AsyncMock()
        calendar_service._auto_join_task.cancel = MagicMock()

        await calendar_service.stop_auto_join_monitor()
        # Should cancel monitoring task

    def test_should_auto_join(self, calendar_service):
        """Test determining if should auto-join meeting."""
        now = datetime.now()
        event = CalendarEvent(
            "e1",
            "Meeting",
            now + timedelta(minutes=1),  # Starts in 1 minute
            now + timedelta(hours=1),
            meeting_url="https://meet.google.com/abc",
        )

        # Within join window
        should_join = calendar_service.should_auto_join(event, join_early_minutes=2)
        assert should_join is True

    def test_should_not_auto_join_too_early(self, calendar_service):
        """Test should not auto-join if too early."""
        now = datetime.now()
        event = CalendarEvent(
            "e1",
            "Meeting",
            now + timedelta(minutes=30),  # Starts in 30 minutes
            now + timedelta(hours=1),
            meeting_url="https://meet.google.com/abc",
        )

        should_join = calendar_service.should_auto_join(event, join_early_minutes=2)
        assert should_join is False

    def test_should_not_auto_join_no_url(self, calendar_service):
        """Test should not auto-join if no meeting URL."""
        now = datetime.now()
        event = CalendarEvent(
            "e1",
            "Meeting",
            now + timedelta(minutes=1),
            now + timedelta(hours=1),
            # No meeting_url
        )

        should_join = calendar_service.should_auto_join(event, join_early_minutes=2)
        assert should_join is False

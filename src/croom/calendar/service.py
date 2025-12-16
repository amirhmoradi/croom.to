"""
Calendar Service for Croom.

Manages calendar providers and coordinates event polling.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable, Set

from croom.calendar.providers.base import (
    CalendarProvider,
    CalendarEvent,
    MeetingPlatform,
)
from croom.calendar.providers.google import GoogleCalendarProvider
from croom.calendar.providers.microsoft import MicrosoftCalendarProvider

logger = logging.getLogger(__name__)


class CalendarService:
    """
    High-level calendar service for Croom.

    Manages multiple calendar providers, polls for events,
    and notifies about upcoming meetings.
    """

    # Provider classes by name
    PROVIDERS = {
        'google': GoogleCalendarProvider,
        'microsoft': MicrosoftCalendarProvider,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize calendar service.

        Args:
            config: Service configuration with:
                - provider: Calendar provider name ('google', 'microsoft')
                - credentials: Provider-specific credentials
                - calendar_ids: List of calendar IDs to monitor
                - poll_interval: How often to check for events (seconds)
                - auto_join_minutes: Minutes before meeting to trigger auto-join
        """
        self.config = config or {}
        self._provider: Optional[CalendarProvider] = None
        self._calendar_ids: List[str] = []
        self._poll_interval = self.config.get('poll_interval', 60)
        self._auto_join_minutes = self.config.get('auto_join_minutes', 1)

        # Event cache
        self._events: Dict[str, CalendarEvent] = {}
        self._next_meeting: Optional[CalendarEvent] = None

        # Callbacks
        self._on_meeting_starting: List[Callable[[CalendarEvent], None]] = []
        self._on_events_updated: List[Callable[[List[CalendarEvent]], None]] = []

        # Polling task
        self._poll_task: Optional[asyncio.Task] = None
        self._running = False

        # Track notified meetings to avoid duplicate notifications
        self._notified_meetings: Set[str] = set()

    @property
    def provider(self) -> Optional[CalendarProvider]:
        """Get the current calendar provider."""
        return self._provider

    @property
    def next_meeting(self) -> Optional[CalendarEvent]:
        """Get the next upcoming meeting."""
        return self._next_meeting

    @property
    def events(self) -> List[CalendarEvent]:
        """Get all cached events sorted by start time."""
        return sorted(
            self._events.values(),
            key=lambda e: e.start_time
        )

    async def initialize(self) -> bool:
        """
        Initialize the calendar service.

        Creates and authenticates the calendar provider.

        Returns:
            True if initialization successful
        """
        provider_name = self.config.get('provider', 'google')
        credentials = self.config.get('credentials', {})
        calendar_ids = self.config.get('calendar_ids', [])

        if provider_name not in self.PROVIDERS:
            logger.error(f"Unknown calendar provider: {provider_name}")
            return False

        try:
            # Create provider
            provider_class = self.PROVIDERS[provider_name]
            self._provider = provider_class()

            # Authenticate
            if not await self._provider.authenticate(credentials):
                logger.error(f"Failed to authenticate with {provider_name}")
                return False

            # Set calendar IDs or discover primary
            if calendar_ids:
                self._calendar_ids = calendar_ids
            else:
                # Try to get primary calendar
                calendars = await self._provider.get_calendars()
                primary = next(
                    (c for c in calendars if c.get('primary')),
                    calendars[0] if calendars else None
                )
                if primary:
                    self._calendar_ids = [primary['id']]
                    logger.info(f"Using primary calendar: {primary.get('name', primary['id'])}")
                else:
                    logger.warning("No calendars found")
                    self._calendar_ids = []

            logger.info(f"Calendar service initialized with {provider_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize calendar service: {e}")
            return False

    async def start(self) -> None:
        """Start the calendar polling loop."""
        if self._running:
            return

        self._running = True

        # Initial fetch
        await self._fetch_events()

        # Start polling
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info(f"Calendar polling started (interval: {self._poll_interval}s)")

    async def stop(self) -> None:
        """Stop the calendar polling loop."""
        self._running = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        logger.info("Calendar polling stopped")

    async def _poll_loop(self) -> None:
        """Background polling loop."""
        while self._running:
            try:
                await asyncio.sleep(self._poll_interval)
                await self._fetch_events()
                self._check_upcoming_meetings()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Calendar poll error: {e}")

    async def _fetch_events(self) -> None:
        """Fetch events from all calendars."""
        if not self._provider or not self._calendar_ids:
            return

        try:
            now = datetime.now(timezone.utc)
            time_min = now - timedelta(hours=1)  # Include recent past
            time_max = now + timedelta(days=7)   # One week ahead

            all_events: Dict[str, CalendarEvent] = {}

            for calendar_id in self._calendar_ids:
                events = await self._provider.get_events(
                    calendar_id=calendar_id,
                    time_min=time_min,
                    time_max=time_max,
                )

                for event in events:
                    # Skip cancelled events
                    if event.status == 'cancelled':
                        continue
                    all_events[event.id] = event

            self._events = all_events

            # Update next meeting
            self._update_next_meeting()

            # Notify listeners
            for callback in self._on_events_updated:
                try:
                    callback(self.events)
                except Exception as e:
                    logger.error(f"Events callback error: {e}")

            logger.debug(f"Fetched {len(all_events)} calendar events")

        except Exception as e:
            logger.error(f"Failed to fetch calendar events: {e}")

    def _update_next_meeting(self) -> None:
        """Update the next meeting reference."""
        now = datetime.now(timezone.utc)

        # Find next meeting with a video conference link
        upcoming = [
            e for e in self._events.values()
            if e.meeting_url and e.end_time > now
        ]

        if upcoming:
            # Sort by start time
            upcoming.sort(key=lambda e: e.start_time)
            self._next_meeting = upcoming[0]
        else:
            self._next_meeting = None

    def _check_upcoming_meetings(self) -> None:
        """Check for meetings starting soon and trigger notifications."""
        now = datetime.now(timezone.utc)

        for event in self._events.values():
            # Skip if no meeting URL
            if not event.meeting_url:
                continue

            # Skip if already notified
            if event.id in self._notified_meetings:
                continue

            # Skip if meeting already ended
            if event.end_time <= now:
                continue

            # Check if meeting is starting soon
            if event.is_starting_soon(minutes=self._auto_join_minutes):
                self._notified_meetings.add(event.id)

                logger.info(f"Meeting starting soon: {event.title}")

                # Notify listeners
                for callback in self._on_meeting_starting:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Meeting callback error: {e}")

        # Clean up old notifications
        self._cleanup_notified()

    def _cleanup_notified(self) -> None:
        """Remove old meeting IDs from notified set."""
        now = datetime.now(timezone.utc)

        to_remove = set()
        for event_id in self._notified_meetings:
            if event_id not in self._events:
                to_remove.add(event_id)
            elif self._events[event_id].end_time < now - timedelta(hours=1):
                to_remove.add(event_id)

        self._notified_meetings -= to_remove

    def on_meeting_starting(self, callback: Callable[[CalendarEvent], None]) -> None:
        """
        Register callback for when a meeting is about to start.

        Args:
            callback: Function taking CalendarEvent, called when meeting starts soon
        """
        self._on_meeting_starting.append(callback)

    def on_events_updated(self, callback: Callable[[List[CalendarEvent]], None]) -> None:
        """
        Register callback for when events are updated.

        Args:
            callback: Function taking list of CalendarEvents
        """
        self._on_events_updated.append(callback)

    async def get_today_events(self) -> List[CalendarEvent]:
        """
        Get all events for today.

        Returns:
            List of today's calendar events
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        return [
            e for e in self._events.values()
            if e.start_time >= today_start and e.start_time < today_end
        ]

    async def get_meetings_in_range(
        self,
        start: datetime,
        end: datetime,
        with_url_only: bool = True
    ) -> List[CalendarEvent]:
        """
        Get meetings in a time range.

        Args:
            start: Start of range
            end: End of range
            with_url_only: Only return events with meeting URLs

        Returns:
            List of calendar events in range
        """
        events = []

        for event in self._events.values():
            # Check time range
            if event.start_time >= end or event.end_time <= start:
                continue

            # Check URL filter
            if with_url_only and not event.meeting_url:
                continue

            events.append(event)

        return sorted(events, key=lambda e: e.start_time)

    async def refresh(self) -> None:
        """Force refresh of calendar events."""
        await self._fetch_events()
        logger.info("Calendar events refreshed")

    def get_event_by_id(self, event_id: str) -> Optional[CalendarEvent]:
        """Get a specific event by ID."""
        return self._events.get(event_id)

    def get_current_meeting(self) -> Optional[CalendarEvent]:
        """
        Get the meeting happening right now.

        Returns:
            Current meeting or None if no meeting is active
        """
        for event in self._events.values():
            if event.is_happening_now() and event.meeting_url:
                return event
        return None

    async def shutdown(self) -> None:
        """Shutdown the calendar service."""
        await self.stop()
        self._provider = None
        self._events.clear()
        self._notified_meetings.clear()
        logger.info("Calendar service shutdown")


# Factory function
def create_calendar_service(config: Dict[str, Any]) -> CalendarService:
    """
    Create a calendar service from configuration.

    Args:
        config: Calendar configuration dict

    Returns:
        Configured CalendarService instance
    """
    return CalendarService(config)

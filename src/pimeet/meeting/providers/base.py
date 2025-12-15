"""
Abstract base class for meeting providers.

All meeting platform providers must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
import re


class MeetingState(Enum):
    """Meeting lifecycle states."""
    IDLE = "idle"
    JOINING = "joining"
    IN_LOBBY = "in_lobby"
    CONNECTED = "connected"
    LEAVING = "leaving"
    ERROR = "error"


@dataclass
class MeetingInfo:
    """Information about a meeting."""
    platform: str
    meeting_id: str
    meeting_url: str
    title: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    organizer: str = ""
    calendar_event_id: str = ""

    # Runtime state
    state: MeetingState = MeetingState.IDLE
    participants: List[str] = field(default_factory=list)
    is_muted: bool = False
    is_camera_on: bool = True
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "meeting_id": self.meeting_id,
            "meeting_url": self.meeting_url,
            "title": self.title,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "organizer": self.organizer,
            "state": self.state.value,
            "participants": self.participants,
            "is_muted": self.is_muted,
            "is_camera_on": self.is_camera_on,
        }


class MeetingProvider(ABC):
    """
    Abstract base class for meeting platform providers.

    Each provider handles joining, controlling, and leaving
    meetings on a specific platform.
    """

    def __init__(self):
        self._state = MeetingState.IDLE
        self._current_meeting: Optional[MeetingInfo] = None
        self._state_callbacks: List[Callable[[MeetingState], None]] = []

    @property
    @abstractmethod
    def name(self) -> str:
        """Return provider name (e.g., 'google_meet')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return human-readable provider name."""
        pass

    @property
    def state(self) -> MeetingState:
        """Get current meeting state."""
        return self._state

    @property
    def current_meeting(self) -> Optional[MeetingInfo]:
        """Get current meeting info."""
        return self._current_meeting

    def add_state_callback(self, callback: Callable[[MeetingState], None]) -> None:
        """Add callback for state changes."""
        self._state_callbacks.append(callback)

    def _set_state(self, state: MeetingState) -> None:
        """Update state and notify callbacks."""
        self._state = state
        if self._current_meeting:
            self._current_meeting.state = state

        for callback in self._state_callbacks:
            try:
                callback(state)
            except Exception:
                pass

    @classmethod
    @abstractmethod
    def can_handle_url(cls, url: str) -> bool:
        """
        Check if this provider can handle a meeting URL.

        Args:
            url: Meeting URL or code

        Returns:
            True if this provider can handle the URL
        """
        pass

    @classmethod
    @abstractmethod
    def extract_meeting_id(cls, url: str) -> Optional[str]:
        """
        Extract meeting ID from URL.

        Args:
            url: Meeting URL

        Returns:
            Meeting ID or None
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the provider.

        Set up browser, load required resources, etc.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the provider.

        Close browser, release resources, etc.
        """
        pass

    @abstractmethod
    async def join_meeting(
        self,
        meeting_url: str,
        display_name: str = "Conference Room",
        camera_on: bool = True,
        mic_on: bool = True
    ) -> MeetingInfo:
        """
        Join a meeting.

        Args:
            meeting_url: Meeting URL or code
            display_name: Name to display in meeting
            camera_on: Start with camera enabled
            mic_on: Start with microphone enabled

        Returns:
            MeetingInfo with connection details
        """
        pass

    @abstractmethod
    async def leave_meeting(self) -> None:
        """Leave the current meeting."""
        pass

    @abstractmethod
    async def toggle_camera(self) -> bool:
        """
        Toggle camera on/off.

        Returns:
            New camera state (True = on)
        """
        pass

    @abstractmethod
    async def toggle_mute(self) -> bool:
        """
        Toggle microphone mute.

        Returns:
            New mute state (True = muted)
        """
        pass

    async def set_camera(self, on: bool) -> bool:
        """
        Set camera state.

        Args:
            on: True to enable camera

        Returns:
            New camera state
        """
        if self._current_meeting and self._current_meeting.is_camera_on != on:
            return await self.toggle_camera()
        return self._current_meeting.is_camera_on if self._current_meeting else False

    async def set_mute(self, muted: bool) -> bool:
        """
        Set mute state.

        Args:
            muted: True to mute

        Returns:
            New mute state
        """
        if self._current_meeting and self._current_meeting.is_muted != muted:
            return await self.toggle_mute()
        return self._current_meeting.is_muted if self._current_meeting else False

    def get_status(self) -> Dict[str, Any]:
        """Get provider status."""
        return {
            "provider": self.name,
            "state": self._state.value,
            "meeting": self._current_meeting.to_dict() if self._current_meeting else None,
        }


def detect_platform(url: str) -> Optional[str]:
    """
    Detect meeting platform from URL.

    Args:
        url: Meeting URL

    Returns:
        Platform name or None
    """
    url_lower = url.lower()

    if "meet.google.com" in url_lower or "g.co/meet" in url_lower:
        return "google_meet"
    elif "teams.microsoft.com" in url_lower or "teams.live.com" in url_lower:
        return "teams"
    elif "zoom.us" in url_lower or "zoomgov.com" in url_lower:
        return "zoom"

    return None

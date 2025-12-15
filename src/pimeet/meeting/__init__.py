"""
Meeting platform support for PiMeet.

Provides integration with video conferencing platforms:
- Google Meet
- Microsoft Teams
- Zoom

Includes advanced meeting controls and quality monitoring.
"""

from pimeet.meeting.service import MeetingService
from pimeet.meeting.providers.base import MeetingProvider, MeetingInfo, MeetingState

from pimeet.meeting.controls import (
    ControlCapability,
    Reaction,
    LayoutMode,
    RecordingState,
    ShareType,
    Participant,
    ChatMessage,
    ScreenShareInfo,
    RecordingInfo,
    MeetingControlsInterface,
    BaseMeetingControls,
    GoogleMeetControls,
    TeamsControls,
    ZoomControls,
    get_controls_for_provider,
)

from pimeet.meeting.quality import (
    QualityLevel,
    IssueType,
    QualityIssue,
    AudioMetrics,
    VideoMetrics,
    NetworkMetrics,
    QualitySnapshot,
    QualityMetricsCollector,
    MeetingQualityService,
)

__all__ = [
    # Core
    "MeetingService",
    "MeetingProvider",
    "MeetingInfo",
    "MeetingState",
    # Controls
    "ControlCapability",
    "Reaction",
    "LayoutMode",
    "RecordingState",
    "ShareType",
    "Participant",
    "ChatMessage",
    "ScreenShareInfo",
    "RecordingInfo",
    "MeetingControlsInterface",
    "BaseMeetingControls",
    "GoogleMeetControls",
    "TeamsControls",
    "ZoomControls",
    "get_controls_for_provider",
    # Quality
    "QualityLevel",
    "IssueType",
    "QualityIssue",
    "AudioMetrics",
    "VideoMetrics",
    "NetworkMetrics",
    "QualitySnapshot",
    "QualityMetricsCollector",
    "MeetingQualityService",
]

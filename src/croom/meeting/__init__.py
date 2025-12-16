"""
Meeting platform support for Croom.

Provides integration with video conferencing platforms:
- Google Meet
- Microsoft Teams
- Zoom

Includes advanced meeting controls and quality monitoring.
"""

from croom.meeting.service import MeetingService
from croom.meeting.providers.base import MeetingProvider, MeetingInfo, MeetingState

from croom.meeting.controls import (
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
    WebexControls,
    get_controls_for_provider,
)

from croom.meeting.quality import (
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
    "WebexControls",
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

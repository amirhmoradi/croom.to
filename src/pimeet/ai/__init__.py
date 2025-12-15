"""
AI features for PiMeet.

This module provides AI-powered features including:
- Person detection
- Face detection
- Auto-framing with smooth tracking
- Speaker tracking and localization
- PTZ camera control
- Noise reduction
- Occupancy counting
"""

from pimeet.ai.service import AIService
from pimeet.ai.backends.base import AIBackend

from pimeet.ai.auto_framing import (
    FramingMode,
    TransitionType,
    BoundingBox,
    FrameRegion,
    AutoFramingEngine,
    AutoFramingService,
)

from pimeet.ai.speaker_tracking import (
    SpeakerState,
    SpeakerInfo,
    AudioActivityDetector,
    SpeakerTracker,
    SpeakerTrackingService,
)

from pimeet.ai.ptz_control import (
    PTZProtocol,
    PTZCapability,
    PTZPosition,
    PTZPreset,
    PTZController,
    VISCAController,
    SoftwarePTZController,
    PTZService,
)

__all__ = [
    # Core
    "AIService",
    "AIBackend",
    # Auto-framing
    "FramingMode",
    "TransitionType",
    "BoundingBox",
    "FrameRegion",
    "AutoFramingEngine",
    "AutoFramingService",
    # Speaker tracking
    "SpeakerState",
    "SpeakerInfo",
    "AudioActivityDetector",
    "SpeakerTracker",
    "SpeakerTrackingService",
    # PTZ control
    "PTZProtocol",
    "PTZCapability",
    "PTZPosition",
    "PTZPreset",
    "PTZController",
    "VISCAController",
    "SoftwarePTZController",
    "PTZService",
]

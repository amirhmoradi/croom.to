"""
AI features for Croom.

This module provides AI-powered features including:
- Person detection
- Face detection
- Auto-framing with smooth tracking
- Speaker tracking and localization
- PTZ camera control
- Noise reduction
- Occupancy counting
"""

from croom.ai.service import AIService
from croom.ai.backends.base import AIBackend

from croom.ai.auto_framing import (
    FramingMode,
    TransitionType,
    BoundingBox,
    FrameRegion,
    AutoFramingEngine,
    AutoFramingService,
)

from croom.ai.speaker_tracking import (
    SpeakerState,
    SpeakerInfo,
    AudioActivityDetector,
    SpeakerTracker,
    SpeakerTrackingService,
)

from croom.ai.ptz_control import (
    PTZProtocol,
    PTZCapability,
    PTZPosition,
    PTZPreset,
    PTZController,
    VISCAController,
    SoftwarePTZController,
    PTZService,
)

from croom.ai.gesture_recognition import (
    GestureType,
    GestureAction,
    HandLandmarks,
    GestureEvent,
    GestureConfig,
    GestureClassifier,
    GestureActionMapper,
    GestureRecognitionService,
    GestureMeetingController,
)

from croom.ai.privacy_mode import (
    AIFeature,
    PrivacyLevel,
    PrivacySchedule,
    PrivacyConfig,
    PrivacyModeService,
    PrivacyIndicator,
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
    # Gesture recognition
    "GestureType",
    "GestureAction",
    "HandLandmarks",
    "GestureEvent",
    "GestureConfig",
    "GestureClassifier",
    "GestureActionMapper",
    "GestureRecognitionService",
    "GestureMeetingController",
    # Privacy mode
    "AIFeature",
    "PrivacyLevel",
    "PrivacySchedule",
    "PrivacyConfig",
    "PrivacyModeService",
    "PrivacyIndicator",
]

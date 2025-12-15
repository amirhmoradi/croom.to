"""
Audio module for Croom.

Provides audio capture, playback, and processing:
- Device management (USB, ALSA, PulseAudio)
- Noise reduction (RNNoise, DeepFilterNet)
- Echo cancellation
- Volume control
"""

from croom.audio.service import AudioService, create_audio_service
from croom.audio.device import (
    AudioDevice,
    AudioDeviceInfo,
    AudioDeviceType,
    get_audio_devices,
)
from croom.audio.processor import (
    AudioProcessor,
    NoiseReduction,
    EchoCancellation,
)

__all__ = [
    "AudioService",
    "create_audio_service",
    "AudioDevice",
    "AudioDeviceInfo",
    "AudioDeviceType",
    "get_audio_devices",
    "AudioProcessor",
    "NoiseReduction",
    "EchoCancellation",
]

"""
Audio module for PiMeet.

Provides audio capture, playback, and processing:
- Device management (USB, ALSA, PulseAudio)
- Noise reduction (RNNoise, DeepFilterNet)
- Echo cancellation
- Volume control
"""

from pimeet.audio.service import AudioService, create_audio_service
from pimeet.audio.device import (
    AudioDevice,
    AudioDeviceInfo,
    AudioDeviceType,
    get_audio_devices,
)
from pimeet.audio.processor import (
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

"""
Hardware Profiles for PiMeet.

Defines platform-specific configurations and capabilities for different
hardware targets (Raspberry Pi, x86_64 PCs, NUCs, etc.).
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

from pimeet.platform.detector import (
    DeviceType,
    Architecture,
    PlatformDetector,
    PlatformInfo,
)

logger = logging.getLogger(__name__)


class PerformanceTier(Enum):
    """Performance tier for AI and video processing."""
    MINIMAL = "minimal"    # CPU-only, 480p/720p, basic features
    LOW = "low"            # Basic accelerator, 720p, limited AI
    MEDIUM = "medium"      # Good accelerator, 1080p, most AI features
    HIGH = "high"          # High-end GPU, 1080p/4K, all features
    ULTRA = "ultra"        # Top-tier GPU, 4K, max performance


@dataclass
class DisplayProfile:
    """Display configuration profile."""
    default_resolution: tuple = (1920, 1080)
    supported_resolutions: List[tuple] = field(default_factory=lambda: [(1920, 1080)])
    hdmi_cec_supported: bool = False
    ddc_ci_supported: bool = False
    touch_supported: bool = False
    brightness_control: bool = False


@dataclass
class AIProfile:
    """AI acceleration profile."""
    preferred_backend: str = "cpu"
    fallback_backends: List[str] = field(default_factory=lambda: ["cpu"])
    max_inference_fps: int = 10
    batch_size: int = 1
    precision: str = "fp32"  # fp32, fp16, int8
    features_enabled: List[str] = field(default_factory=list)


@dataclass
class AudioProfile:
    """Audio configuration profile."""
    preferred_backend: str = "auto"  # pulseaudio, pipewire, alsa
    sample_rate: int = 48000
    channels: int = 2
    echo_cancellation: bool = True
    noise_reduction: bool = True
    agc: bool = True  # Automatic Gain Control


@dataclass
class VideoProfile:
    """Video/camera configuration profile."""
    preferred_backend: str = "auto"  # v4l2, opencv, libcamera
    default_resolution: tuple = (1920, 1080)
    default_fps: int = 30
    supported_resolutions: List[tuple] = field(default_factory=lambda: [
        (1920, 1080), (1280, 720), (640, 480)
    ])
    auto_exposure: bool = True
    auto_focus: bool = True
    ptz_supported: bool = False


@dataclass
class HardwareProfile:
    """Complete hardware profile for a platform."""
    name: str
    device_type: DeviceType
    architecture: Architecture
    performance_tier: PerformanceTier

    display: DisplayProfile = field(default_factory=DisplayProfile)
    ai: AIProfile = field(default_factory=AIProfile)
    audio: AudioProfile = field(default_factory=AudioProfile)
    video: VideoProfile = field(default_factory=VideoProfile)

    # Hardware capabilities
    has_gpio: bool = False
    has_i2c: bool = False
    has_spi: bool = False
    has_hdmi_cec: bool = False
    has_hardware_encoder: bool = False

    # System resources
    recommended_ram_mb: int = 2048
    recommended_storage_gb: int = 16

    # Service configuration
    auto_start: bool = True
    kiosk_mode: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "device_type": self.device_type.value,
            "architecture": self.architecture.value,
            "performance_tier": self.performance_tier.value,
            "display": {
                "default_resolution": list(self.display.default_resolution),
                "hdmi_cec_supported": self.display.hdmi_cec_supported,
                "ddc_ci_supported": self.display.ddc_ci_supported,
                "touch_supported": self.display.touch_supported,
            },
            "ai": {
                "preferred_backend": self.ai.preferred_backend,
                "max_inference_fps": self.ai.max_inference_fps,
                "precision": self.ai.precision,
                "features_enabled": self.ai.features_enabled,
            },
            "has_gpio": self.has_gpio,
            "has_hdmi_cec": self.has_hdmi_cec,
        }


# Pre-defined hardware profiles

PROFILE_RASPBERRY_PI_5 = HardwareProfile(
    name="Raspberry Pi 5",
    device_type=DeviceType.RASPBERRY_PI_5,
    architecture=Architecture.ARM64,
    performance_tier=PerformanceTier.MEDIUM,
    display=DisplayProfile(
        default_resolution=(1920, 1080),
        supported_resolutions=[(3840, 2160), (1920, 1080), (1280, 720)],
        hdmi_cec_supported=True,
        ddc_ci_supported=False,
        touch_supported=True,
        brightness_control=True,
    ),
    ai=AIProfile(
        preferred_backend="hailo",
        fallback_backends=["coral", "cpu"],
        max_inference_fps=30,
        batch_size=1,
        precision="int8",
        features_enabled=[
            "person_detection",
            "face_detection",
            "speaker_tracking",
            "hand_raise_detection",
            "occupancy_counting",
        ],
    ),
    audio=AudioProfile(
        preferred_backend="pipewire",
        echo_cancellation=True,
        noise_reduction=True,
    ),
    video=VideoProfile(
        preferred_backend="libcamera",
        default_resolution=(1920, 1080),
        default_fps=30,
        ptz_supported=True,
    ),
    has_gpio=True,
    has_i2c=True,
    has_spi=True,
    has_hdmi_cec=True,
    has_hardware_encoder=True,
    recommended_ram_mb=4096,
    recommended_storage_gb=32,
    auto_start=True,
    kiosk_mode=True,
)

PROFILE_RASPBERRY_PI_4 = HardwareProfile(
    name="Raspberry Pi 4",
    device_type=DeviceType.RASPBERRY_PI_4,
    architecture=Architecture.ARM64,
    performance_tier=PerformanceTier.LOW,
    display=DisplayProfile(
        default_resolution=(1920, 1080),
        supported_resolutions=[(1920, 1080), (1280, 720)],
        hdmi_cec_supported=True,
        touch_supported=True,
    ),
    ai=AIProfile(
        preferred_backend="coral",
        fallback_backends=["cpu"],
        max_inference_fps=15,
        batch_size=1,
        precision="int8",
        features_enabled=[
            "person_detection",
            "occupancy_counting",
        ],
    ),
    video=VideoProfile(
        preferred_backend="libcamera",
        default_resolution=(1280, 720),
        default_fps=30,
    ),
    has_gpio=True,
    has_i2c=True,
    has_hdmi_cec=True,
    recommended_ram_mb=4096,
    recommended_storage_gb=16,
    kiosk_mode=True,
)

PROFILE_X86_64_NVIDIA = HardwareProfile(
    name="x86_64 with NVIDIA GPU",
    device_type=DeviceType.PC,
    architecture=Architecture.AMD64,
    performance_tier=PerformanceTier.HIGH,
    display=DisplayProfile(
        default_resolution=(1920, 1080),
        supported_resolutions=[(3840, 2160), (2560, 1440), (1920, 1080), (1280, 720)],
        hdmi_cec_supported=False,
        ddc_ci_supported=True,
        touch_supported=True,
        brightness_control=True,
    ),
    ai=AIProfile(
        preferred_backend="nvidia",
        fallback_backends=["coral", "cpu"],
        max_inference_fps=60,
        batch_size=4,
        precision="fp16",
        features_enabled=[
            "person_detection",
            "face_detection",
            "speaker_tracking",
            "hand_raise_detection",
            "occupancy_counting",
            "gesture_recognition",
            "noise_reduction",
        ],
    ),
    audio=AudioProfile(
        preferred_backend="pipewire",
        echo_cancellation=True,
        noise_reduction=True,
    ),
    video=VideoProfile(
        preferred_backend="v4l2",
        default_resolution=(1920, 1080),
        default_fps=30,
        supported_resolutions=[
            (3840, 2160), (1920, 1080), (1280, 720), (640, 480)
        ],
    ),
    has_gpio=False,
    has_i2c=False,
    has_hdmi_cec=False,
    has_hardware_encoder=True,  # NVENC
    recommended_ram_mb=8192,
    recommended_storage_gb=64,
    auto_start=True,
    kiosk_mode=False,
)

PROFILE_X86_64_INTEL = HardwareProfile(
    name="x86_64 with Intel CPU/GPU",
    device_type=DeviceType.PC,
    architecture=Architecture.AMD64,
    performance_tier=PerformanceTier.MEDIUM,
    display=DisplayProfile(
        default_resolution=(1920, 1080),
        supported_resolutions=[(3840, 2160), (1920, 1080), (1280, 720)],
        hdmi_cec_supported=False,
        ddc_ci_supported=True,
        brightness_control=True,
    ),
    ai=AIProfile(
        preferred_backend="intel",
        fallback_backends=["coral", "cpu"],
        max_inference_fps=30,
        batch_size=2,
        precision="fp16",
        features_enabled=[
            "person_detection",
            "face_detection",
            "speaker_tracking",
            "occupancy_counting",
        ],
    ),
    audio=AudioProfile(
        preferred_backend="pipewire",
        echo_cancellation=True,
        noise_reduction=True,
    ),
    video=VideoProfile(
        preferred_backend="v4l2",
        default_resolution=(1920, 1080),
        default_fps=30,
    ),
    has_gpio=False,
    has_hdmi_cec=False,
    has_hardware_encoder=True,  # QSV
    recommended_ram_mb=8192,
    recommended_storage_gb=64,
)

PROFILE_X86_64_CPU_ONLY = HardwareProfile(
    name="x86_64 CPU Only",
    device_type=DeviceType.PC,
    architecture=Architecture.AMD64,
    performance_tier=PerformanceTier.LOW,
    display=DisplayProfile(
        default_resolution=(1920, 1080),
        supported_resolutions=[(1920, 1080), (1280, 720)],
        ddc_ci_supported=True,
    ),
    ai=AIProfile(
        preferred_backend="cpu",
        fallback_backends=[],
        max_inference_fps=10,
        batch_size=1,
        precision="fp32",
        features_enabled=[
            "person_detection",
            "occupancy_counting",
        ],
    ),
    video=VideoProfile(
        preferred_backend="v4l2",
        default_resolution=(1280, 720),
        default_fps=30,
    ),
    has_gpio=False,
    has_hdmi_cec=False,
    recommended_ram_mb=4096,
    recommended_storage_gb=32,
)

PROFILE_NUC = HardwareProfile(
    name="Intel NUC",
    device_type=DeviceType.NUC,
    architecture=Architecture.AMD64,
    performance_tier=PerformanceTier.MEDIUM,
    display=DisplayProfile(
        default_resolution=(1920, 1080),
        supported_resolutions=[(3840, 2160), (1920, 1080), (1280, 720)],
        hdmi_cec_supported=True,  # Some NUCs support CEC
        ddc_ci_supported=True,
        brightness_control=True,
    ),
    ai=AIProfile(
        preferred_backend="intel",
        fallback_backends=["coral", "cpu"],
        max_inference_fps=30,
        batch_size=2,
        precision="fp16",
        features_enabled=[
            "person_detection",
            "face_detection",
            "speaker_tracking",
            "occupancy_counting",
        ],
    ),
    audio=AudioProfile(
        preferred_backend="pipewire",
        echo_cancellation=True,
        noise_reduction=True,
    ),
    video=VideoProfile(
        preferred_backend="v4l2",
        default_resolution=(1920, 1080),
        default_fps=30,
    ),
    has_gpio=False,
    has_hdmi_cec=True,
    has_hardware_encoder=True,  # QSV
    recommended_ram_mb=8192,
    recommended_storage_gb=128,
    auto_start=True,
    kiosk_mode=True,
)

PROFILE_JETSON = HardwareProfile(
    name="NVIDIA Jetson",
    device_type=DeviceType.JETSON,
    architecture=Architecture.ARM64,
    performance_tier=PerformanceTier.HIGH,
    display=DisplayProfile(
        default_resolution=(1920, 1080),
        supported_resolutions=[(3840, 2160), (1920, 1080), (1280, 720)],
        hdmi_cec_supported=False,
    ),
    ai=AIProfile(
        preferred_backend="nvidia",
        fallback_backends=["cpu"],
        max_inference_fps=60,
        batch_size=4,
        precision="fp16",
        features_enabled=[
            "person_detection",
            "face_detection",
            "speaker_tracking",
            "hand_raise_detection",
            "occupancy_counting",
            "gesture_recognition",
        ],
    ),
    video=VideoProfile(
        preferred_backend="v4l2",
        default_resolution=(1920, 1080),
        default_fps=30,
    ),
    has_gpio=True,
    has_i2c=True,
    has_hardware_encoder=True,  # NVENC
    recommended_ram_mb=8192,
    recommended_storage_gb=64,
)


# Profile registry
PROFILES = {
    DeviceType.RASPBERRY_PI_5: PROFILE_RASPBERRY_PI_5,
    DeviceType.RASPBERRY_PI_4: PROFILE_RASPBERRY_PI_4,
    DeviceType.PC: PROFILE_X86_64_CPU_ONLY,  # Default, may be upgraded
    DeviceType.NUC: PROFILE_NUC,
    DeviceType.JETSON: PROFILE_JETSON,
}


def detect_profile() -> HardwareProfile:
    """
    Detect and return the appropriate hardware profile for the current system.

    Returns:
        HardwareProfile matching the detected hardware.
    """
    info = PlatformDetector.detect()

    # Get base profile for device type
    profile = PROFILES.get(info.device, PROFILE_X86_64_CPU_ONLY)

    # For x86_64, upgrade profile based on detected GPU
    if info.arch == Architecture.AMD64:
        if info.gpu:
            from pimeet.platform.detector import GPUVendor
            if info.gpu.vendor == GPUVendor.NVIDIA:
                profile = PROFILE_X86_64_NVIDIA
                logger.info(f"Using NVIDIA profile for {info.gpu.name}")
            elif info.gpu.vendor == GPUVendor.INTEL:
                profile = PROFILE_X86_64_INTEL
                logger.info(f"Using Intel profile for {info.gpu.name}")
            elif info.gpu.vendor == GPUVendor.AMD:
                # AMD uses CPU/OpenCL for now
                profile = PROFILE_X86_64_CPU_ONLY
                profile.ai.features_enabled.extend([
                    "person_detection",
                    "face_detection",
                ])
                logger.info(f"Using AMD profile for {info.gpu.name}")

    logger.info(f"Detected hardware profile: {profile.name}")
    return profile


def get_profile_for_device(device_type: DeviceType) -> HardwareProfile:
    """
    Get hardware profile for a specific device type.

    Args:
        device_type: Target device type

    Returns:
        HardwareProfile for the device
    """
    return PROFILES.get(device_type, PROFILE_X86_64_CPU_ONLY)


class ProfileManager:
    """
    Manages hardware profiles and provides configuration based on detected hardware.
    """

    def __init__(self):
        self._profile: Optional[HardwareProfile] = None
        self._platform_info: Optional[PlatformInfo] = None

    def initialize(self) -> HardwareProfile:
        """
        Initialize profile manager and detect hardware.

        Returns:
            Detected HardwareProfile
        """
        self._platform_info = PlatformDetector.detect()
        self._profile = detect_profile()
        return self._profile

    @property
    def profile(self) -> HardwareProfile:
        """Get current hardware profile."""
        if not self._profile:
            self.initialize()
        return self._profile

    @property
    def platform_info(self) -> PlatformInfo:
        """Get platform information."""
        if not self._platform_info:
            self._platform_info = PlatformDetector.detect()
        return self._platform_info

    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration from profile."""
        return {
            "backend": self.profile.ai.preferred_backend,
            "fallback_backends": self.profile.ai.fallback_backends,
            "max_fps": self.profile.ai.max_inference_fps,
            "batch_size": self.profile.ai.batch_size,
            "precision": self.profile.ai.precision,
            "features": self.profile.ai.features_enabled,
        }

    def get_display_config(self) -> Dict[str, Any]:
        """Get display configuration from profile."""
        return {
            "resolution": list(self.profile.display.default_resolution),
            "cec_enabled": self.profile.display.hdmi_cec_supported,
            "ddc_enabled": self.profile.display.ddc_ci_supported,
            "touch_enabled": self.profile.display.touch_supported,
            "brightness_control": self.profile.display.brightness_control,
        }

    def get_video_config(self) -> Dict[str, Any]:
        """Get video/camera configuration from profile."""
        return {
            "backend": self.profile.video.preferred_backend,
            "resolution": list(self.profile.video.default_resolution),
            "fps": self.profile.video.default_fps,
            "auto_exposure": self.profile.video.auto_exposure,
            "auto_focus": self.profile.video.auto_focus,
        }

    def get_audio_config(self) -> Dict[str, Any]:
        """Get audio configuration from profile."""
        return {
            "backend": self.profile.audio.preferred_backend,
            "sample_rate": self.profile.audio.sample_rate,
            "channels": self.profile.audio.channels,
            "echo_cancellation": self.profile.audio.echo_cancellation,
            "noise_reduction": self.profile.audio.noise_reduction,
            "agc": self.profile.audio.agc,
        }


# Singleton instance
_profile_manager: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Get profile manager singleton."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager

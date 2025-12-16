"""
Platform capabilities module.

Provides a high-level interface to query what features are available
on the current platform.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from croom.platform.detector import PlatformDetector, DeviceType


@dataclass
class AICapabilities:
    """AI-related capabilities."""
    has_hailo: bool = False
    has_coral: bool = False
    has_nvidia: bool = False
    has_cpu_inference: bool = True

    # Feature availability based on hardware
    can_person_detect: bool = True  # All platforms (varies by speed)
    can_face_detect: bool = True
    can_auto_frame: bool = True
    can_noise_reduce: bool = True  # CPU-based, always available
    can_echo_cancel: bool = True   # CPU-based, always available
    can_speaker_track: bool = False  # Requires AI accelerator + PTZ
    can_hand_raise_detect: bool = False  # Requires AI accelerator
    can_occupancy_count: bool = True

    # Performance tiers
    inference_fps_estimate: int = 5  # Expected FPS for detection

    @property
    def best_accelerator(self) -> str:
        """Return the best available accelerator."""
        if self.has_hailo:
            return "hailo"
        elif self.has_nvidia:
            return "nvidia"
        elif self.has_coral:
            return "coral"
        return "cpu"


@dataclass
class AudioCapabilities:
    """Audio-related capabilities."""
    has_pulseaudio: bool = False
    has_pipewire: bool = False
    can_noise_reduce: bool = True
    can_echo_cancel: bool = True
    can_select_device: bool = True


@dataclass
class VideoCapabilities:
    """Video-related capabilities."""
    has_v4l2: bool = False
    has_picamera: bool = False
    cameras_detected: List[str] = None
    can_capture: bool = True
    can_auto_frame: bool = True

    def __post_init__(self):
        if self.cameras_detected is None:
            self.cameras_detected = []


@dataclass
class DisplayCapabilities:
    """Display-related capabilities."""
    has_hdmi_cec: bool = False
    has_ddc: bool = False
    has_touch: bool = False
    displays_detected: List[str] = None
    can_power_control: bool = False

    def __post_init__(self):
        if self.displays_detected is None:
            self.displays_detected = []


@dataclass
class Capabilities:
    """Complete platform capabilities."""
    ai: AICapabilities = None
    audio: AudioCapabilities = None
    video: VideoCapabilities = None
    display: DisplayCapabilities = None

    # General capabilities
    can_run_headless: bool = True
    can_run_touch_ui: bool = True
    can_join_meetings: bool = True

    def __post_init__(self):
        if self.ai is None:
            self.ai = AICapabilities()
        if self.audio is None:
            self.audio = AudioCapabilities()
        if self.video is None:
            self.video = VideoCapabilities()
        if self.display is None:
            self.display = DisplayCapabilities()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "ai": {
                "best_accelerator": self.ai.best_accelerator,
                "has_hailo": self.ai.has_hailo,
                "has_coral": self.ai.has_coral,
                "has_nvidia": self.ai.has_nvidia,
                "inference_fps_estimate": self.ai.inference_fps_estimate,
                "features": {
                    "person_detection": self.ai.can_person_detect,
                    "face_detection": self.ai.can_face_detect,
                    "auto_framing": self.ai.can_auto_frame,
                    "noise_reduction": self.ai.can_noise_reduce,
                    "echo_cancellation": self.ai.can_echo_cancel,
                    "speaker_tracking": self.ai.can_speaker_track,
                    "hand_raise_detection": self.ai.can_hand_raise_detect,
                    "occupancy_counting": self.ai.can_occupancy_count,
                },
            },
            "audio": {
                "backend": "pipewire" if self.audio.has_pipewire else "pulseaudio",
                "noise_reduction": self.audio.can_noise_reduce,
                "echo_cancellation": self.audio.can_echo_cancel,
            },
            "video": {
                "cameras": self.video.cameras_detected,
                "auto_framing": self.video.can_auto_frame,
            },
            "display": {
                "hdmi_cec": self.display.has_hdmi_cec,
                "touch": self.display.has_touch,
                "power_control": self.display.can_power_control,
            },
        }


class CapabilityDetector:
    """Detects detailed capabilities based on platform."""

    @classmethod
    def detect(cls) -> Capabilities:
        """Detect all capabilities for the current platform."""
        platform_info = PlatformDetector.detect()
        caps = Capabilities()

        # Detect AI capabilities
        caps.ai = cls._detect_ai_capabilities(platform_info)

        # Detect audio capabilities
        caps.audio = cls._detect_audio_capabilities()

        # Detect video capabilities
        caps.video = cls._detect_video_capabilities(platform_info)

        # Detect display capabilities
        caps.display = cls._detect_display_capabilities(platform_info)

        return caps

    @classmethod
    def _detect_ai_capabilities(cls, platform_info) -> AICapabilities:
        """Detect AI capabilities."""
        caps = AICapabilities()

        # Check accelerators from platform detection
        accelerators = platform_info.ai_accelerators

        caps.has_hailo = "hailo" in accelerators
        caps.has_coral = "coral" in accelerators
        caps.has_nvidia = "nvidia" in accelerators

        # Estimate FPS based on best accelerator
        if caps.has_hailo:
            caps.inference_fps_estimate = 30
            caps.can_speaker_track = True
            caps.can_hand_raise_detect = True
        elif caps.has_nvidia:
            caps.inference_fps_estimate = 60  # NVIDIA GPUs are fast
            caps.can_speaker_track = True
            caps.can_hand_raise_detect = True
        elif caps.has_coral:
            caps.inference_fps_estimate = 15
            caps.can_speaker_track = True
            caps.can_hand_raise_detect = True
        else:
            # CPU only
            if platform_info.device == DeviceType.RASPBERRY_PI_5:
                caps.inference_fps_estimate = 5
            elif platform_info.device == DeviceType.RASPBERRY_PI_4:
                caps.inference_fps_estimate = 2
            else:
                caps.inference_fps_estimate = 10  # PC CPUs are faster

        return caps

    @classmethod
    def _detect_audio_capabilities(cls) -> AudioCapabilities:
        """Detect audio capabilities."""
        import subprocess
        caps = AudioCapabilities()

        # Check for PipeWire
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "pipewire"],
                capture_output=True,
                timeout=5
            )
            caps.has_pipewire = result.returncode == 0
        except Exception:
            pass

        # Check for PulseAudio
        try:
            result = subprocess.run(
                ["pactl", "info"],
                capture_output=True,
                timeout=5
            )
            caps.has_pulseaudio = result.returncode == 0
        except Exception:
            pass

        return caps

    @classmethod
    def _detect_video_capabilities(cls, platform_info) -> VideoCapabilities:
        """Detect video capabilities."""
        import subprocess
        caps = VideoCapabilities()

        # Check for V4L2 devices
        try:
            result = subprocess.run(
                ["v4l2-ctl", "--list-devices"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                caps.has_v4l2 = True
                # Parse device list
                output = result.stdout.decode()
                cameras = []
                for line in output.split("\n"):
                    if "/dev/video" in line:
                        cameras.append(line.strip())
                caps.cameras_detected = cameras
        except Exception:
            pass

        # Check for Pi camera
        caps.has_picamera = platform_info.has_camera_module

        return caps

    @classmethod
    def _detect_display_capabilities(cls, platform_info) -> DisplayCapabilities:
        """Detect display capabilities."""
        import subprocess
        caps = DisplayCapabilities()

        caps.has_hdmi_cec = platform_info.has_hdmi_cec
        caps.has_touch = platform_info.has_touch_display

        # HDMI-CEC enables power control
        caps.can_power_control = caps.has_hdmi_cec

        # Detect displays
        try:
            result = subprocess.run(
                ["xrandr", "--listmonitors"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                displays = []
                for line in result.stdout.decode().split("\n"):
                    if ":" in line and "Monitors" not in line:
                        displays.append(line.strip())
                caps.displays_detected = displays
        except Exception:
            pass

        return caps


def get_capabilities() -> Capabilities:
    """Convenience function to get platform capabilities."""
    return CapabilityDetector.detect()

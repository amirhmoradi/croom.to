"""
Configuration management for PiMeet.

Handles loading, validation, and access to configuration settings.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path


# Default configuration paths
CONFIG_PATHS = [
    "/etc/pimeet/config.yaml",
    os.path.expanduser("~/.config/pimeet/config.yaml"),
    "config.yaml",
]


@dataclass
class RoomConfig:
    """Room-specific configuration."""
    name: str = "Conference Room"
    location: str = ""
    timezone: str = "UTC"


@dataclass
class MeetingConfig:
    """Meeting service configuration."""
    platforms: List[str] = field(default_factory=lambda: ["google_meet", "teams", "zoom"])
    default_platform: str = "auto"
    join_early_minutes: int = 1
    auto_leave: bool = True
    camera_default_on: bool = True
    mic_default_on: bool = True


@dataclass
class CalendarConfig:
    """Calendar integration configuration."""
    providers: List[str] = field(default_factory=lambda: ["google", "microsoft"])
    sync_interval_seconds: int = 60
    google_credentials_path: str = ""
    microsoft_tenant_id: str = ""
    microsoft_client_id: str = ""


@dataclass
class AIConfig:
    """AI features configuration."""
    enabled: bool = True
    backend: str = "auto"  # 'hailo', 'coral', 'nvidia', 'cpu', 'auto'

    # Feature toggles
    person_detection: bool = True
    noise_reduction: bool = True
    echo_cancellation: bool = True
    auto_framing: bool = True
    occupancy_counting: bool = True
    speaker_detection: bool = False  # Requires accelerator
    hand_raise_detection: bool = False  # Requires accelerator

    # Privacy
    privacy_mode: bool = False  # Disables all AI when True


@dataclass
class AudioConfig:
    """Audio configuration."""
    backend: str = "auto"  # 'pulseaudio', 'pipewire', 'auto'
    input_device: str = "auto"
    output_device: str = "auto"
    noise_reduction_level: str = "medium"  # 'off', 'light', 'medium', 'aggressive'
    echo_cancellation: bool = True


@dataclass
class VideoConfig:
    """Video configuration."""
    backend: str = "auto"  # 'v4l2', 'picamera', 'auto'
    device: str = "auto"
    resolution: str = "1080p"
    framerate: int = 30


@dataclass
class DisplayConfig:
    """Display configuration."""
    backend: str = "auto"  # 'hdmi_cec', 'ddc', 'none', 'auto'
    power_on_boot: bool = True
    power_off_shutdown: bool = True
    touch_enabled: bool = True


@dataclass
class DashboardConfig:
    """Management dashboard connection configuration."""
    enabled: bool = True
    url: str = ""
    enrollment_token: str = ""
    heartbeat_interval_seconds: int = 30
    metrics_interval_seconds: int = 60


@dataclass
class UpdateConfig:
    """Update configuration."""
    auto_check: bool = True
    auto_install: bool = False  # Require manual admin approval
    check_interval_hours: int = 24
    channel: str = "stable"  # 'stable', 'beta', 'nightly'


@dataclass
class SecurityConfig:
    """Security configuration."""
    admin_pin: str = ""  # For local UI access
    ssh_enabled: bool = True
    require_encryption: bool = True


@dataclass
class Config:
    """Main configuration class."""
    version: int = 2
    room: RoomConfig = field(default_factory=RoomConfig)
    meeting: MeetingConfig = field(default_factory=MeetingConfig)
    calendar: CalendarConfig = field(default_factory=CalendarConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    updates: UpdateConfig = field(default_factory=UpdateConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # Platform override (usually auto-detected)
    platform_type: str = "auto"  # 'rpi5', 'rpi4', 'pc', 'auto'

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        config = cls()

        if "version" in data:
            config.version = data["version"]

        if "platform_type" in data:
            config.platform_type = data["platform_type"]

        if "room" in data:
            config.room = RoomConfig(**data["room"])

        if "meeting" in data:
            config.meeting = MeetingConfig(**data["meeting"])

        if "calendar" in data:
            config.calendar = CalendarConfig(**data["calendar"])

        if "ai" in data:
            config.ai = AIConfig(**data["ai"])

        if "audio" in data:
            config.audio = AudioConfig(**data["audio"])

        if "video" in data:
            config.video = VideoConfig(**data["video"])

        if "display" in data:
            config.display = DisplayConfig(**data["display"])

        if "dashboard" in data:
            config.dashboard = DashboardConfig(**data["dashboard"])

        if "updates" in data:
            config.updates = UpdateConfig(**data["updates"])

        if "security" in data:
            config.security = SecurityConfig(**data["security"])

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert Config to dictionary."""
        return {
            "version": self.version,
            "platform_type": self.platform_type,
            "room": {
                "name": self.room.name,
                "location": self.room.location,
                "timezone": self.room.timezone,
            },
            "meeting": {
                "platforms": self.meeting.platforms,
                "default_platform": self.meeting.default_platform,
                "join_early_minutes": self.meeting.join_early_minutes,
                "auto_leave": self.meeting.auto_leave,
                "camera_default_on": self.meeting.camera_default_on,
                "mic_default_on": self.meeting.mic_default_on,
            },
            "calendar": {
                "providers": self.calendar.providers,
                "sync_interval_seconds": self.calendar.sync_interval_seconds,
            },
            "ai": {
                "enabled": self.ai.enabled,
                "backend": self.ai.backend,
                "person_detection": self.ai.person_detection,
                "noise_reduction": self.ai.noise_reduction,
                "echo_cancellation": self.ai.echo_cancellation,
                "auto_framing": self.ai.auto_framing,
                "occupancy_counting": self.ai.occupancy_counting,
                "speaker_detection": self.ai.speaker_detection,
                "hand_raise_detection": self.ai.hand_raise_detection,
                "privacy_mode": self.ai.privacy_mode,
            },
            "audio": {
                "backend": self.audio.backend,
                "input_device": self.audio.input_device,
                "output_device": self.audio.output_device,
                "noise_reduction_level": self.audio.noise_reduction_level,
                "echo_cancellation": self.audio.echo_cancellation,
            },
            "video": {
                "backend": self.video.backend,
                "device": self.video.device,
                "resolution": self.video.resolution,
                "framerate": self.video.framerate,
            },
            "display": {
                "backend": self.display.backend,
                "power_on_boot": self.display.power_on_boot,
                "power_off_shutdown": self.display.power_off_shutdown,
                "touch_enabled": self.display.touch_enabled,
            },
            "dashboard": {
                "enabled": self.dashboard.enabled,
                "url": self.dashboard.url,
                "heartbeat_interval_seconds": self.dashboard.heartbeat_interval_seconds,
                "metrics_interval_seconds": self.dashboard.metrics_interval_seconds,
            },
            "updates": {
                "auto_check": self.updates.auto_check,
                "auto_install": self.updates.auto_install,
                "check_interval_hours": self.updates.check_interval_hours,
                "channel": self.updates.channel,
            },
            "security": {
                "ssh_enabled": self.security.ssh_enabled,
                "require_encryption": self.security.require_encryption,
            },
        }

    def save(self, path: Optional[str] = None):
        """Save configuration to file."""
        if path is None:
            path = CONFIG_PATHS[0]

        # Ensure directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)


def load_config(path: Optional[str] = None) -> Config:
    """
    Load configuration from file.

    Args:
        path: Path to config file. If None, searches default locations.

    Returns:
        Config object with loaded or default settings.
    """
    if path is not None:
        paths_to_try = [path]
    else:
        paths_to_try = CONFIG_PATHS

    for config_path in paths_to_try:
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    data = yaml.safe_load(f)
                    if data:
                        return Config.from_dict(data)
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")

    # Return default config
    return Config()


def get_config_path() -> Optional[str]:
    """Get the path to the active config file."""
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            return path
    return None

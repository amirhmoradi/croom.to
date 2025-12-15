"""
Privacy Mode for PiMeet AI Features.

Provides comprehensive privacy controls for AI features including:
- Complete AI disable
- Selective feature disable
- Data collection controls
- Visual indicators
- Scheduled privacy windows
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, time as dtime, timedelta
from enum import Enum, Flag, auto
from typing import Any, Callable, Dict, List, Optional, Set
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class AIFeature(Flag):
    """AI features that can be individually controlled."""
    NONE = 0
    PERSON_DETECTION = auto()
    FACE_DETECTION = auto()
    SPEAKER_TRACKING = auto()
    AUTO_FRAMING = auto()
    GESTURE_RECOGNITION = auto()
    OCCUPANCY_COUNTING = auto()
    NOISE_SUPPRESSION = auto()
    ECHO_CANCELLATION = auto()
    BACKGROUND_BLUR = auto()
    VIRTUAL_BACKGROUND = auto()
    TRANSCRIPTION = auto()
    MEETING_INSIGHTS = auto()

    # Convenience groups
    @classmethod
    def VIDEO_PROCESSING(cls) -> "AIFeature":
        return (cls.PERSON_DETECTION | cls.FACE_DETECTION |
                cls.SPEAKER_TRACKING | cls.AUTO_FRAMING |
                cls.GESTURE_RECOGNITION | cls.OCCUPANCY_COUNTING |
                cls.BACKGROUND_BLUR | cls.VIRTUAL_BACKGROUND)

    @classmethod
    def AUDIO_PROCESSING(cls) -> "AIFeature":
        return cls.NOISE_SUPPRESSION | cls.ECHO_CANCELLATION

    @classmethod
    def DATA_COLLECTION(cls) -> "AIFeature":
        return cls.TRANSCRIPTION | cls.MEETING_INSIGHTS

    @classmethod
    def ALL(cls) -> "AIFeature":
        return (cls.PERSON_DETECTION | cls.FACE_DETECTION |
                cls.SPEAKER_TRACKING | cls.AUTO_FRAMING |
                cls.GESTURE_RECOGNITION | cls.OCCUPANCY_COUNTING |
                cls.NOISE_SUPPRESSION | cls.ECHO_CANCELLATION |
                cls.BACKGROUND_BLUR | cls.VIRTUAL_BACKGROUND |
                cls.TRANSCRIPTION | cls.MEETING_INSIGHTS)


class PrivacyLevel(Enum):
    """Privacy level presets."""
    NORMAL = "normal"           # All AI features enabled
    ENHANCED = "enhanced"       # No data collection, basic AI only
    MAXIMUM = "maximum"         # No video AI, audio processing only
    COMPLETE = "complete"       # All AI disabled


@dataclass
class PrivacySchedule:
    """Scheduled privacy mode window."""
    id: str
    name: str
    start_time: dtime
    end_time: dtime
    days: List[int]  # 0=Monday, 6=Sunday
    privacy_level: PrivacyLevel
    enabled: bool = True

    def is_active(self, now: datetime = None) -> bool:
        """Check if schedule is currently active."""
        if not self.enabled:
            return False

        now = now or datetime.now()
        current_day = now.weekday()
        current_time = now.time()

        if current_day not in self.days:
            return False

        # Handle overnight schedules
        if self.start_time <= self.end_time:
            return self.start_time <= current_time <= self.end_time
        else:
            return current_time >= self.start_time or current_time <= self.end_time


@dataclass
class PrivacyConfig:
    """Privacy mode configuration."""
    # Current privacy level
    level: PrivacyLevel = PrivacyLevel.NORMAL

    # Individually disabled features (overrides level)
    disabled_features: AIFeature = AIFeature.NONE

    # Force enabled features (overrides level)
    force_enabled_features: AIFeature = AIFeature.NONE

    # Scheduled privacy windows
    schedules: List[PrivacySchedule] = field(default_factory=list)

    # Visual indicator settings
    show_indicator: bool = True
    indicator_position: str = "top-right"

    # Data handling
    local_processing_only: bool = False
    no_cloud_upload: bool = False
    auto_delete_local: bool = True
    retention_hours: int = 24

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "disabled_features": self.disabled_features.value,
            "force_enabled_features": self.force_enabled_features.value,
            "schedules": [
                {
                    "id": s.id,
                    "name": s.name,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat(),
                    "days": s.days,
                    "privacy_level": s.privacy_level.value,
                    "enabled": s.enabled,
                }
                for s in self.schedules
            ],
            "show_indicator": self.show_indicator,
            "indicator_position": self.indicator_position,
            "local_processing_only": self.local_processing_only,
            "no_cloud_upload": self.no_cloud_upload,
            "auto_delete_local": self.auto_delete_local,
            "retention_hours": self.retention_hours,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PrivacyConfig":
        schedules = []
        for s in data.get("schedules", []):
            schedules.append(PrivacySchedule(
                id=s["id"],
                name=s["name"],
                start_time=dtime.fromisoformat(s["start_time"]),
                end_time=dtime.fromisoformat(s["end_time"]),
                days=s["days"],
                privacy_level=PrivacyLevel(s["privacy_level"]),
                enabled=s.get("enabled", True),
            ))

        return cls(
            level=PrivacyLevel(data.get("level", "normal")),
            disabled_features=AIFeature(data.get("disabled_features", 0)),
            force_enabled_features=AIFeature(data.get("force_enabled_features", 0)),
            schedules=schedules,
            show_indicator=data.get("show_indicator", True),
            indicator_position=data.get("indicator_position", "top-right"),
            local_processing_only=data.get("local_processing_only", False),
            no_cloud_upload=data.get("no_cloud_upload", False),
            auto_delete_local=data.get("auto_delete_local", True),
            retention_hours=data.get("retention_hours", 24),
        )


# Feature sets for each privacy level
PRIVACY_LEVEL_FEATURES = {
    PrivacyLevel.NORMAL: AIFeature.ALL(),
    PrivacyLevel.ENHANCED: (
        AIFeature.PERSON_DETECTION |
        AIFeature.SPEAKER_TRACKING |
        AIFeature.AUTO_FRAMING |
        AIFeature.NOISE_SUPPRESSION |
        AIFeature.ECHO_CANCELLATION |
        AIFeature.BACKGROUND_BLUR
    ),
    PrivacyLevel.MAXIMUM: (
        AIFeature.NOISE_SUPPRESSION |
        AIFeature.ECHO_CANCELLATION
    ),
    PrivacyLevel.COMPLETE: AIFeature.NONE,
}


class PrivacyModeService:
    """
    Privacy mode management service for PiMeet.

    Controls which AI features are active and manages privacy settings.
    """

    def __init__(
        self,
        config_path: str = "/etc/pimeet/privacy.json",
        config: PrivacyConfig = None,
    ):
        self._config_path = Path(config_path)
        self._config = config or self._load_config()

        self._running = False
        self._listeners: List[Callable[[PrivacyConfig], None]] = []
        self._feature_services: Dict[AIFeature, Any] = {}

        self._effective_level: PrivacyLevel = self._config.level
        self._schedule_task: Optional[asyncio.Task] = None

    def _load_config(self) -> PrivacyConfig:
        """Load configuration from file."""
        if self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    data = json.load(f)
                return PrivacyConfig.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load privacy config: {e}")

        return PrivacyConfig()

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w") as f:
                json.dump(self._config.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save privacy config: {e}")

    async def start(self) -> None:
        """Start privacy mode service."""
        self._running = True
        self._schedule_task = asyncio.create_task(self._schedule_loop())
        await self._apply_privacy_settings()
        logger.info("Privacy mode service started")

    async def stop(self) -> None:
        """Stop privacy mode service."""
        self._running = False
        if self._schedule_task:
            self._schedule_task.cancel()
            try:
                await self._schedule_task
            except asyncio.CancelledError:
                pass
        logger.info("Privacy mode service stopped")

    def register_feature_service(self, feature: AIFeature, service: Any) -> None:
        """Register a feature service to be controlled by privacy mode."""
        self._feature_services[feature] = service

    def add_listener(self, callback: Callable[[PrivacyConfig], None]) -> None:
        """Add listener for privacy config changes."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[PrivacyConfig], None]) -> None:
        """Remove listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    @property
    def config(self) -> PrivacyConfig:
        """Get current privacy configuration."""
        return self._config

    @property
    def effective_level(self) -> PrivacyLevel:
        """Get effective privacy level (considering schedules)."""
        return self._effective_level

    def get_enabled_features(self) -> AIFeature:
        """Get currently enabled AI features."""
        # Start with features for current level
        enabled = PRIVACY_LEVEL_FEATURES.get(self._effective_level, AIFeature.NONE)

        # Remove individually disabled features
        enabled &= ~self._config.disabled_features

        # Add force-enabled features
        enabled |= self._config.force_enabled_features

        return enabled

    def is_feature_enabled(self, feature: AIFeature) -> bool:
        """Check if a specific feature is enabled."""
        enabled = self.get_enabled_features()
        return bool(enabled & feature)

    async def set_privacy_level(self, level: PrivacyLevel) -> None:
        """Set privacy level."""
        self._config.level = level
        self._effective_level = level
        self._save_config()
        await self._apply_privacy_settings()
        self._notify_listeners()
        logger.info(f"Privacy level set to: {level.value}")

    async def set_feature_enabled(self, feature: AIFeature, enabled: bool) -> None:
        """Enable or disable a specific feature."""
        if enabled:
            self._config.disabled_features &= ~feature
            self._config.force_enabled_features |= feature
        else:
            self._config.disabled_features |= feature
            self._config.force_enabled_features &= ~feature

        self._save_config()
        await self._apply_privacy_settings()
        self._notify_listeners()
        logger.info(f"Feature {feature.name} {'enabled' if enabled else 'disabled'}")

    async def toggle_privacy_mode(self) -> PrivacyLevel:
        """Toggle between normal and complete privacy."""
        if self._effective_level == PrivacyLevel.COMPLETE:
            await self.set_privacy_level(PrivacyLevel.NORMAL)
        else:
            await self.set_privacy_level(PrivacyLevel.COMPLETE)
        return self._effective_level

    def add_schedule(self, schedule: PrivacySchedule) -> None:
        """Add a privacy schedule."""
        self._config.schedules.append(schedule)
        self._save_config()
        logger.info(f"Added privacy schedule: {schedule.name}")

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a privacy schedule."""
        for i, schedule in enumerate(self._config.schedules):
            if schedule.id == schedule_id:
                self._config.schedules.pop(i)
                self._save_config()
                logger.info(f"Removed privacy schedule: {schedule_id}")
                return True
        return False

    def update_schedule(self, schedule: PrivacySchedule) -> bool:
        """Update a privacy schedule."""
        for i, s in enumerate(self._config.schedules):
            if s.id == schedule.id:
                self._config.schedules[i] = schedule
                self._save_config()
                return True
        return False

    async def _schedule_loop(self) -> None:
        """Check schedules and apply privacy settings."""
        while self._running:
            try:
                # Check if any schedule is active
                active_schedule = None
                highest_level = self._config.level

                for schedule in self._config.schedules:
                    if schedule.is_active():
                        # Use highest privacy level from active schedules
                        if self._compare_levels(schedule.privacy_level, highest_level) > 0:
                            highest_level = schedule.privacy_level
                            active_schedule = schedule

                # Update effective level if changed
                if highest_level != self._effective_level:
                    old_level = self._effective_level
                    self._effective_level = highest_level
                    await self._apply_privacy_settings()
                    self._notify_listeners()

                    if active_schedule:
                        logger.info(f"Privacy schedule '{active_schedule.name}' activated: {highest_level.value}")
                    else:
                        logger.info(f"Privacy level restored to: {highest_level.value}")

            except Exception as e:
                logger.error(f"Error in schedule loop: {e}")

            await asyncio.sleep(60)  # Check every minute

    def _compare_levels(self, level1: PrivacyLevel, level2: PrivacyLevel) -> int:
        """Compare privacy levels (higher = more private)."""
        order = [PrivacyLevel.NORMAL, PrivacyLevel.ENHANCED, PrivacyLevel.MAXIMUM, PrivacyLevel.COMPLETE]
        return order.index(level1) - order.index(level2)

    async def _apply_privacy_settings(self) -> None:
        """Apply current privacy settings to feature services."""
        enabled_features = self.get_enabled_features()

        for feature, service in self._feature_services.items():
            should_enable = bool(enabled_features & feature)

            try:
                if hasattr(service, "set_enabled"):
                    if asyncio.iscoroutinefunction(service.set_enabled):
                        await service.set_enabled(should_enable)
                    else:
                        service.set_enabled(should_enable)
                    logger.debug(f"Feature {feature.name}: {'enabled' if should_enable else 'disabled'}")
            except Exception as e:
                logger.error(f"Failed to set feature {feature.name}: {e}")

    def _notify_listeners(self) -> None:
        """Notify listeners of config changes."""
        for callback in self._listeners:
            try:
                callback(self._config)
            except Exception as e:
                logger.error(f"Error in privacy listener: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get privacy mode status."""
        enabled_features = self.get_enabled_features()

        return {
            "level": self._effective_level.value,
            "configured_level": self._config.level.value,
            "enabled_features": [
                f.name for f in AIFeature
                if f != AIFeature.NONE and enabled_features & f
            ],
            "disabled_features": [
                f.name for f in AIFeature
                if f != AIFeature.NONE and not (enabled_features & f)
            ],
            "active_schedule": next(
                (s.name for s in self._config.schedules if s.is_active()),
                None
            ),
            "local_processing_only": self._config.local_processing_only,
            "no_cloud_upload": self._config.no_cloud_upload,
        }


class PrivacyIndicator:
    """
    Visual privacy indicator for QML UI.

    Shows current privacy status and provides quick toggle.
    """

    def __init__(self, privacy_service: PrivacyModeService):
        self._service = privacy_service
        self._qml_bridge = None

        # Register for updates
        self._service.add_listener(self._on_privacy_changed)

    def set_qml_bridge(self, bridge) -> None:
        """Set QML bridge for UI updates."""
        self._qml_bridge = bridge
        self._update_indicator()

    def _on_privacy_changed(self, config: PrivacyConfig) -> None:
        """Handle privacy config changes."""
        self._update_indicator()

    def _update_indicator(self) -> None:
        """Update privacy indicator in UI."""
        if not self._qml_bridge:
            return

        status = self._service.get_status()

        indicator_data = {
            "visible": self._service.config.show_indicator,
            "position": self._service.config.indicator_position,
            "level": status["level"],
            "icon": self._get_icon_for_level(self._service.effective_level),
            "color": self._get_color_for_level(self._service.effective_level),
            "tooltip": self._get_tooltip(status),
        }

        self._qml_bridge.update_privacy_indicator(indicator_data)

    def _get_icon_for_level(self, level: PrivacyLevel) -> str:
        """Get icon name for privacy level."""
        icons = {
            PrivacyLevel.NORMAL: "eye",
            PrivacyLevel.ENHANCED: "eye-off",
            PrivacyLevel.MAXIMUM: "shield",
            PrivacyLevel.COMPLETE: "lock",
        }
        return icons.get(level, "eye")

    def _get_color_for_level(self, level: PrivacyLevel) -> str:
        """Get color for privacy level."""
        colors = {
            PrivacyLevel.NORMAL: "#44ff44",
            PrivacyLevel.ENHANCED: "#ffaa00",
            PrivacyLevel.MAXIMUM: "#ff8800",
            PrivacyLevel.COMPLETE: "#ff4444",
        }
        return colors.get(level, "#ffffff")

    def _get_tooltip(self, status: Dict[str, Any]) -> str:
        """Get tooltip text for indicator."""
        level = status["level"]
        enabled = len(status["enabled_features"])
        disabled = len(status["disabled_features"])

        schedule = status.get("active_schedule")
        schedule_text = f" (Schedule: {schedule})" if schedule else ""

        return f"Privacy: {level.title()}{schedule_text}\n{enabled} AI features enabled, {disabled} disabled"

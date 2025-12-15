"""
Meeting quality metrics for PiMeet.

Collects and analyzes meeting quality metrics including audio, video,
and network performance.
"""

import asyncio
import logging
import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Quality level classification."""
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"  # 70-89
    FAIR = "fair"  # 50-69
    POOR = "poor"  # 30-49
    CRITICAL = "critical"  # 0-29


class IssueType(Enum):
    """Types of quality issues."""
    AUDIO_DROPOUT = "audio_dropout"
    AUDIO_ECHO = "audio_echo"
    AUDIO_NOISE = "audio_noise"
    AUDIO_LATENCY = "audio_latency"
    VIDEO_FREEZE = "video_freeze"
    VIDEO_BLUR = "video_blur"
    VIDEO_PIXELATION = "video_pixelation"
    VIDEO_LOW_FPS = "video_low_fps"
    NETWORK_PACKET_LOSS = "network_packet_loss"
    NETWORK_HIGH_LATENCY = "network_high_latency"
    NETWORK_JITTER = "network_jitter"
    BANDWIDTH_LOW = "bandwidth_low"
    CPU_HIGH = "cpu_high"
    MEMORY_HIGH = "memory_high"


@dataclass
class QualityIssue:
    """A detected quality issue."""
    type: IssueType
    severity: QualityLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_seconds: int = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "details": self.details,
        }


@dataclass
class AudioMetrics:
    """Audio quality metrics."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    input_level_db: float = -60  # Input audio level
    output_level_db: float = -60  # Output audio level
    noise_level_db: float = -60  # Background noise level
    echo_return_loss: float = 0  # Echo cancellation effectiveness
    jitter_ms: float = 0  # Audio jitter
    packet_loss_percent: float = 0  # Audio packet loss
    latency_ms: float = 0  # End-to-end audio latency
    sample_rate: int = 48000  # Audio sample rate
    codec: str = "opus"  # Audio codec

    def get_quality_score(self) -> float:
        """Calculate audio quality score (0-100)."""
        score = 100.0

        # Deduct for packet loss
        if self.packet_loss_percent > 5:
            score -= 30
        elif self.packet_loss_percent > 2:
            score -= 15
        elif self.packet_loss_percent > 0.5:
            score -= 5

        # Deduct for jitter
        if self.jitter_ms > 50:
            score -= 25
        elif self.jitter_ms > 30:
            score -= 15
        elif self.jitter_ms > 15:
            score -= 5

        # Deduct for latency
        if self.latency_ms > 300:
            score -= 20
        elif self.latency_ms > 150:
            score -= 10
        elif self.latency_ms > 80:
            score -= 5

        # Deduct for poor echo cancellation
        if self.echo_return_loss < 20:
            score -= 15
        elif self.echo_return_loss < 30:
            score -= 5

        return max(0, min(100, score))

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "input_level_db": self.input_level_db,
            "output_level_db": self.output_level_db,
            "noise_level_db": self.noise_level_db,
            "echo_return_loss": self.echo_return_loss,
            "jitter_ms": self.jitter_ms,
            "packet_loss_percent": self.packet_loss_percent,
            "latency_ms": self.latency_ms,
            "sample_rate": self.sample_rate,
            "codec": self.codec,
            "quality_score": self.get_quality_score(),
        }


@dataclass
class VideoMetrics:
    """Video quality metrics."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    width: int = 1280
    height: int = 720
    fps: float = 30
    bitrate_kbps: int = 2500
    packet_loss_percent: float = 0
    freeze_count: int = 0
    freeze_duration_ms: int = 0
    codec: str = "vp9"
    keyframe_interval: int = 0

    def get_quality_score(self) -> float:
        """Calculate video quality score (0-100)."""
        score = 100.0

        # Resolution scoring
        pixels = self.width * self.height
        if pixels < 640 * 360:
            score -= 30
        elif pixels < 1280 * 720:
            score -= 15
        elif pixels < 1920 * 1080:
            score -= 5

        # FPS scoring
        if self.fps < 15:
            score -= 30
        elif self.fps < 24:
            score -= 15
        elif self.fps < 30:
            score -= 5

        # Packet loss
        if self.packet_loss_percent > 5:
            score -= 25
        elif self.packet_loss_percent > 2:
            score -= 15
        elif self.packet_loss_percent > 0.5:
            score -= 5

        # Freeze penalty
        if self.freeze_count > 10:
            score -= 25
        elif self.freeze_count > 5:
            score -= 15
        elif self.freeze_count > 2:
            score -= 5

        # Bitrate
        if self.bitrate_kbps < 500:
            score -= 20
        elif self.bitrate_kbps < 1000:
            score -= 10
        elif self.bitrate_kbps < 1500:
            score -= 5

        return max(0, min(100, score))

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "width": self.width,
            "height": self.height,
            "resolution": f"{self.width}x{self.height}",
            "fps": self.fps,
            "bitrate_kbps": self.bitrate_kbps,
            "packet_loss_percent": self.packet_loss_percent,
            "freeze_count": self.freeze_count,
            "freeze_duration_ms": self.freeze_duration_ms,
            "codec": self.codec,
            "quality_score": self.get_quality_score(),
        }


@dataclass
class NetworkMetrics:
    """Network quality metrics."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    rtt_ms: float = 0  # Round-trip time
    jitter_ms: float = 0  # Network jitter
    packet_loss_percent: float = 0  # Packet loss
    available_bandwidth_kbps: int = 0  # Available bandwidth
    bytes_sent: int = 0
    bytes_received: int = 0
    connection_type: str = "unknown"  # wifi, ethernet, cellular

    def get_quality_score(self) -> float:
        """Calculate network quality score (0-100)."""
        score = 100.0

        # RTT scoring
        if self.rtt_ms > 500:
            score -= 30
        elif self.rtt_ms > 300:
            score -= 20
        elif self.rtt_ms > 150:
            score -= 10
        elif self.rtt_ms > 80:
            score -= 5

        # Jitter scoring
        if self.jitter_ms > 50:
            score -= 25
        elif self.jitter_ms > 30:
            score -= 15
        elif self.jitter_ms > 15:
            score -= 5

        # Packet loss
        if self.packet_loss_percent > 5:
            score -= 30
        elif self.packet_loss_percent > 2:
            score -= 20
        elif self.packet_loss_percent > 0.5:
            score -= 10

        # Bandwidth
        if self.available_bandwidth_kbps < 500:
            score -= 25
        elif self.available_bandwidth_kbps < 1500:
            score -= 15
        elif self.available_bandwidth_kbps < 3000:
            score -= 5

        return max(0, min(100, score))

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "rtt_ms": self.rtt_ms,
            "jitter_ms": self.jitter_ms,
            "packet_loss_percent": self.packet_loss_percent,
            "available_bandwidth_kbps": self.available_bandwidth_kbps,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "connection_type": self.connection_type,
            "quality_score": self.get_quality_score(),
        }


@dataclass
class QualitySnapshot:
    """Complete quality snapshot at a point in time."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    audio: Optional[AudioMetrics] = None
    video: Optional[VideoMetrics] = None
    network: Optional[NetworkMetrics] = None
    overall_score: float = 0
    level: QualityLevel = QualityLevel.GOOD
    issues: List[QualityIssue] = field(default_factory=list)

    def calculate_overall_score(self) -> float:
        """Calculate weighted overall quality score."""
        scores = []
        weights = []

        if self.audio:
            scores.append(self.audio.get_quality_score())
            weights.append(0.35)  # 35% weight for audio

        if self.video:
            scores.append(self.video.get_quality_score())
            weights.append(0.35)  # 35% weight for video

        if self.network:
            scores.append(self.network.get_quality_score())
            weights.append(0.30)  # 30% weight for network

        if not scores:
            return 0

        # Weighted average
        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        self.overall_score = weighted_sum / total_weight if total_weight > 0 else 0

        # Determine quality level
        if self.overall_score >= 90:
            self.level = QualityLevel.EXCELLENT
        elif self.overall_score >= 70:
            self.level = QualityLevel.GOOD
        elif self.overall_score >= 50:
            self.level = QualityLevel.FAIR
        elif self.overall_score >= 30:
            self.level = QualityLevel.POOR
        else:
            self.level = QualityLevel.CRITICAL

        return self.overall_score

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "audio": self.audio.to_dict() if self.audio else None,
            "video": self.video.to_dict() if self.video else None,
            "network": self.network.to_dict() if self.network else None,
            "overall_score": self.overall_score,
            "level": self.level.value,
            "issues": [i.to_dict() for i in self.issues],
        }


class QualityMetricsCollector:
    """Collects and analyzes meeting quality metrics."""

    def __init__(
        self,
        collection_interval: float = 1.0,
        history_size: int = 3600,  # 1 hour at 1 second intervals
    ):
        """
        Initialize quality metrics collector.

        Args:
            collection_interval: Seconds between collections
            history_size: Number of snapshots to keep in history
        """
        self._interval = collection_interval
        self._history_size = history_size

        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Metrics history
        self._snapshots: deque = deque(maxlen=history_size)
        self._issues: List[QualityIssue] = []

        # Current metrics
        self._current_audio: Optional[AudioMetrics] = None
        self._current_video: Optional[VideoMetrics] = None
        self._current_network: Optional[NetworkMetrics] = None

        # Callbacks
        self._on_quality_change: List[Callable[[QualitySnapshot], None]] = []
        self._on_issue_detected: List[Callable[[QualityIssue], None]] = []

        # Thresholds for issue detection
        self._thresholds = {
            "audio_packet_loss": 2.0,
            "audio_jitter": 30,
            "audio_latency": 150,
            "video_packet_loss": 2.0,
            "video_fps_min": 20,
            "video_freeze_max": 5,
            "network_rtt": 200,
            "network_jitter": 30,
            "network_packet_loss": 2.0,
        }

        # For tracking issue duration
        self._active_issues: Dict[IssueType, datetime] = {}

    async def start(self) -> None:
        """Start collecting metrics."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
        logger.info("Quality metrics collector started")

    async def stop(self) -> None:
        """Stop collecting metrics."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Quality metrics collector stopped")

    async def _collection_loop(self) -> None:
        """Main collection loop."""
        while self._running:
            try:
                snapshot = await self._collect_snapshot()
                self._snapshots.append(snapshot)

                # Detect issues
                issues = self._detect_issues(snapshot)
                for issue in issues:
                    self._issues.append(issue)
                    self._emit_issue_detected(issue)

                snapshot.issues = issues

                # Emit quality change callback
                self._emit_quality_change(snapshot)

            except Exception as e:
                logger.error(f"Quality collection error: {e}")

            await asyncio.sleep(self._interval)

    async def _collect_snapshot(self) -> QualitySnapshot:
        """Collect current quality snapshot."""
        snapshot = QualitySnapshot()

        # Use current metrics if available
        if self._current_audio:
            snapshot.audio = self._current_audio
        if self._current_video:
            snapshot.video = self._current_video
        if self._current_network:
            snapshot.network = self._current_network

        snapshot.calculate_overall_score()
        return snapshot

    def update_audio_metrics(self, metrics: AudioMetrics) -> None:
        """Update current audio metrics."""
        self._current_audio = metrics

    def update_video_metrics(self, metrics: VideoMetrics) -> None:
        """Update current video metrics."""
        self._current_video = metrics

    def update_network_metrics(self, metrics: NetworkMetrics) -> None:
        """Update current network metrics."""
        self._current_network = metrics

    def _detect_issues(self, snapshot: QualitySnapshot) -> List[QualityIssue]:
        """Detect quality issues from snapshot."""
        issues = []
        now = datetime.utcnow()

        # Audio issues
        if snapshot.audio:
            audio = snapshot.audio

            if audio.packet_loss_percent > self._thresholds["audio_packet_loss"]:
                issues.append(self._create_issue(
                    IssueType.AUDIO_DROPOUT,
                    audio.packet_loss_percent,
                    self._thresholds["audio_packet_loss"],
                    f"Audio packet loss: {audio.packet_loss_percent:.1f}%",
                ))

            if audio.jitter_ms > self._thresholds["audio_jitter"]:
                issues.append(self._create_issue(
                    IssueType.AUDIO_LATENCY,
                    audio.jitter_ms,
                    self._thresholds["audio_jitter"],
                    f"High audio jitter: {audio.jitter_ms:.0f}ms",
                ))

            if audio.latency_ms > self._thresholds["audio_latency"]:
                issues.append(self._create_issue(
                    IssueType.AUDIO_LATENCY,
                    audio.latency_ms,
                    self._thresholds["audio_latency"],
                    f"High audio latency: {audio.latency_ms:.0f}ms",
                ))

            if audio.echo_return_loss < 20:
                issues.append(self._create_issue(
                    IssueType.AUDIO_ECHO,
                    20 - audio.echo_return_loss,
                    0,
                    f"Poor echo cancellation: {audio.echo_return_loss:.0f}dB",
                ))

        # Video issues
        if snapshot.video:
            video = snapshot.video

            if video.packet_loss_percent > self._thresholds["video_packet_loss"]:
                issues.append(self._create_issue(
                    IssueType.VIDEO_PIXELATION,
                    video.packet_loss_percent,
                    self._thresholds["video_packet_loss"],
                    f"Video packet loss: {video.packet_loss_percent:.1f}%",
                ))

            if video.fps < self._thresholds["video_fps_min"]:
                issues.append(self._create_issue(
                    IssueType.VIDEO_LOW_FPS,
                    self._thresholds["video_fps_min"] - video.fps,
                    0,
                    f"Low video framerate: {video.fps:.0f} FPS",
                ))

            if video.freeze_count > self._thresholds["video_freeze_max"]:
                issues.append(self._create_issue(
                    IssueType.VIDEO_FREEZE,
                    video.freeze_count,
                    self._thresholds["video_freeze_max"],
                    f"Video freezes detected: {video.freeze_count}",
                ))

        # Network issues
        if snapshot.network:
            network = snapshot.network

            if network.rtt_ms > self._thresholds["network_rtt"]:
                issues.append(self._create_issue(
                    IssueType.NETWORK_HIGH_LATENCY,
                    network.rtt_ms,
                    self._thresholds["network_rtt"],
                    f"High network latency: {network.rtt_ms:.0f}ms",
                ))

            if network.jitter_ms > self._thresholds["network_jitter"]:
                issues.append(self._create_issue(
                    IssueType.NETWORK_JITTER,
                    network.jitter_ms,
                    self._thresholds["network_jitter"],
                    f"High network jitter: {network.jitter_ms:.0f}ms",
                ))

            if network.packet_loss_percent > self._thresholds["network_packet_loss"]:
                issues.append(self._create_issue(
                    IssueType.NETWORK_PACKET_LOSS,
                    network.packet_loss_percent,
                    self._thresholds["network_packet_loss"],
                    f"Network packet loss: {network.packet_loss_percent:.1f}%",
                ))

            if network.available_bandwidth_kbps < 1000:
                issues.append(self._create_issue(
                    IssueType.BANDWIDTH_LOW,
                    1000 - network.available_bandwidth_kbps,
                    0,
                    f"Low bandwidth: {network.available_bandwidth_kbps}kbps",
                ))

        return issues

    def _create_issue(
        self,
        issue_type: IssueType,
        value: float,
        threshold: float,
        message: str,
    ) -> QualityIssue:
        """Create a quality issue with severity calculation."""
        # Calculate severity based on how much threshold is exceeded
        excess = value - threshold if threshold > 0 else value
        excess_percent = (excess / threshold * 100) if threshold > 0 else excess

        if excess_percent > 100 or value > threshold * 2:
            severity = QualityLevel.CRITICAL
        elif excess_percent > 50:
            severity = QualityLevel.POOR
        elif excess_percent > 25:
            severity = QualityLevel.FAIR
        else:
            severity = QualityLevel.GOOD

        # Track issue duration
        if issue_type not in self._active_issues:
            self._active_issues[issue_type] = datetime.utcnow()

        duration = int((datetime.utcnow() - self._active_issues[issue_type]).total_seconds())

        return QualityIssue(
            type=issue_type,
            severity=severity,
            message=message,
            duration_seconds=duration,
            details={"value": value, "threshold": threshold},
        )

    # Callbacks
    def on_quality_change(self, callback: Callable[[QualitySnapshot], None]) -> None:
        """Register callback for quality changes."""
        self._on_quality_change.append(callback)

    def on_issue_detected(self, callback: Callable[[QualityIssue], None]) -> None:
        """Register callback for issue detection."""
        self._on_issue_detected.append(callback)

    def _emit_quality_change(self, snapshot: QualitySnapshot) -> None:
        for callback in self._on_quality_change:
            try:
                callback(snapshot)
            except Exception as e:
                logger.error(f"Quality change callback error: {e}")

    def _emit_issue_detected(self, issue: QualityIssue) -> None:
        for callback in self._on_issue_detected:
            try:
                callback(issue)
            except Exception as e:
                logger.error(f"Issue detected callback error: {e}")

    # Analytics
    def get_current_quality(self) -> Optional[QualitySnapshot]:
        """Get current quality snapshot."""
        if self._snapshots:
            return self._snapshots[-1]
        return None

    def get_average_quality(
        self,
        duration_seconds: int = 60,
    ) -> Dict[str, float]:
        """
        Get average quality metrics over a duration.

        Args:
            duration_seconds: Duration to average over

        Returns:
            Dictionary of average metrics
        """
        cutoff = datetime.utcnow() - timedelta(seconds=duration_seconds)
        recent = [s for s in self._snapshots if s.timestamp >= cutoff]

        if not recent:
            return {}

        audio_scores = [s.audio.get_quality_score() for s in recent if s.audio]
        video_scores = [s.video.get_quality_score() for s in recent if s.video]
        network_scores = [s.network.get_quality_score() for s in recent if s.network]
        overall_scores = [s.overall_score for s in recent]

        return {
            "audio_avg": statistics.mean(audio_scores) if audio_scores else 0,
            "video_avg": statistics.mean(video_scores) if video_scores else 0,
            "network_avg": statistics.mean(network_scores) if network_scores else 0,
            "overall_avg": statistics.mean(overall_scores) if overall_scores else 0,
            "sample_count": len(recent),
        }

    def get_quality_history(
        self,
        duration_seconds: int = 300,
    ) -> List[Dict[str, Any]]:
        """
        Get quality history over a duration.

        Args:
            duration_seconds: Duration of history to return

        Returns:
            List of quality snapshots
        """
        cutoff = datetime.utcnow() - timedelta(seconds=duration_seconds)
        return [s.to_dict() for s in self._snapshots if s.timestamp >= cutoff]

    def get_issues(
        self,
        duration_seconds: int = 300,
        min_severity: Optional[QualityLevel] = None,
    ) -> List[QualityIssue]:
        """
        Get issues detected over a duration.

        Args:
            duration_seconds: Duration to look back
            min_severity: Minimum severity filter

        Returns:
            List of quality issues
        """
        cutoff = datetime.utcnow() - timedelta(seconds=duration_seconds)
        issues = [i for i in self._issues if i.timestamp >= cutoff]

        if min_severity:
            severity_order = [
                QualityLevel.EXCELLENT,
                QualityLevel.GOOD,
                QualityLevel.FAIR,
                QualityLevel.POOR,
                QualityLevel.CRITICAL,
            ]
            min_index = severity_order.index(min_severity)
            issues = [i for i in issues if severity_order.index(i.severity) >= min_index]

        return issues

    def get_summary(self) -> Dict[str, Any]:
        """Get quality metrics summary."""
        current = self.get_current_quality()
        avg = self.get_average_quality(60)
        issues = self.get_issues(300)

        return {
            "current_score": current.overall_score if current else 0,
            "current_level": current.level.value if current else "unknown",
            "average_60s": avg,
            "issues_5m": len(issues),
            "issues_by_severity": {
                "critical": len([i for i in issues if i.severity == QualityLevel.CRITICAL]),
                "poor": len([i for i in issues if i.severity == QualityLevel.POOR]),
                "fair": len([i for i in issues if i.severity == QualityLevel.FAIR]),
            },
        }


class MeetingQualityService:
    """High-level service for meeting quality management."""

    def __init__(self):
        self._collector = QualityMetricsCollector()
        self._meeting_id: Optional[str] = None
        self._meeting_start: Optional[datetime] = None
        self._meeting_quality_log: List[Dict[str, Any]] = []

    async def start_monitoring(self, meeting_id: str) -> None:
        """Start monitoring quality for a meeting."""
        self._meeting_id = meeting_id
        self._meeting_start = datetime.utcnow()
        self._meeting_quality_log = []
        await self._collector.start()

        # Register callback to log quality periodically
        self._collector.on_quality_change(self._log_quality)
        logger.info(f"Started quality monitoring for meeting: {meeting_id}")

    async def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return meeting quality report."""
        await self._collector.stop()

        report = self._generate_report()
        logger.info(f"Stopped quality monitoring for meeting: {self._meeting_id}")

        self._meeting_id = None
        self._meeting_start = None

        return report

    def _log_quality(self, snapshot: QualitySnapshot) -> None:
        """Log quality snapshot."""
        self._meeting_quality_log.append({
            "timestamp": snapshot.timestamp.isoformat(),
            "score": snapshot.overall_score,
            "level": snapshot.level.value,
        })

    def _generate_report(self) -> Dict[str, Any]:
        """Generate meeting quality report."""
        if not self._meeting_start or not self._meeting_quality_log:
            return {}

        scores = [entry["score"] for entry in self._meeting_quality_log]
        issues = self._collector.get_issues(
            int((datetime.utcnow() - self._meeting_start).total_seconds())
        )

        return {
            "meeting_id": self._meeting_id,
            "duration_seconds": int((datetime.utcnow() - self._meeting_start).total_seconds()),
            "quality_summary": {
                "average_score": statistics.mean(scores) if scores else 0,
                "min_score": min(scores) if scores else 0,
                "max_score": max(scores) if scores else 0,
                "score_std_dev": statistics.stdev(scores) if len(scores) > 1 else 0,
            },
            "time_in_quality_levels": self._calculate_time_in_levels(),
            "total_issues": len(issues),
            "issues_by_type": self._group_issues_by_type(issues),
            "recommendations": self._generate_recommendations(issues),
        }

    def _calculate_time_in_levels(self) -> Dict[str, int]:
        """Calculate time spent in each quality level."""
        levels = {
            "excellent": 0,
            "good": 0,
            "fair": 0,
            "poor": 0,
            "critical": 0,
        }

        for entry in self._meeting_quality_log:
            levels[entry["level"]] += 1  # Each entry represents ~1 second

        return levels

    def _group_issues_by_type(self, issues: List[QualityIssue]) -> Dict[str, int]:
        """Group issues by type."""
        by_type: Dict[str, int] = {}
        for issue in issues:
            key = issue.type.value
            by_type[key] = by_type.get(key, 0) + 1
        return by_type

    def _generate_recommendations(self, issues: List[QualityIssue]) -> List[str]:
        """Generate recommendations based on issues."""
        recommendations = []
        issue_types = set(i.type for i in issues)

        if IssueType.NETWORK_HIGH_LATENCY in issue_types:
            recommendations.append("Network latency was high. Consider using a wired connection.")

        if IssueType.NETWORK_PACKET_LOSS in issue_types:
            recommendations.append("Packet loss detected. Check network stability.")

        if IssueType.BANDWIDTH_LOW in issue_types:
            recommendations.append("Low bandwidth detected. Close other applications using network.")

        if IssueType.AUDIO_ECHO in issue_types:
            recommendations.append("Audio echo detected. Use headphones or adjust speaker volume.")

        if IssueType.VIDEO_LOW_FPS in issue_types:
            recommendations.append("Low video framerate. Check CPU usage and close resource-intensive apps.")

        if IssueType.VIDEO_FREEZE in issue_types:
            recommendations.append("Video freezes detected. Check network stability and bandwidth.")

        if not recommendations:
            recommendations.append("Meeting quality was good. No specific recommendations.")

        return recommendations

    @property
    def collector(self) -> QualityMetricsCollector:
        """Get the quality collector."""
        return self._collector

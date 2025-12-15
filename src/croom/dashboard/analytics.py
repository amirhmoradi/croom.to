"""
Analytics and reporting for Croom dashboard.

Provides usage statistics, trend analysis, and report generation.
"""

import asyncio
import csv
import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TimeRange(Enum):
    """Predefined time ranges for analytics."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"


class MetricType(Enum):
    """Types of metrics for analytics."""
    MEETING_COUNT = "meeting_count"
    MEETING_DURATION = "meeting_duration"
    ROOM_UTILIZATION = "room_utilization"
    PARTICIPANT_COUNT = "participant_count"
    PLATFORM_USAGE = "platform_usage"
    DEVICE_UPTIME = "device_uptime"
    ERROR_COUNT = "error_count"
    AI_DETECTIONS = "ai_detections"


class ReportFormat(Enum):
    """Report output formats."""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"


@dataclass
class MeetingRecord:
    """Record of a meeting session."""
    id: str
    device_id: str
    room_name: str
    platform: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: float = 0
    participant_count: int = 0
    recording_enabled: bool = False
    ai_features_used: List[str] = field(default_factory=list)
    quality_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "room_name": self.room_name,
            "platform": self.platform,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": self.duration_seconds,
            "participant_count": self.participant_count,
            "recording_enabled": self.recording_enabled,
            "ai_features_used": self.ai_features_used,
            "quality_score": self.quality_score,
        }


@dataclass
class UsageStats:
    """Usage statistics summary."""
    period_start: datetime
    period_end: datetime
    total_meetings: int = 0
    total_duration_hours: float = 0
    avg_meeting_duration_minutes: float = 0
    total_participants: int = 0
    avg_participants_per_meeting: float = 0
    busiest_hour: Optional[int] = None
    busiest_day: Optional[str] = None
    platform_breakdown: Dict[str, int] = field(default_factory=dict)
    room_breakdown: Dict[str, int] = field(default_factory=dict)
    utilization_percent: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_meetings": self.total_meetings,
            "total_duration_hours": round(self.total_duration_hours, 2),
            "avg_meeting_duration_minutes": round(self.avg_meeting_duration_minutes, 1),
            "total_participants": self.total_participants,
            "avg_participants_per_meeting": round(self.avg_participants_per_meeting, 1),
            "busiest_hour": self.busiest_hour,
            "busiest_day": self.busiest_day,
            "platform_breakdown": self.platform_breakdown,
            "room_breakdown": self.room_breakdown,
            "utilization_percent": round(self.utilization_percent, 1),
        }


@dataclass
class TrendData:
    """Trend data point."""
    timestamp: datetime
    value: float
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "label": self.label,
        }


@dataclass
class Report:
    """Generated report."""
    id: str
    name: str
    report_type: str
    format: ReportFormat
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    data: Any = None
    file_path: Optional[str] = None
    file_size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "report_type": self.report_type,
            "format": self.format.value,
            "created_at": self.created_at.isoformat(),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
        }


class MeetingTracker:
    """Tracks meeting sessions and collects statistics."""

    def __init__(self):
        self._meetings: Dict[str, MeetingRecord] = {}
        self._completed_meetings: List[MeetingRecord] = []
        self._max_history = 10000

    def start_meeting(
        self,
        meeting_id: str,
        device_id: str,
        room_name: str,
        platform: str,
    ) -> MeetingRecord:
        """Record meeting start."""
        meeting = MeetingRecord(
            id=meeting_id,
            device_id=device_id,
            room_name=room_name,
            platform=platform,
            started_at=datetime.now(timezone.utc),
        )
        self._meetings[meeting_id] = meeting
        logger.info(f"Meeting started: {meeting_id} in {room_name}")
        return meeting

    def end_meeting(self, meeting_id: str) -> Optional[MeetingRecord]:
        """Record meeting end."""
        meeting = self._meetings.pop(meeting_id, None)
        if not meeting:
            return None

        meeting.ended_at = datetime.now(timezone.utc)
        meeting.duration_seconds = (meeting.ended_at - meeting.started_at).total_seconds()

        self._completed_meetings.append(meeting)

        # Trim history
        while len(self._completed_meetings) > self._max_history:
            self._completed_meetings.pop(0)

        logger.info(f"Meeting ended: {meeting_id}, duration: {meeting.duration_seconds}s")
        return meeting

    def update_meeting(
        self,
        meeting_id: str,
        participant_count: Optional[int] = None,
        ai_features: Optional[List[str]] = None,
        quality_score: Optional[float] = None,
    ) -> Optional[MeetingRecord]:
        """Update meeting information."""
        meeting = self._meetings.get(meeting_id)
        if not meeting:
            return None

        if participant_count is not None:
            meeting.participant_count = max(meeting.participant_count, participant_count)

        if ai_features:
            meeting.ai_features_used.extend(ai_features)
            meeting.ai_features_used = list(set(meeting.ai_features_used))

        if quality_score is not None:
            meeting.quality_score = quality_score

        return meeting

    def get_active_meetings(self) -> List[MeetingRecord]:
        """Get currently active meetings."""
        return list(self._meetings.values())

    def get_meeting_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        device_id: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 100,
    ) -> List[MeetingRecord]:
        """Get meeting history with filters."""
        meetings = self._completed_meetings.copy()

        if start_time:
            meetings = [m for m in meetings if m.started_at >= start_time]

        if end_time:
            meetings = [m for m in meetings if m.started_at <= end_time]

        if device_id:
            meetings = [m for m in meetings if m.device_id == device_id]

        if platform:
            meetings = [m for m in meetings if m.platform == platform]

        meetings.sort(key=lambda m: m.started_at, reverse=True)
        return meetings[:limit]


class AnalyticsEngine:
    """Engine for computing analytics and statistics."""

    def __init__(self, meeting_tracker: MeetingTracker):
        self._tracker = meeting_tracker
        self._working_hours = (8, 18)  # 8am to 6pm

    def get_usage_stats(
        self,
        time_range: TimeRange = TimeRange.WEEK,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> UsageStats:
        """
        Calculate usage statistics for a time period.

        Args:
            time_range: Predefined time range
            start_time: Custom start time (for CUSTOM range)
            end_time: Custom end time (for CUSTOM range)

        Returns:
            UsageStats with computed statistics
        """
        # Determine time period
        now = datetime.now(timezone.utc)

        if time_range == TimeRange.CUSTOM and start_time and end_time:
            period_start = start_time
            period_end = end_time
        else:
            period_end = now
            if time_range == TimeRange.HOUR:
                period_start = now - timedelta(hours=1)
            elif time_range == TimeRange.DAY:
                period_start = now - timedelta(days=1)
            elif time_range == TimeRange.WEEK:
                period_start = now - timedelta(weeks=1)
            elif time_range == TimeRange.MONTH:
                period_start = now - timedelta(days=30)
            elif time_range == TimeRange.QUARTER:
                period_start = now - timedelta(days=90)
            elif time_range == TimeRange.YEAR:
                period_start = now - timedelta(days=365)
            else:
                period_start = now - timedelta(weeks=1)

        # Get meetings in period
        meetings = self._tracker.get_meeting_history(
            start_time=period_start,
            end_time=period_end,
            limit=10000,
        )

        stats = UsageStats(
            period_start=period_start,
            period_end=period_end,
        )

        if not meetings:
            return stats

        # Compute statistics
        stats.total_meetings = len(meetings)

        total_duration = sum(m.duration_seconds for m in meetings)
        stats.total_duration_hours = total_duration / 3600

        stats.avg_meeting_duration_minutes = (total_duration / len(meetings)) / 60

        stats.total_participants = sum(m.participant_count for m in meetings)
        stats.avg_participants_per_meeting = stats.total_participants / len(meetings)

        # Busiest hour
        hour_counts = {}
        for meeting in meetings:
            hour = meeting.started_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        if hour_counts:
            stats.busiest_hour = max(hour_counts, key=hour_counts.get)

        # Busiest day
        day_counts = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for meeting in meetings:
            day = days[meeting.started_at.weekday()]
            day_counts[day] = day_counts.get(day, 0) + 1

        if day_counts:
            stats.busiest_day = max(day_counts, key=day_counts.get)

        # Platform breakdown
        for meeting in meetings:
            platform = meeting.platform or "Unknown"
            stats.platform_breakdown[platform] = stats.platform_breakdown.get(platform, 0) + 1

        # Room breakdown
        for meeting in meetings:
            room = meeting.room_name or "Unknown"
            stats.room_breakdown[room] = stats.room_breakdown.get(room, 0) + 1

        # Calculate utilization
        stats.utilization_percent = self._calculate_utilization(
            meetings, period_start, period_end
        )

        return stats

    def _calculate_utilization(
        self,
        meetings: List[MeetingRecord],
        start: datetime,
        end: datetime,
    ) -> float:
        """Calculate room utilization percentage."""
        # Calculate available hours (working hours only)
        total_days = (end - start).days + 1
        working_hours_per_day = self._working_hours[1] - self._working_hours[0]
        total_available_hours = total_days * working_hours_per_day

        if total_available_hours <= 0:
            return 0

        # Calculate used hours
        used_hours = sum(m.duration_seconds for m in meetings) / 3600

        return min(100, (used_hours / total_available_hours) * 100)

    def get_trend(
        self,
        metric: MetricType,
        time_range: TimeRange = TimeRange.WEEK,
        granularity: str = "hour",
    ) -> List[TrendData]:
        """
        Get trend data for a metric.

        Args:
            metric: Metric to track
            time_range: Time period
            granularity: Data point granularity (hour, day, week)

        Returns:
            List of trend data points
        """
        now = datetime.now(timezone.utc)

        # Determine period
        if time_range == TimeRange.DAY:
            period_start = now - timedelta(days=1)
            delta = timedelta(hours=1)
        elif time_range == TimeRange.WEEK:
            period_start = now - timedelta(weeks=1)
            delta = timedelta(hours=6) if granularity == "hour" else timedelta(days=1)
        elif time_range == TimeRange.MONTH:
            period_start = now - timedelta(days=30)
            delta = timedelta(days=1)
        else:
            period_start = now - timedelta(weeks=1)
            delta = timedelta(days=1)

        meetings = self._tracker.get_meeting_history(
            start_time=period_start,
            limit=10000,
        )

        trend_data = []
        current = period_start

        while current < now:
            next_time = current + delta

            # Filter meetings for this bucket
            bucket_meetings = [
                m for m in meetings
                if current <= m.started_at < next_time
            ]

            value = 0
            if metric == MetricType.MEETING_COUNT:
                value = len(bucket_meetings)
            elif metric == MetricType.MEETING_DURATION:
                value = sum(m.duration_seconds for m in bucket_meetings) / 60
            elif metric == MetricType.PARTICIPANT_COUNT:
                value = sum(m.participant_count for m in bucket_meetings)

            trend_data.append(TrendData(
                timestamp=current,
                value=value,
            ))

            current = next_time

        return trend_data

    def get_platform_distribution(
        self,
        time_range: TimeRange = TimeRange.MONTH,
    ) -> Dict[str, float]:
        """Get meeting platform usage distribution."""
        stats = self.get_usage_stats(time_range)
        total = sum(stats.platform_breakdown.values())

        if total == 0:
            return {}

        return {
            platform: (count / total) * 100
            for platform, count in stats.platform_breakdown.items()
        }

    def get_peak_hours(
        self,
        time_range: TimeRange = TimeRange.MONTH,
    ) -> Dict[int, int]:
        """Get meeting counts by hour of day."""
        now = datetime.now(timezone.utc)

        if time_range == TimeRange.WEEK:
            period_start = now - timedelta(weeks=1)
        elif time_range == TimeRange.MONTH:
            period_start = now - timedelta(days=30)
        else:
            period_start = now - timedelta(days=30)

        meetings = self._tracker.get_meeting_history(
            start_time=period_start,
            limit=10000,
        )

        hour_counts = {h: 0 for h in range(24)}
        for meeting in meetings:
            hour = meeting.started_at.hour
            hour_counts[hour] += 1

        return hour_counts


class ReportGenerator:
    """Generates reports in various formats."""

    def __init__(self, analytics: AnalyticsEngine):
        self._analytics = analytics
        self._reports: Dict[str, Report] = {}

    async def generate_usage_report(
        self,
        time_range: TimeRange,
        format: ReportFormat = ReportFormat.JSON,
        name: str = "Usage Report",
    ) -> Report:
        """Generate a usage report."""
        import uuid

        stats = self._analytics.get_usage_stats(time_range)
        trend = self._analytics.get_trend(MetricType.MEETING_COUNT, time_range)

        report_data = {
            "summary": stats.to_dict(),
            "trends": [t.to_dict() for t in trend],
            "platform_distribution": self._analytics.get_platform_distribution(time_range),
            "peak_hours": self._analytics.get_peak_hours(time_range),
        }

        report_id = str(uuid.uuid4())[:8]
        report = Report(
            id=report_id,
            name=name,
            report_type="usage",
            format=format,
            period_start=stats.period_start,
            period_end=stats.period_end,
            data=report_data,
        )

        self._reports[report_id] = report
        return report

    def export_to_json(self, report: Report) -> str:
        """Export report to JSON."""
        return json.dumps(report.data, indent=2, default=str)

    def export_to_csv(self, report: Report) -> str:
        """Export report to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Summary section
        writer.writerow(["Summary"])
        summary = report.data.get("summary", {})
        for key, value in summary.items():
            if not isinstance(value, dict):
                writer.writerow([key, value])

        writer.writerow([])

        # Trends section
        writer.writerow(["Trends"])
        writer.writerow(["Timestamp", "Value"])
        for trend in report.data.get("trends", []):
            writer.writerow([trend["timestamp"], trend["value"]])

        writer.writerow([])

        # Platform distribution
        writer.writerow(["Platform Distribution"])
        writer.writerow(["Platform", "Percentage"])
        for platform, pct in report.data.get("platform_distribution", {}).items():
            writer.writerow([platform, f"{pct:.1f}%"])

        return output.getvalue()

    def export_to_html(self, report: Report) -> str:
        """Export report to HTML."""
        summary = report.data.get("summary", {})
        trends = report.data.get("trends", [])

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{report.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 8px; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #0066cc; color: white; }}
    </style>
</head>
<body>
    <h1>{report.name}</h1>
    <p>Period: {summary.get('period_start', '')} to {summary.get('period_end', '')}</p>

    <div class="summary">
        <h2>Summary</h2>
        <div class="metric">
            <div class="metric-value">{summary.get('total_meetings', 0)}</div>
            <div class="metric-label">Total Meetings</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary.get('total_duration_hours', 0):.1f}h</div>
            <div class="metric-label">Total Duration</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary.get('avg_meeting_duration_minutes', 0):.0f}m</div>
            <div class="metric-label">Avg Meeting Duration</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary.get('utilization_percent', 0):.1f}%</div>
            <div class="metric-label">Utilization</div>
        </div>
    </div>

    <h2>Platform Usage</h2>
    <table>
        <tr><th>Platform</th><th>Meetings</th></tr>
"""

        for platform, count in summary.get('platform_breakdown', {}).items():
            html += f"        <tr><td>{platform}</td><td>{count}</td></tr>\n"

        html += """
    </table>

    <h2>Peak Hours</h2>
    <table>
        <tr><th>Hour</th><th>Meetings</th></tr>
"""

        peak_hours = report.data.get('peak_hours', {})
        for hour in sorted(peak_hours.keys()):
            if peak_hours[hour] > 0:
                html += f"        <tr><td>{hour}:00</td><td>{peak_hours[hour]}</td></tr>\n"

        html += """
    </table>

    <footer>
        <p>Generated: """ + report.created_at.isoformat() + """</p>
    </footer>
</body>
</html>
"""
        return html

    def get_report(self, report_id: str) -> Optional[Report]:
        """Get report by ID."""
        return self._reports.get(report_id)

    def list_reports(self, limit: int = 50) -> List[Report]:
        """List all reports."""
        reports = list(self._reports.values())
        reports.sort(key=lambda r: r.created_at, reverse=True)
        return reports[:limit]


class ScheduledReportService:
    """Service for scheduling recurring reports."""

    def __init__(self, generator: ReportGenerator):
        self._generator = generator
        self._schedules: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[Report], None]] = []

    async def start(self) -> None:
        """Start the scheduling service."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._schedule_loop())
        logger.info("Scheduled report service started")

    async def stop(self) -> None:
        """Stop the scheduling service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduled report service stopped")

    def add_schedule(
        self,
        schedule_id: str,
        report_type: str,
        time_range: TimeRange,
        format: ReportFormat,
        interval_hours: int = 24,
        name: str = "",
    ) -> None:
        """Add a report schedule."""
        self._schedules[schedule_id] = {
            "report_type": report_type,
            "time_range": time_range,
            "format": format,
            "interval_hours": interval_hours,
            "name": name or f"Scheduled {report_type}",
            "last_run": None,
        }
        logger.info(f"Added report schedule: {schedule_id}")

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a report schedule."""
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            return True
        return False

    def on_report_generated(self, callback: Callable[[Report], None]) -> None:
        """Register callback for generated reports."""
        self._callbacks.append(callback)

    async def _schedule_loop(self) -> None:
        """Main scheduling loop."""
        while self._running:
            try:
                now = datetime.now(timezone.utc)

                for schedule_id, schedule in list(self._schedules.items()):
                    last_run = schedule.get("last_run")
                    interval = timedelta(hours=schedule["interval_hours"])

                    if last_run is None or (now - last_run) >= interval:
                        await self._run_scheduled_report(schedule_id, schedule)

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Schedule loop error: {e}")
                await asyncio.sleep(60)

    async def _run_scheduled_report(
        self,
        schedule_id: str,
        schedule: Dict[str, Any],
    ) -> None:
        """Run a scheduled report."""
        try:
            report = await self._generator.generate_usage_report(
                time_range=schedule["time_range"],
                format=schedule["format"],
                name=schedule["name"],
            )

            self._schedules[schedule_id]["last_run"] = datetime.now(timezone.utc)

            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(report)
                except Exception as e:
                    logger.error(f"Report callback error: {e}")

            logger.info(f"Generated scheduled report: {schedule_id}")

        except Exception as e:
            logger.error(f"Failed to generate scheduled report {schedule_id}: {e}")

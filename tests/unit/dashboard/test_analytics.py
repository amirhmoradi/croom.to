"""
Tests for croom.dashboard.analytics module.
"""

import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

import pytest

from croom.dashboard.analytics import (
    TimeRange,
    MetricType,
    ReportFormat,
    MeetingRecord,
    UsageStats,
    TrendData,
    Report,
    MeetingTracker,
    AnalyticsEngine,
    ReportGenerator,
    ScheduledReportService,
)


class TestTimeRange:
    """Tests for TimeRange enum."""

    def test_values(self):
        """Test time range enum values."""
        assert TimeRange.DAY.value == "day"
        assert TimeRange.WEEK.value == "week"
        assert TimeRange.MONTH.value == "month"
        assert TimeRange.QUARTER.value == "quarter"
        assert TimeRange.YEAR.value == "year"


class TestMetricType:
    """Tests for MetricType enum."""

    def test_values(self):
        """Test metric type enum values."""
        assert MetricType.MEETING_COUNT.value == "meeting_count"
        assert MetricType.MEETING_DURATION.value == "meeting_duration"
        assert MetricType.OCCUPANCY.value == "occupancy"
        assert MetricType.UTILIZATION.value == "utilization"


class TestReportFormat:
    """Tests for ReportFormat enum."""

    def test_values(self):
        """Test report format enum values."""
        assert ReportFormat.JSON.value == "json"
        assert ReportFormat.CSV.value == "csv"
        assert ReportFormat.HTML.value == "html"
        assert ReportFormat.PDF.value == "pdf"


class TestMeetingRecord:
    """Tests for MeetingRecord dataclass."""

    def test_creation(self):
        """Test creating a meeting record."""
        start = datetime.now()
        end = start + timedelta(hours=1)

        record = MeetingRecord(
            meeting_id="meeting-001",
            device_id="device-001",
            room_name="Conference Room A",
            platform="google_meet",
            start_time=start,
            end_time=end,
        )

        assert record.meeting_id == "meeting-001"
        assert record.platform == "google_meet"
        assert record.duration_minutes == 60

    def test_duration_calculation(self):
        """Test duration calculation."""
        start = datetime.now()
        end = start + timedelta(minutes=45)

        record = MeetingRecord(
            meeting_id="meeting-001",
            device_id="device-001",
            room_name="Room A",
            platform="teams",
            start_time=start,
            end_time=end,
        )

        assert record.duration_minutes == 45


class TestUsageStats:
    """Tests for UsageStats dataclass."""

    def test_creation(self):
        """Test creating usage stats."""
        stats = UsageStats(
            total_meetings=100,
            total_duration_minutes=6000,
            avg_duration_minutes=60.0,
            peak_hours={9: 15, 10: 20, 14: 18},
            platform_distribution={"google_meet": 0.5, "teams": 0.3, "zoom": 0.2},
            time_range=TimeRange.MONTH,
        )

        assert stats.total_meetings == 100
        assert stats.avg_duration_minutes == 60.0
        assert len(stats.peak_hours) == 3


class TestMeetingTracker:
    """Tests for MeetingTracker class."""

    def test_init(self):
        """Test tracker initialization."""
        tracker = MeetingTracker()
        assert tracker._active_meetings == {}
        assert tracker._meeting_history == []

    def test_start_meeting(self):
        """Test starting a meeting."""
        tracker = MeetingTracker()

        tracker.start_meeting(
            meeting_id="meeting-001",
            device_id="device-001",
            room_name="Room A",
            platform="google_meet",
        )

        assert "meeting-001" in tracker._active_meetings
        assert tracker._active_meetings["meeting-001"]["platform"] == "google_meet"

    def test_end_meeting(self):
        """Test ending a meeting."""
        tracker = MeetingTracker()

        tracker.start_meeting(
            meeting_id="meeting-001",
            device_id="device-001",
            room_name="Room A",
            platform="google_meet",
        )

        record = tracker.end_meeting("meeting-001")

        assert record is not None
        assert record.meeting_id == "meeting-001"
        assert "meeting-001" not in tracker._active_meetings
        assert len(tracker._meeting_history) == 1

    def test_end_nonexistent_meeting(self):
        """Test ending a meeting that doesn't exist."""
        tracker = MeetingTracker()

        record = tracker.end_meeting("nonexistent")
        assert record is None

    def test_get_active_meetings(self):
        """Test getting active meetings."""
        tracker = MeetingTracker()

        tracker.start_meeting("meeting-001", "device-001", "Room A", "google_meet")
        tracker.start_meeting("meeting-002", "device-002", "Room B", "teams")

        active = tracker.get_active_meetings()
        assert len(active) == 2

    def test_get_meeting_history(self):
        """Test getting meeting history."""
        tracker = MeetingTracker()

        tracker.start_meeting("meeting-001", "device-001", "Room A", "google_meet")
        tracker.end_meeting("meeting-001")

        tracker.start_meeting("meeting-002", "device-001", "Room A", "teams")
        tracker.end_meeting("meeting-002")

        history = tracker.get_meeting_history()
        assert len(history) == 2

    def test_get_meeting_history_filtered(self):
        """Test getting filtered meeting history."""
        tracker = MeetingTracker()

        tracker.start_meeting("meeting-001", "device-001", "Room A", "google_meet")
        tracker.end_meeting("meeting-001")

        tracker.start_meeting("meeting-002", "device-002", "Room B", "teams")
        tracker.end_meeting("meeting-002")

        history = tracker.get_meeting_history(device_id="device-001")
        assert len(history) == 1
        assert history[0].device_id == "device-001"


class TestAnalyticsEngine:
    """Tests for AnalyticsEngine class."""

    def test_init(self):
        """Test engine initialization."""
        tracker = MeetingTracker()
        engine = AnalyticsEngine(tracker)
        assert engine._tracker == tracker

    def test_get_usage_stats_empty(self):
        """Test getting usage stats with no data."""
        tracker = MeetingTracker()
        engine = AnalyticsEngine(tracker)

        stats = engine.get_usage_stats(TimeRange.WEEK)

        assert stats.total_meetings == 0
        assert stats.total_duration_minutes == 0
        assert stats.avg_duration_minutes == 0.0

    def test_get_usage_stats_with_data(self):
        """Test getting usage stats with meeting data."""
        tracker = MeetingTracker()

        # Add some historical meeting records manually
        now = datetime.now()
        for i in range(5):
            tracker._meeting_history.append(MeetingRecord(
                meeting_id=f"meeting-{i}",
                device_id="device-001",
                room_name="Room A",
                platform="google_meet",
                start_time=now - timedelta(days=1, hours=i),
                end_time=now - timedelta(days=1, hours=i-1),
            ))

        engine = AnalyticsEngine(tracker)
        stats = engine.get_usage_stats(TimeRange.WEEK)

        assert stats.total_meetings == 5
        assert stats.total_duration_minutes == 300  # 5 meetings * 60 minutes

    def test_get_platform_distribution(self):
        """Test getting platform distribution."""
        tracker = MeetingTracker()

        now = datetime.now()
        tracker._meeting_history.append(MeetingRecord(
            meeting_id="meeting-1",
            device_id="device-001",
            room_name="Room A",
            platform="google_meet",
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
        ))
        tracker._meeting_history.append(MeetingRecord(
            meeting_id="meeting-2",
            device_id="device-001",
            room_name="Room A",
            platform="teams",
            start_time=now - timedelta(hours=4),
            end_time=now - timedelta(hours=3),
        ))

        engine = AnalyticsEngine(tracker)
        distribution = engine.get_platform_distribution(TimeRange.DAY)

        assert "google_meet" in distribution
        assert "teams" in distribution
        assert distribution["google_meet"] == 0.5
        assert distribution["teams"] == 0.5

    def test_get_peak_hours(self):
        """Test getting peak hours."""
        tracker = MeetingTracker()

        now = datetime.now()
        # Add meetings at 9 AM and 10 AM
        tracker._meeting_history.append(MeetingRecord(
            meeting_id="meeting-1",
            device_id="device-001",
            room_name="Room A",
            platform="google_meet",
            start_time=now.replace(hour=9, minute=0),
            end_time=now.replace(hour=10, minute=0),
        ))
        tracker._meeting_history.append(MeetingRecord(
            meeting_id="meeting-2",
            device_id="device-001",
            room_name="Room A",
            platform="teams",
            start_time=now.replace(hour=9, minute=30),
            end_time=now.replace(hour=10, minute=30),
        ))

        engine = AnalyticsEngine(tracker)
        peak_hours = engine.get_peak_hours(TimeRange.DAY)

        assert 9 in peak_hours
        assert peak_hours[9] == 2  # Both meetings started at 9

    def test_get_trend(self):
        """Test getting trend data."""
        tracker = MeetingTracker()

        now = datetime.now()
        for i in range(7):
            tracker._meeting_history.append(MeetingRecord(
                meeting_id=f"meeting-{i}",
                device_id="device-001",
                room_name="Room A",
                platform="google_meet",
                start_time=now - timedelta(days=i, hours=1),
                end_time=now - timedelta(days=i),
            ))

        engine = AnalyticsEngine(tracker)
        trend = engine.get_trend(MetricType.MEETING_COUNT, TimeRange.WEEK)

        assert len(trend) > 0
        assert all(isinstance(t, TrendData) for t in trend)


class TestReportGenerator:
    """Tests for ReportGenerator class."""

    def test_init(self):
        """Test generator initialization."""
        tracker = MeetingTracker()
        engine = AnalyticsEngine(tracker)
        generator = ReportGenerator(engine)
        assert generator._engine == engine

    @pytest.mark.asyncio
    async def test_generate_usage_report(self):
        """Test generating usage report."""
        tracker = MeetingTracker()
        engine = AnalyticsEngine(tracker)
        generator = ReportGenerator(engine)

        report = await generator.generate_usage_report(
            time_range=TimeRange.WEEK,
            format=ReportFormat.JSON,
        )

        assert report is not None
        assert report.title == "Usage Report"
        assert report.format == ReportFormat.JSON

    def test_export_to_json(self):
        """Test exporting report to JSON."""
        tracker = MeetingTracker()
        engine = AnalyticsEngine(tracker)
        generator = ReportGenerator(engine)

        report = Report(
            report_id="report-001",
            title="Test Report",
            generated_at=datetime.now(),
            time_range=TimeRange.WEEK,
            format=ReportFormat.JSON,
            data={"total_meetings": 10},
        )

        json_output = generator.export_to_json(report)
        assert isinstance(json_output, str)
        assert "total_meetings" in json_output

    def test_export_to_csv(self):
        """Test exporting report to CSV."""
        tracker = MeetingTracker()
        engine = AnalyticsEngine(tracker)
        generator = ReportGenerator(engine)

        report = Report(
            report_id="report-001",
            title="Test Report",
            generated_at=datetime.now(),
            time_range=TimeRange.WEEK,
            format=ReportFormat.CSV,
            data={"meetings": [
                {"id": "m1", "duration": 60},
                {"id": "m2", "duration": 45},
            ]},
        )

        csv_output = generator.export_to_csv(report)
        assert isinstance(csv_output, str)

    def test_export_to_html(self):
        """Test exporting report to HTML."""
        tracker = MeetingTracker()
        engine = AnalyticsEngine(tracker)
        generator = ReportGenerator(engine)

        report = Report(
            report_id="report-001",
            title="Test Report",
            generated_at=datetime.now(),
            time_range=TimeRange.WEEK,
            format=ReportFormat.HTML,
            data={"total_meetings": 10},
        )

        html_output = generator.export_to_html(report)
        assert isinstance(html_output, str)
        assert "<html>" in html_output
        assert "Test Report" in html_output


class TestScheduledReportService:
    """Tests for ScheduledReportService class."""

    def test_init(self):
        """Test service initialization."""
        tracker = MeetingTracker()
        engine = AnalyticsEngine(tracker)
        generator = ReportGenerator(engine)
        service = ScheduledReportService(generator)

        assert service._generator == generator
        assert service._schedules == {}

    def test_add_schedule(self):
        """Test adding report schedule."""
        tracker = MeetingTracker()
        engine = AnalyticsEngine(tracker)
        generator = ReportGenerator(engine)
        service = ScheduledReportService(generator)

        schedule_id = service.add_schedule(
            name="Weekly Report",
            time_range=TimeRange.WEEK,
            format=ReportFormat.JSON,
            cron_expression="0 9 * * 1",  # Every Monday at 9 AM
            recipients=["admin@example.com"],
        )

        assert schedule_id is not None
        assert schedule_id in service._schedules

    def test_remove_schedule(self):
        """Test removing report schedule."""
        tracker = MeetingTracker()
        engine = AnalyticsEngine(tracker)
        generator = ReportGenerator(engine)
        service = ScheduledReportService(generator)

        schedule_id = service.add_schedule(
            name="Weekly Report",
            time_range=TimeRange.WEEK,
            format=ReportFormat.JSON,
            cron_expression="0 9 * * 1",
            recipients=["admin@example.com"],
        )

        result = service.remove_schedule(schedule_id)
        assert result is True
        assert schedule_id not in service._schedules

    def test_get_schedules(self):
        """Test getting all schedules."""
        tracker = MeetingTracker()
        engine = AnalyticsEngine(tracker)
        generator = ReportGenerator(engine)
        service = ScheduledReportService(generator)

        service.add_schedule(
            name="Weekly Report",
            time_range=TimeRange.WEEK,
            format=ReportFormat.JSON,
            cron_expression="0 9 * * 1",
            recipients=["admin@example.com"],
        )
        service.add_schedule(
            name="Monthly Report",
            time_range=TimeRange.MONTH,
            format=ReportFormat.HTML,
            cron_expression="0 9 1 * *",
            recipients=["admin@example.com"],
        )

        schedules = service.get_schedules()
        assert len(schedules) == 2

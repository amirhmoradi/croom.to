"""
Analytics service for Croom.

Provides usage analytics, reporting, and insights for fleet management.
"""

import json
import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TimeRange(Enum):
    """Predefined time ranges for analytics."""
    LAST_HOUR = "1h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
    CUSTOM = "custom"


class AggregationType(Enum):
    """Aggregation types for metrics."""
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"


@dataclass
class MeetingStats:
    """Statistics for a single meeting."""
    meeting_id: str
    provider: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: float = 0
    participants_peak: int = 0
    quality_score: float = 0  # 0-100
    audio_issues: int = 0
    video_issues: int = 0
    connection_drops: int = 0
    cpu_avg: float = 0
    memory_avg: float = 0
    network_latency_avg: float = 0

    def to_dict(self) -> dict:
        return {
            "meeting_id": self.meeting_id,
            "provider": self.provider,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "participants_peak": self.participants_peak,
            "quality_score": self.quality_score,
            "audio_issues": self.audio_issues,
            "video_issues": self.video_issues,
            "connection_drops": self.connection_drops,
            "cpu_avg": self.cpu_avg,
            "memory_avg": self.memory_avg,
            "network_latency_avg": self.network_latency_avg,
        }


@dataclass
class DeviceStats:
    """Aggregated device statistics."""
    device_id: str
    device_name: str
    site: Optional[str] = None
    time_range: TimeRange = TimeRange.LAST_24_HOURS
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Availability
    uptime_percent: float = 0
    downtime_minutes: int = 0
    reboot_count: int = 0

    # Meetings
    total_meetings: int = 0
    total_meeting_minutes: float = 0
    avg_meeting_duration: float = 0
    avg_quality_score: float = 0

    # Performance
    cpu_avg: float = 0
    cpu_max: float = 0
    memory_avg: float = 0
    memory_max: float = 0
    temperature_avg: float = 0
    temperature_max: float = 0

    # Network
    network_latency_avg: float = 0
    network_latency_p95: float = 0
    packet_loss_percent: float = 0

    # Issues
    alert_count: int = 0
    critical_alerts: int = 0
    warning_alerts: int = 0

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "site": self.site,
            "time_range": self.time_range.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "uptime_percent": self.uptime_percent,
            "downtime_minutes": self.downtime_minutes,
            "reboot_count": self.reboot_count,
            "total_meetings": self.total_meetings,
            "total_meeting_minutes": self.total_meeting_minutes,
            "avg_meeting_duration": self.avg_meeting_duration,
            "avg_quality_score": self.avg_quality_score,
            "cpu_avg": self.cpu_avg,
            "cpu_max": self.cpu_max,
            "memory_avg": self.memory_avg,
            "memory_max": self.memory_max,
            "temperature_avg": self.temperature_avg,
            "temperature_max": self.temperature_max,
            "network_latency_avg": self.network_latency_avg,
            "network_latency_p95": self.network_latency_p95,
            "packet_loss_percent": self.packet_loss_percent,
            "alert_count": self.alert_count,
            "critical_alerts": self.critical_alerts,
            "warning_alerts": self.warning_alerts,
        }


@dataclass
class FleetStats:
    """Aggregated fleet-wide statistics."""
    time_range: TimeRange = TimeRange.LAST_24_HOURS
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Fleet size
    total_devices: int = 0
    online_devices: int = 0
    offline_devices: int = 0

    # Availability
    fleet_uptime_percent: float = 0

    # Meetings
    total_meetings: int = 0
    total_meeting_hours: float = 0
    avg_meetings_per_device: float = 0
    busiest_device: Optional[str] = None
    busiest_hour: Optional[int] = None

    # Performance
    avg_quality_score: float = 0
    devices_below_threshold: int = 0  # Quality score < 70

    # Issues
    total_alerts: int = 0
    devices_with_critical_alerts: int = 0

    # By provider
    meetings_by_provider: Dict[str, int] = field(default_factory=dict)

    # By site
    meetings_by_site: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "time_range": self.time_range.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_devices": self.total_devices,
            "online_devices": self.online_devices,
            "offline_devices": self.offline_devices,
            "fleet_uptime_percent": self.fleet_uptime_percent,
            "total_meetings": self.total_meetings,
            "total_meeting_hours": self.total_meeting_hours,
            "avg_meetings_per_device": self.avg_meetings_per_device,
            "busiest_device": self.busiest_device,
            "busiest_hour": self.busiest_hour,
            "avg_quality_score": self.avg_quality_score,
            "devices_below_threshold": self.devices_below_threshold,
            "total_alerts": self.total_alerts,
            "devices_with_critical_alerts": self.devices_with_critical_alerts,
            "meetings_by_provider": self.meetings_by_provider,
            "meetings_by_site": self.meetings_by_site,
        }


class MetricsStore:
    """In-memory store for metrics with time-series capabilities."""

    def __init__(self, retention_days: int = 90):
        """
        Initialize metrics store.

        Args:
            retention_days: Number of days to retain metrics
        """
        self._retention = timedelta(days=retention_days)
        self._metrics: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self._meetings: List[MeetingStats] = []
        self._alerts: List[Dict[str, Any]] = []
        self._device_events: List[Dict[str, Any]] = []

    def record_metric(
        self,
        name: str,
        value: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record a metric value."""
        ts = timestamp or datetime.utcnow()
        self._metrics[name].append((ts, value))
        self._cleanup_old_metrics()

    def record_meeting(self, meeting: MeetingStats) -> None:
        """Record meeting statistics."""
        self._meetings.append(meeting)
        self._cleanup_old_data()

    def record_alert(
        self,
        alert_id: str,
        severity: str,
        rule_name: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record an alert occurrence."""
        self._alerts.append({
            "id": alert_id,
            "severity": severity,
            "rule_name": rule_name,
            "timestamp": timestamp or datetime.utcnow(),
        })
        self._cleanup_old_data()

    def record_device_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record a device event (reboot, update, etc)."""
        self._device_events.append({
            "type": event_type,
            "details": details,
            "timestamp": timestamp or datetime.utcnow(),
        })
        self._cleanup_old_data()

    def get_metrics(
        self,
        name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Tuple[datetime, float]]:
        """Get metric values within time range."""
        values = self._metrics.get(name, [])

        if start_time or end_time:
            filtered = []
            for ts, val in values:
                if start_time and ts < start_time:
                    continue
                if end_time and ts > end_time:
                    continue
                filtered.append((ts, val))
            return filtered

        return values

    def aggregate_metric(
        self,
        name: str,
        aggregation: AggregationType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Optional[float]:
        """Aggregate metric values."""
        values = [v for _, v in self.get_metrics(name, start_time, end_time)]

        if not values:
            return None

        if aggregation == AggregationType.AVG:
            return statistics.mean(values)
        elif aggregation == AggregationType.MIN:
            return min(values)
        elif aggregation == AggregationType.MAX:
            return max(values)
        elif aggregation == AggregationType.SUM:
            return sum(values)
        elif aggregation == AggregationType.COUNT:
            return float(len(values))
        elif aggregation == AggregationType.P50:
            return statistics.median(values)
        elif aggregation == AggregationType.P95:
            return self._percentile(values, 95)
        elif aggregation == AggregationType.P99:
            return self._percentile(values, 99)

        return None

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def get_meetings(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        provider: Optional[str] = None,
    ) -> List[MeetingStats]:
        """Get meetings within time range."""
        meetings = self._meetings

        if provider:
            meetings = [m for m in meetings if m.provider == provider]

        if start_time or end_time:
            filtered = []
            for meeting in meetings:
                if start_time and meeting.start_time < start_time:
                    continue
                if end_time and meeting.start_time > end_time:
                    continue
                filtered.append(meeting)
            return filtered

        return meetings

    def get_alerts(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get alerts within time range."""
        alerts = self._alerts

        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]

        if start_time or end_time:
            filtered = []
            for alert in alerts:
                ts = alert["timestamp"]
                if start_time and ts < start_time:
                    continue
                if end_time and ts > end_time:
                    continue
                filtered.append(alert)
            return filtered

        return alerts

    def get_device_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get device events within time range."""
        events = self._device_events

        if event_type:
            events = [e for e in events if e["type"] == event_type]

        if start_time or end_time:
            filtered = []
            for event in events:
                ts = event["timestamp"]
                if start_time and ts < start_time:
                    continue
                if end_time and ts > end_time:
                    continue
                filtered.append(event)
            return filtered

        return events

    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff = datetime.utcnow() - self._retention

        for name in list(self._metrics.keys()):
            self._metrics[name] = [
                (ts, val) for ts, val in self._metrics[name]
                if ts >= cutoff
            ]
            if not self._metrics[name]:
                del self._metrics[name]

    def _cleanup_old_data(self) -> None:
        """Remove old data beyond retention period."""
        cutoff = datetime.utcnow() - self._retention

        self._meetings = [m for m in self._meetings if m.start_time >= cutoff]
        self._alerts = [a for a in self._alerts if a["timestamp"] >= cutoff]
        self._device_events = [e for e in self._device_events if e["timestamp"] >= cutoff]


class AnalyticsEngine:
    """Engine for computing analytics and generating reports."""

    def __init__(self, metrics_store: MetricsStore):
        """
        Initialize analytics engine.

        Args:
            metrics_store: Metrics store instance
        """
        self._store = metrics_store

    def get_time_range(
        self,
        range_type: TimeRange,
        custom_start: Optional[datetime] = None,
        custom_end: Optional[datetime] = None,
    ) -> Tuple[datetime, datetime]:
        """Get start and end times for a time range."""
        end = datetime.utcnow()

        if range_type == TimeRange.LAST_HOUR:
            start = end - timedelta(hours=1)
        elif range_type == TimeRange.LAST_24_HOURS:
            start = end - timedelta(hours=24)
        elif range_type == TimeRange.LAST_7_DAYS:
            start = end - timedelta(days=7)
        elif range_type == TimeRange.LAST_30_DAYS:
            start = end - timedelta(days=30)
        elif range_type == TimeRange.LAST_90_DAYS:
            start = end - timedelta(days=90)
        elif range_type == TimeRange.CUSTOM and custom_start and custom_end:
            start = custom_start
            end = custom_end
        else:
            start = end - timedelta(hours=24)

        return start, end

    def get_device_stats(
        self,
        device_id: str,
        device_name: str,
        time_range: TimeRange = TimeRange.LAST_24_HOURS,
        site: Optional[str] = None,
        custom_start: Optional[datetime] = None,
        custom_end: Optional[datetime] = None,
    ) -> DeviceStats:
        """
        Calculate device statistics for a time range.

        Args:
            device_id: Device identifier
            device_name: Device display name
            time_range: Time range for statistics
            site: Site/location name
            custom_start: Custom start time
            custom_end: Custom end time

        Returns:
            Device statistics
        """
        start, end = self.get_time_range(time_range, custom_start, custom_end)

        stats = DeviceStats(
            device_id=device_id,
            device_name=device_name,
            site=site,
            time_range=time_range,
            start_time=start,
            end_time=end,
        )

        # Calculate uptime
        uptime_values = self._store.get_metrics("uptime", start, end)
        if uptime_values:
            total_time = (end - start).total_seconds()
            # Assuming uptime metric is recorded periodically
            stats.uptime_percent = 100.0  # Placeholder, would need actual calculation

        # Reboot count
        reboot_events = self._store.get_device_events(start, end, "reboot")
        stats.reboot_count = len(reboot_events)

        # Meeting statistics
        meetings = self._store.get_meetings(start, end)
        stats.total_meetings = len(meetings)
        if meetings:
            stats.total_meeting_minutes = sum(m.duration_minutes for m in meetings)
            stats.avg_meeting_duration = stats.total_meeting_minutes / len(meetings)
            quality_scores = [m.quality_score for m in meetings if m.quality_score > 0]
            if quality_scores:
                stats.avg_quality_score = statistics.mean(quality_scores)

        # Performance metrics
        cpu_avg = self._store.aggregate_metric("cpu_usage_percent", AggregationType.AVG, start, end)
        cpu_max = self._store.aggregate_metric("cpu_usage_percent", AggregationType.MAX, start, end)
        if cpu_avg is not None:
            stats.cpu_avg = cpu_avg
        if cpu_max is not None:
            stats.cpu_max = cpu_max

        mem_avg = self._store.aggregate_metric("memory_usage_percent", AggregationType.AVG, start, end)
        mem_max = self._store.aggregate_metric("memory_usage_percent", AggregationType.MAX, start, end)
        if mem_avg is not None:
            stats.memory_avg = mem_avg
        if mem_max is not None:
            stats.memory_max = mem_max

        temp_avg = self._store.aggregate_metric("cpu_temperature_celsius", AggregationType.AVG, start, end)
        temp_max = self._store.aggregate_metric("cpu_temperature_celsius", AggregationType.MAX, start, end)
        if temp_avg is not None:
            stats.temperature_avg = temp_avg
        if temp_max is not None:
            stats.temperature_max = temp_max

        # Network metrics
        latency_avg = self._store.aggregate_metric("network_latency_ms", AggregationType.AVG, start, end)
        latency_p95 = self._store.aggregate_metric("network_latency_ms", AggregationType.P95, start, end)
        if latency_avg is not None:
            stats.network_latency_avg = latency_avg
        if latency_p95 is not None:
            stats.network_latency_p95 = latency_p95

        # Alerts
        alerts = self._store.get_alerts(start, end)
        stats.alert_count = len(alerts)
        stats.critical_alerts = len([a for a in alerts if a["severity"] == "critical"])
        stats.warning_alerts = len([a for a in alerts if a["severity"] == "warning"])

        return stats

    def get_meeting_analytics(
        self,
        time_range: TimeRange = TimeRange.LAST_24_HOURS,
        custom_start: Optional[datetime] = None,
        custom_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get meeting analytics.

        Returns detailed meeting statistics and trends.
        """
        start, end = self.get_time_range(time_range, custom_start, custom_end)
        meetings = self._store.get_meetings(start, end)

        if not meetings:
            return {
                "time_range": time_range.value,
                "total_meetings": 0,
                "message": "No meetings in time range",
            }

        # Basic stats
        total = len(meetings)
        total_minutes = sum(m.duration_minutes for m in meetings)
        durations = [m.duration_minutes for m in meetings]

        # By provider
        by_provider: Dict[str, int] = defaultdict(int)
        for m in meetings:
            by_provider[m.provider] += 1

        # By hour of day
        by_hour: Dict[int, int] = defaultdict(int)
        for m in meetings:
            by_hour[m.start_time.hour] += 1

        # By day of week
        by_day: Dict[int, int] = defaultdict(int)
        for m in meetings:
            by_day[m.start_time.weekday()] += 1

        # Quality analysis
        quality_scores = [m.quality_score for m in meetings if m.quality_score > 0]

        # Issue analysis
        total_audio_issues = sum(m.audio_issues for m in meetings)
        total_video_issues = sum(m.video_issues for m in meetings)
        total_connection_drops = sum(m.connection_drops for m in meetings)

        return {
            "time_range": time_range.value,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "total_meetings": total,
            "total_minutes": total_minutes,
            "total_hours": total_minutes / 60,
            "avg_duration_minutes": statistics.mean(durations) if durations else 0,
            "min_duration_minutes": min(durations) if durations else 0,
            "max_duration_minutes": max(durations) if durations else 0,
            "median_duration_minutes": statistics.median(durations) if durations else 0,
            "by_provider": dict(by_provider),
            "by_hour": dict(by_hour),
            "by_day_of_week": dict(by_day),
            "busiest_hour": max(by_hour.items(), key=lambda x: x[1])[0] if by_hour else None,
            "busiest_day": max(by_day.items(), key=lambda x: x[1])[0] if by_day else None,
            "quality": {
                "avg_score": statistics.mean(quality_scores) if quality_scores else 0,
                "min_score": min(quality_scores) if quality_scores else 0,
                "max_score": max(quality_scores) if quality_scores else 0,
                "below_threshold": len([s for s in quality_scores if s < 70]),
            },
            "issues": {
                "audio_issues": total_audio_issues,
                "video_issues": total_video_issues,
                "connection_drops": total_connection_drops,
                "meetings_with_issues": len([m for m in meetings if m.audio_issues + m.video_issues + m.connection_drops > 0]),
            },
        }

    def get_performance_trends(
        self,
        metric_name: str,
        time_range: TimeRange = TimeRange.LAST_24_HOURS,
        interval_minutes: int = 60,
        custom_start: Optional[datetime] = None,
        custom_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get performance trends for a metric.

        Args:
            metric_name: Name of the metric
            time_range: Time range
            interval_minutes: Aggregation interval in minutes
            custom_start: Custom start time
            custom_end: Custom end time

        Returns:
            Trend data with time-series points
        """
        start, end = self.get_time_range(time_range, custom_start, custom_end)
        values = self._store.get_metrics(metric_name, start, end)

        if not values:
            return {
                "metric": metric_name,
                "time_range": time_range.value,
                "data_points": [],
            }

        # Bucket by interval
        interval = timedelta(minutes=interval_minutes)
        buckets: Dict[datetime, List[float]] = defaultdict(list)

        for ts, val in values:
            bucket_time = datetime(
                ts.year, ts.month, ts.day, ts.hour,
                (ts.minute // interval_minutes) * interval_minutes,
            )
            buckets[bucket_time].append(val)

        # Create data points
        data_points = []
        for bucket_time in sorted(buckets.keys()):
            bucket_values = buckets[bucket_time]
            data_points.append({
                "timestamp": bucket_time.isoformat(),
                "avg": statistics.mean(bucket_values),
                "min": min(bucket_values),
                "max": max(bucket_values),
                "count": len(bucket_values),
            })

        # Calculate overall statistics
        all_values = [v for _, v in values]

        return {
            "metric": metric_name,
            "time_range": time_range.value,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "interval_minutes": interval_minutes,
            "data_points": data_points,
            "summary": {
                "avg": statistics.mean(all_values),
                "min": min(all_values),
                "max": max(all_values),
                "std_dev": statistics.stdev(all_values) if len(all_values) > 1 else 0,
            },
        }

    def get_alert_analytics(
        self,
        time_range: TimeRange = TimeRange.LAST_24_HOURS,
        custom_start: Optional[datetime] = None,
        custom_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get alert analytics."""
        start, end = self.get_time_range(time_range, custom_start, custom_end)
        alerts = self._store.get_alerts(start, end)

        if not alerts:
            return {
                "time_range": time_range.value,
                "total_alerts": 0,
                "message": "No alerts in time range",
            }

        # By severity
        by_severity: Dict[str, int] = defaultdict(int)
        for a in alerts:
            by_severity[a["severity"]] += 1

        # By rule
        by_rule: Dict[str, int] = defaultdict(int)
        for a in alerts:
            by_rule[a["rule_name"]] += 1

        # By hour
        by_hour: Dict[int, int] = defaultdict(int)
        for a in alerts:
            by_hour[a["timestamp"].hour] += 1

        # Top rules
        top_rules = sorted(by_rule.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "time_range": time_range.value,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "total_alerts": len(alerts),
            "by_severity": dict(by_severity),
            "by_rule": dict(by_rule),
            "by_hour": dict(by_hour),
            "top_rules": [{"rule": r, "count": c} for r, c in top_rules],
            "peak_hour": max(by_hour.items(), key=lambda x: x[1])[0] if by_hour else None,
        }


class ReportGenerator:
    """Generates analytics reports."""

    def __init__(self, analytics: AnalyticsEngine):
        """
        Initialize report generator.

        Args:
            analytics: Analytics engine instance
        """
        self._analytics = analytics

    def generate_daily_report(
        self,
        device_id: str,
        device_name: str,
        site: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate daily device report."""
        stats = self._analytics.get_device_stats(
            device_id=device_id,
            device_name=device_name,
            site=site,
            time_range=TimeRange.LAST_24_HOURS,
        )

        meeting_analytics = self._analytics.get_meeting_analytics(
            time_range=TimeRange.LAST_24_HOURS,
        )

        alert_analytics = self._analytics.get_alert_analytics(
            time_range=TimeRange.LAST_24_HOURS,
        )

        return {
            "report_type": "daily",
            "generated_at": datetime.utcnow().isoformat(),
            "device": stats.to_dict(),
            "meetings": meeting_analytics,
            "alerts": alert_analytics,
            "summary": {
                "health_score": self._calculate_health_score(stats),
                "highlights": self._generate_highlights(stats, meeting_analytics),
                "recommendations": self._generate_recommendations(stats),
            },
        }

    def generate_weekly_report(
        self,
        device_id: str,
        device_name: str,
        site: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate weekly device report."""
        stats = self._analytics.get_device_stats(
            device_id=device_id,
            device_name=device_name,
            site=site,
            time_range=TimeRange.LAST_7_DAYS,
        )

        meeting_analytics = self._analytics.get_meeting_analytics(
            time_range=TimeRange.LAST_7_DAYS,
        )

        # Compare with previous week
        end = datetime.utcnow()
        prev_start = end - timedelta(days=14)
        prev_end = end - timedelta(days=7)

        prev_stats = self._analytics.get_device_stats(
            device_id=device_id,
            device_name=device_name,
            site=site,
            time_range=TimeRange.CUSTOM,
            custom_start=prev_start,
            custom_end=prev_end,
        )

        return {
            "report_type": "weekly",
            "generated_at": datetime.utcnow().isoformat(),
            "device": stats.to_dict(),
            "meetings": meeting_analytics,
            "comparison": {
                "meetings_change": stats.total_meetings - prev_stats.total_meetings,
                "quality_change": stats.avg_quality_score - prev_stats.avg_quality_score,
                "alerts_change": stats.alert_count - prev_stats.alert_count,
            },
            "summary": {
                "health_score": self._calculate_health_score(stats),
                "trend": "improving" if stats.avg_quality_score > prev_stats.avg_quality_score else "declining",
            },
        }

    def _calculate_health_score(self, stats: DeviceStats) -> float:
        """Calculate overall health score (0-100)."""
        score = 100.0

        # Deduct for high CPU usage
        if stats.cpu_avg > 80:
            score -= 10
        elif stats.cpu_avg > 60:
            score -= 5

        # Deduct for high memory usage
        if stats.memory_avg > 85:
            score -= 10
        elif stats.memory_avg > 70:
            score -= 5

        # Deduct for high temperature
        if stats.temperature_max > 80:
            score -= 15
        elif stats.temperature_max > 70:
            score -= 5

        # Deduct for low quality score
        if stats.avg_quality_score < 70:
            score -= 15
        elif stats.avg_quality_score < 80:
            score -= 5

        # Deduct for alerts
        score -= stats.critical_alerts * 10
        score -= stats.warning_alerts * 2

        # Deduct for network issues
        if stats.network_latency_avg > 100:
            score -= 10
        elif stats.network_latency_avg > 50:
            score -= 5

        return max(0, min(100, score))

    def _generate_highlights(
        self,
        stats: DeviceStats,
        meetings: Dict[str, Any],
    ) -> List[str]:
        """Generate report highlights."""
        highlights = []

        if stats.total_meetings > 0:
            highlights.append(f"Hosted {stats.total_meetings} meetings totaling {stats.total_meeting_minutes:.0f} minutes")

        if stats.avg_quality_score >= 90:
            highlights.append("Excellent meeting quality maintained")
        elif stats.avg_quality_score >= 80:
            highlights.append("Good meeting quality overall")

        if stats.uptime_percent >= 99.9:
            highlights.append("Near-perfect uptime achieved")

        if stats.critical_alerts == 0:
            highlights.append("No critical alerts during period")

        return highlights

    def _generate_recommendations(self, stats: DeviceStats) -> List[str]:
        """Generate recommendations based on statistics."""
        recommendations = []

        if stats.cpu_avg > 80:
            recommendations.append("Consider upgrading hardware - CPU consistently high")

        if stats.memory_avg > 85:
            recommendations.append("Memory usage critical - check for memory leaks or increase RAM")

        if stats.temperature_max > 80:
            recommendations.append("Improve cooling - high temperatures detected")

        if stats.network_latency_avg > 100:
            recommendations.append("Network latency high - check network infrastructure")

        if stats.avg_quality_score < 70:
            recommendations.append("Meeting quality below threshold - investigate audio/video issues")

        if stats.critical_alerts > 5:
            recommendations.append("Multiple critical alerts - schedule maintenance review")

        if not recommendations:
            recommendations.append("Device performing within normal parameters")

        return recommendations


class AnalyticsService:
    """Main analytics service."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        retention_days: int = 90,
    ):
        """
        Initialize analytics service.

        Args:
            storage_path: Path to store analytics data
            retention_days: Data retention period in days
        """
        self._storage_path = storage_path or Path("/var/lib/croom/analytics")
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._store = MetricsStore(retention_days=retention_days)
        self._engine = AnalyticsEngine(self._store)
        self._reports = ReportGenerator(self._engine)

    def record_metric(
        self,
        name: str,
        value: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record a metric value."""
        self._store.record_metric(name, value, timestamp)

    def record_meeting(self, meeting: MeetingStats) -> None:
        """Record meeting statistics."""
        self._store.record_meeting(meeting)

    def record_alert(
        self,
        alert_id: str,
        severity: str,
        rule_name: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record an alert occurrence."""
        self._store.record_alert(alert_id, severity, rule_name, timestamp)

    def record_device_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record a device event."""
        self._store.record_device_event(event_type, details, timestamp)

    def get_device_stats(
        self,
        device_id: str,
        device_name: str,
        time_range: TimeRange = TimeRange.LAST_24_HOURS,
        **kwargs,
    ) -> DeviceStats:
        """Get device statistics."""
        return self._engine.get_device_stats(device_id, device_name, time_range, **kwargs)

    def get_meeting_analytics(
        self,
        time_range: TimeRange = TimeRange.LAST_24_HOURS,
        **kwargs,
    ) -> Dict[str, Any]:
        """Get meeting analytics."""
        return self._engine.get_meeting_analytics(time_range, **kwargs)

    def get_performance_trends(
        self,
        metric_name: str,
        time_range: TimeRange = TimeRange.LAST_24_HOURS,
        interval_minutes: int = 60,
        **kwargs,
    ) -> Dict[str, Any]:
        """Get performance trends."""
        return self._engine.get_performance_trends(
            metric_name, time_range, interval_minutes, **kwargs
        )

    def get_alert_analytics(
        self,
        time_range: TimeRange = TimeRange.LAST_24_HOURS,
        **kwargs,
    ) -> Dict[str, Any]:
        """Get alert analytics."""
        return self._engine.get_alert_analytics(time_range, **kwargs)

    def generate_daily_report(
        self,
        device_id: str,
        device_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate daily report."""
        return self._reports.generate_daily_report(device_id, device_name, **kwargs)

    def generate_weekly_report(
        self,
        device_id: str,
        device_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate weekly report."""
        return self._reports.generate_weekly_report(device_id, device_name, **kwargs)

    def export_data(
        self,
        time_range: TimeRange = TimeRange.LAST_30_DAYS,
        format: str = "json",
    ) -> str:
        """
        Export analytics data.

        Args:
            time_range: Time range to export
            format: Export format (json, csv)

        Returns:
            Exported data as string
        """
        start, end = self._engine.get_time_range(time_range)

        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "time_range": time_range.value,
            "meetings": [m.to_dict() for m in self._store.get_meetings(start, end)],
            "alerts": self._store.get_alerts(start, end),
            "events": self._store.get_device_events(start, end),
        }

        if format == "json":
            return json.dumps(data, indent=2, default=str)
        else:
            # CSV format would need additional handling
            return json.dumps(data, indent=2, default=str)


def create_analytics_service(config: Dict[str, Any]) -> AnalyticsService:
    """
    Create analytics service from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured analytics service
    """
    return AnalyticsService(
        storage_path=Path(config.get("storage_path", "/var/lib/croom/analytics")),
        retention_days=config.get("retention_days", 90),
    )

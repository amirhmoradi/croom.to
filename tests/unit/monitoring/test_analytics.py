"""
Tests for croom.monitoring.analytics module.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


class TestMetricType:
    """Tests for MetricType enum."""

    def test_values(self):
        """Test metric type enum values."""
        from croom.monitoring.analytics import MetricType

        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"


class TestMetric:
    """Tests for Metric dataclass."""

    def test_counter_metric(self):
        """Test counter metric creation."""
        from croom.monitoring.analytics import Metric, MetricType

        metric = Metric(
            name="meetings_joined",
            metric_type=MetricType.COUNTER,
            value=42,
        )
        assert metric.name == "meetings_joined"
        assert metric.metric_type == MetricType.COUNTER
        assert metric.value == 42


class TestAnalyticsCollector:
    """Tests for AnalyticsCollector class."""

    def test_collector_creation(self):
        """Test analytics collector can be created."""
        from croom.monitoring.analytics import AnalyticsCollector

        collector = AnalyticsCollector()
        assert collector is not None

    def test_record_counter(self):
        """Test recording counter metric."""
        from croom.monitoring.analytics import AnalyticsCollector

        collector = AnalyticsCollector()
        collector.increment("test_counter")
        # Should not raise

    def test_record_gauge(self):
        """Test recording gauge metric."""
        from croom.monitoring.analytics import AnalyticsCollector

        collector = AnalyticsCollector()
        collector.set_gauge("cpu_usage", 75.5)
        # Should not raise


class TestMeetingMetrics:
    """Tests for meeting-related metrics."""

    def test_meeting_started(self):
        """Test recording meeting start."""
        from croom.monitoring.analytics import AnalyticsCollector

        collector = AnalyticsCollector()
        collector.record_meeting_started("google_meet", "meeting-123")
        # Should not raise

    def test_meeting_ended(self):
        """Test recording meeting end."""
        from croom.monitoring.analytics import AnalyticsCollector

        collector = AnalyticsCollector()
        collector.record_meeting_ended("google_meet", "meeting-123", duration_seconds=3600)
        # Should not raise

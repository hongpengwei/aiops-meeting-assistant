import pytest
from src.analytics.sparkline import generate_sparkline_svg
from src.notifications.reporter import render_sparkline
from src.analytics.detector import SystemMetrics, CategoryMetrics

class TestSparkline:
    def test_empty_values(self):
        svg = generate_sparkline_svg([])
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "circle" in svg

    def test_single_value(self):
        svg = generate_sparkline_svg([10], labels=["08/23"])
        assert "<svg" in svg
        assert "08/23: 10 件" in svg

    def test_multiple_values_normal(self):
        values = [2, 3, 5, 2, 4, 3, 6]
        labels = ["08/17", "08/18", "08/19", "08/20", "08/21", "08/22", "08/23"]
        svg = generate_sparkline_svg(values, labels=labels, is_anomaly=False)
        assert "<svg" in svg
        assert "#1a73e8" in svg  # 科技藍
        assert "08/23: 6 件" in svg
        assert "08/17: 2 件" in svg

    def test_multiple_values_anomaly(self):
        values = [2, 2, 3, 1, 2, 3, 18]
        labels = ["08/17", "08/18", "08/19", "08/20", "08/21", "08/22", "08/23"]
        svg = generate_sparkline_svg(values, labels=labels, is_anomaly=True)
        assert "<svg" in svg
        assert "#d93025" in svg  # 警示紅
        assert "08/23: 18 件" in svg

    def test_render_sparkline_filter(self):
        # 測試 Jinja2 Filter 能正確解析 SystemMetrics
        metric = SystemMetrics(
            system_name="MES",
            target_count=12,
            baseline_avg=5.0,
            baseline_std=1.2,
            diff=7.0,
            growth_rate=140.0,
            is_anomaly=True,
            reason="暴增",
            trend_history=[4, 5, 5, 6, 4, 5, 12],
            trend_labels=["08/17", "08/18", "08/19", "08/20", "08/21", "08/22", "08/23"]
        )
        svg = render_sparkline(metric)
        assert "<svg" in svg
        assert "#d93025" in svg
        assert "08/23: 12 件" in svg

        # 測試 None
        assert render_sparkline(None) == ""

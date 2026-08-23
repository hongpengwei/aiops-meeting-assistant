import pytest
from src.analytics.detector import AnomalyDetector

class TestAnomalyDetector:
    def test_daily_detects_spike(self, sample_config, sample_cases_df):
        detector = AnomalyDetector(sample_config)
        result = detector.analyze_daily(sample_cases_df)
        assert result.is_anomaly_detected is True
        anomalous_names = [s.system_name for s in result.anomalous_systems]
        assert 'TCS/TAP' in anomalous_names
    
    def test_daily_normal_systems_not_flagged(self, sample_config, sample_cases_df):
        detector = AnomalyDetector(sample_config)
        result = detector.analyze_daily(sample_cases_df)
        for s in result.systems:
            if s.system_name in ('EES', 'FDC'):
                assert s.is_anomaly is False
    
    def test_daily_empty_df(self, sample_config):
        import pandas as pd
        detector = AnomalyDetector(sample_config)
        result = detector.analyze_daily(pd.DataFrame())
        assert result.is_anomaly_detected is False
        assert len(result.systems) == 0
    
    def test_weekly_analysis_runs(self, sample_config, sample_cases_df):
        detector = AnomalyDetector(sample_config)
        result = detector.analyze_weekly(sample_cases_df)
        assert result.mode == 'weekly'
        assert len(result.systems) > 0

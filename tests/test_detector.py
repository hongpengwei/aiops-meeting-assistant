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

    def test_weekly_category_anomaly_when_system_total_not_spiked(self, sample_config):
        """
        測試週報模式：系統總量未超標 (diff < 10)，但單一類別暴增 (diff >= 4 且 > 1.4倍)
        驗證 is_anomaly_detected 應為 True，且 anomalous_categories 正確捕捉該類別
        """
        import pandas as pd
        from datetime import datetime, timedelta

        rows = []
        target_date = datetime(2026, 8, 23).date()  # 週日
        
        # 過去 4 週基準：每週 TCS/TAP 5 筆 (設備通訊 1 筆，其他類別 4 筆)
        for week_i in range(4, 0, -1):
            w_date = target_date - timedelta(days=week_i * 7)
            rows.append({
                "case_id": f"BASE-W{week_i}-COMM",
                "created_at": pd.Timestamp(w_date),
                "system_name": "TCS/TAP",
                "category": "設備通訊",
                "plant": "Fab 12A",
                "device": "Tool-01",
                "title": "Normal comm issue",
                "description": "Normal comm description",
                "reporter": "User1"
            })
            for i in range(4):
                rows.append({
                    "case_id": f"BASE-W{week_i}-OTHER-{i}",
                    "created_at": pd.Timestamp(w_date) + timedelta(hours=i+1),
                    "system_name": "TCS/TAP",
                    "category": "其他維護",
                    "plant": "Fab 12A",
                    "device": "Tool-01",
                    "title": "Normal issue",
                    "description": "Normal description",
                    "reporter": "User1"
                })

        # 當週 (目標週)：TCS/TAP 共 8 筆 (週均 5 筆，diff=+3 < 10，系統總量未超標)
        # 其中「設備通訊」5 筆 (週均 1 筆，diff=+4 >= 4 且 5 >= 1*1.4，類別暴增)
        # 「其他維護」3 筆 (週均 4 筆，下降)
        for i in range(5):
            rows.append({
                "case_id": f"TGT-COMM-{i}",
                "created_at": pd.Timestamp(target_date) - timedelta(days=i),
                "system_name": "TCS/TAP",
                "category": "設備通訊",
                "plant": "Fab 12A",
                "device": "Tool-01",
                "title": f"Comm error {i}",
                "description": "SECS 通訊中斷",
                "reporter": "User1"
            })
        for i in range(3):
            rows.append({
                "case_id": f"TGT-OTHER-{i}",
                "created_at": pd.Timestamp(target_date) - timedelta(days=i+1),
                "system_name": "TCS/TAP",
                "category": "其他維護",
                "plant": "Fab 12A",
                "device": "Tool-01",
                "title": f"Other error {i}",
                "description": "一般維護",
                "reporter": "User1"
            })

        df = pd.DataFrame(rows)
        detector = AnomalyDetector(sample_config)
        result = detector.analyze_weekly(df, target_week_end=target_date)

        # 驗證整體檢測出異常
        assert result.is_anomaly_detected is True
        # 系統總量未超標
        assert len(result.anomalous_systems) == 0
        # 類別層次檢測出「設備通訊」暴增
        assert "TCS/TAP" in result.anomalous_categories
        anom_cats = [c.category_name for c in result.anomalous_categories["TCS/TAP"]]
        assert "設備通訊" in anom_cats
        assert "其他維護" not in anom_cats


import pytest
import pandas as pd
from datetime import date, datetime, timedelta
from src.utils import get_yesterday_range, get_weekly_range, get_last_full_month_range, subtract_months, get_month_last_day
from src.loaders.csv_loader import CsvCaseLoader
from src.analytics.detector import AnomalyDetector

class TestCalendarPeriods:
    def test_subtract_months_and_last_day(self):
        # 測試跨年與月份回推
        y, m = subtract_months(2026, 1, 1)
        assert (y, m) == (2025, 12)
        assert get_month_last_day(2025, 12) == date(2025, 12, 31)

        y, m = subtract_months(2026, 8, 3)
        assert (y, m) == (2026, 5)
        assert get_month_last_day(2026, 2) == date(2026, 2, 28)

    def test_yesterday_range_deterministic(self):
        # 驗證指定 target_date 時，區間固定對齊 00:00:00 與 23:59:59
        target = date(2026, 8, 23)
        start_dt, end_dt, tgt = get_yesterday_range(target, history_days=7)
        assert start_dt == datetime(2026, 8, 16, 0, 0, 0)
        assert end_dt == datetime(2026, 8, 23, 23, 59, 59)
        assert tgt == target

    def test_last_full_month_range(self):
        # 驗證目標為 2026-07 時，歷史區間起訖精確對齊日曆日
        start_dt, end_dt, tgt_m = get_last_full_month_range("2026-07", history_months=3)
        assert tgt_m == "2026-07"
        assert start_dt == datetime(2026, 4, 1, 0, 0, 0)
        assert end_dt == datetime(2026, 7, 31, 23, 59, 59)

    def test_csv_loader_with_different_execution_hours(self, tmp_path):
        # 建立測試 CSV 資料，包含同一天不同小時的資料
        csv_file = tmp_path / "test_cases.csv"
        rows = [
            # 昨天上午
            {"case_id": "C1", "created_at": "2026-08-23 09:00:00", "system_name": "A", "category": "General", "plant": "F1", "device": "D1", "title": "T1", "description": "D1", "reporter": "R1"},
            # 昨天下午
            {"case_id": "C2", "created_at": "2026-08-23 16:30:00", "system_name": "A", "category": "General", "plant": "F1", "device": "D1", "title": "T2", "description": "D2", "reporter": "R2"},
            # 昨天晚上
            {"case_id": "C3", "created_at": "2026-08-23 21:00:00", "system_name": "B", "category": "General", "plant": "F1", "device": "D1", "title": "T3", "description": "D3", "reporter": "R3"},
            # 今天 (不應納入昨天日報)
            {"case_id": "C4", "created_at": "2026-08-24 10:00:00", "system_name": "A", "category": "General", "plant": "F1", "device": "D1", "title": "T4", "description": "D4", "reporter": "R4"},
        ]
        pd.DataFrame(rows).to_csv(csv_file, index=False)

        loader = CsvCaseLoader(str(csv_file))

        # 模擬早上記錄 (例如 2026-08-24 09:00 執行)
        start_dt, end_dt, tgt_date = get_yesterday_range(date(2026, 8, 23), history_days=7)
        df_morning = loader.load_cases(start_date=start_dt, end_date=end_dt)

        # 模擬晚上記錄 (例如 2026-08-24 23:00 執行)
        start_dt_night, end_dt_night, tgt_date_night = get_yesterday_range(date(2026, 8, 23), history_days=7)
        df_night = loader.load_cases(start_date=start_dt_night, end_date=end_dt_night)

        # 兩次讀取出的筆數與分佈完全一致
        assert len(df_morning) == 3
        assert len(df_night) == 3
        assert (df_morning["system_name"].value_counts() == df_night["system_name"].value_counts()).all()
        assert df_morning["system_name"].value_counts()["A"] == 2
        assert df_morning["system_name"].value_counts()["B"] == 1

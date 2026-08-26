import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.analytics.detector import AnomalyDetector

@pytest.fixture
def monthly_test_df():
    """
    建立跨 4 個月的測試數據 (2026-05, 2026-06, 2026-07 為基準月，2026-08 為目標月)
    - TCS/TAP 在 2026-08 總量暴增
    - 其中 TCS/TAP 的「設備通訊」與「派工作業」兩個類別暴增
    - 其他類別與系統維持正常月均
    """
    rows = []
    
    # 基準月：5, 6, 7 月 (每個月 TCS/TAP 約 20 筆，各類別平均 2~4 筆)
    months = [
        datetime(2026, 5, 15),
        datetime(2026, 6, 15),
        datetime(2026, 7, 15)
    ]
    
    for m in months:
        for cat in ["設備通訊", "派工作業", "自動搬運", "帳號與權限", "報表與查詢"]:
            for i in range(4): # 每個類別 4 筆，TCS/TAP 每月共 20 筆
                rows.append({
                    "case_id": f"BASE-{m.month}-{cat}-{i}",
                    "created_at": m + timedelta(hours=i),
                    "system_name": "tcs/tap",
                    "category": cat,
                    "plant": "Fab 12A",
                    "device": "Tool-01",
                    "title": f"Normal issue {cat}",
                    "description": f"Normal description {cat}",
                    "reporter": "User1"
                })
        # 其他系統 (EES, FDC) 每月 10 筆
        for sys_name in ["ees", "fdc"]:
            for i in range(10):
                rows.append({
                    "case_id": f"BASE-{m.month}-{sys_name}-{i}",
                    "created_at": m + timedelta(hours=i),
                    "system_name": sys_name,
                    "category": "一般維護",
                    "plant": "Fab 14A",
                    "device": "Tool-02",
                    "title": "Normal issue",
                    "description": "Normal description",
                    "reporter": "User2"
                })

    # 目標月：2026-08
    target_month = datetime(2026, 8, 15)
    # TCS/TAP 本月暴增至 60 筆 (基準均值 20 筆，> 1.3 倍且增加 40 筆)
    # 其中「設備通訊」暴增至 30 筆 (月均 4 筆 -> +26 筆)
    # 「派工作業」暴增至 20 筆 (月均 4 筆 -> +16 筆)
    # 其他類別維持正常 (各 2~4 筆)
    for i in range(30):
        rows.append({
            "case_id": f"TGT-COMM-{i}",
            "created_at": target_month + timedelta(hours=i % 24),
            "system_name": "tcs/tap",
            "category": "設備通訊",
            "plant": "Fab 12A",
            "device": "Track-03",
            "title": f"Track-03 communication error {i}",
            "description": "Track-03 通訊逾時中斷",
            "reporter": "User1"
        })
    for i in range(20):
        rows.append({
            "case_id": f"TGT-DISP-{i}",
            "created_at": target_month + timedelta(hours=i % 24),
            "system_name": "tcs/tap",
            "category": "派工作業",
            "plant": "Fab 12A",
            "device": "Track-03",
            "title": f"Track-03 dispatch error {i}",
            "description": "Track-03 派工卡站",
            "reporter": "User1"
        })
    for cat in ["自動搬運", "帳號與權限", "報表與查詢"]:
        for i in range(3):
            rows.append({
                "case_id": f"TGT-NORM-{cat}-{i}",
                "created_at": target_month + timedelta(hours=i),
                "system_name": "tcs/tap",
                "category": cat,
                "plant": "Fab 12B",
                "device": "Tool-05",
                "title": f"Normal {cat}",
                "description": f"Normal {cat}",
                "reporter": "User3"
            })

    # 其他系統正常
    for sys_name in ["ees", "fdc"]:
        for i in range(10):
            rows.append({
                "case_id": f"TGT-{sys_name}-{i}",
                "created_at": target_month + timedelta(hours=i),
                "system_name": sys_name,
                "category": "一般維護",
                "plant": "Fab 14A",
                "device": "Tool-02",
                "title": "Normal issue",
                "description": "Normal description",
                "reporter": "User2"
            })

    df = pd.DataFrame(rows)
    df["created_at"] = pd.to_datetime(df["created_at"])
    return df

class TestMonthlyDetector:
    def test_monthly_system_and_category_anomaly_detection(self, sample_config, monthly_test_df):
        detector = AnomalyDetector(sample_config)
        result = detector.analyze_monthly(monthly_test_df, target_month="2026-08")

        # 1. 驗證整體狀態
        assert result.is_anomaly_detected is True
        assert result.mode == "monthly"

        # 2. 驗證第一層：系統級檢測
        anomalous_sys_names = [s.system_name for s in result.anomalous_systems]
        assert "tcs/tap" in anomalous_sys_names
        assert "ees" not in anomalous_sys_names
        assert "fdc" not in anomalous_sys_names

        # 3. 驗證第二層：類別級檢測
        tcs_anom_cats = result.anomalous_categories.get("tcs/tap", [])
        anom_cat_names = [c.category_name for c in tcs_anom_cats]
        assert "設備通訊" in anom_cat_names
        assert "派工作業" in anom_cat_names
        assert "自動搬運" not in anom_cat_names
        assert "帳號與權限" not in anom_cat_names

    def test_monthly_empty_dataframe(self, sample_config):
        detector = AnomalyDetector(sample_config)
        result = detector.analyze_monthly(pd.DataFrame())
        assert result.is_anomaly_detected is False
        assert len(result.systems) == 0

    def test_monthly_category_anomaly_when_system_total_not_spiked(self, sample_config):
        """
        測試月報模式：系統總量未超標 (diff < 15)，但單一類別暴增 (diff >= 5 且 > 1.5倍)
        驗證 is_anomaly_detected 應為 True，且 anomalous_categories 正確捕捉該類別
        """
        rows = []
        months = [datetime(2026, 5, 15), datetime(2026, 6, 15), datetime(2026, 7, 15)]
        
        # 基準月：每個月 10 筆 (設備通訊 1 筆，其他類別 9 筆)
        for m in months:
            rows.append({
                "case_id": f"BASE-{m.month}-COMM",
                "created_at": m,
                "system_name": "tcs/tap",
                "category": "設備通訊",
                "plant": "Fab 12A",
                "device": "Tool-01",
                "title": "Normal comm issue",
                "description": "Normal description",
                "reporter": "User1"
            })
            for i in range(9):
                rows.append({
                    "case_id": f"BASE-{m.month}-OTHER-{i}",
                    "created_at": m + timedelta(hours=i+1),
                    "system_name": "tcs/tap",
                    "category": "其他維護",
                    "plant": "Fab 12A",
                    "device": "Tool-01",
                    "title": "Normal issue",
                    "description": "Normal description",
                    "reporter": "User1"
                })

        # 目標月：2026-08
        # 總量 12 筆 (基準月均 10 筆，diff=+2 < 15，系統總量未超標)
        # 其中「設備通訊」8 筆 (月均 1 筆，diff=+7 >= 5 且 8 >= 1.5，類別暴增)
        # 「其他維護」4 筆 (月均 9 筆，下降)
        target_month = datetime(2026, 8, 15)
        for i in range(8):
            rows.append({
                "case_id": f"TGT-COMM-{i}",
                "created_at": target_month + timedelta(hours=i),
                "system_name": "tcs/tap",
                "category": "設備通訊",
                "plant": "Fab 12A",
                "device": "Tool-01",
                "title": f"Comm error {i}",
                "description": "SECS 通訊逾時中斷",
                "reporter": "User1"
            })
        for i in range(4):
            rows.append({
                "case_id": f"TGT-OTHER-{i}",
                "created_at": target_month + timedelta(hours=i+8),
                "system_name": "tcs/tap",
                "category": "其他維護",
                "plant": "Fab 12A",
                "device": "Tool-01",
                "title": f"Other error {i}",
                "description": "其他問題",
                "reporter": "User1"
            })

        df = pd.DataFrame(rows)
        df["created_at"] = pd.to_datetime(df["created_at"])

        detector = AnomalyDetector(sample_config)
        result = detector.analyze_monthly(df, target_month="2026-08")

        # 驗證整體狀態為異常
        assert result.is_anomaly_detected is True
        # 系統級無異常 (總量未達標)
        assert len(result.anomalous_systems) == 0
        # 類別級有異常
        assert "tcs/tap" in result.anomalous_categories
        anom_cat_names = [c.category_name for c in result.anomalous_categories["tcs/tap"]]
        assert "設備通訊" in anom_cat_names
        assert "其他維護" not in anom_cat_names


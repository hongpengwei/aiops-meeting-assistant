import pytest
import os
import tempfile
import pandas as pd
from datetime import datetime, timedelta
from src.loaders.csv_loader import CsvCaseLoader

class TestCsvLoader:
    def test_load_existing_csv(self, tmp_path):
        # Create a test CSV
        csv_path = str(tmp_path / 'test.csv')
        df = pd.DataFrame({
            'case_id': ['C1', 'C2'],
            'created_at': ['2026-08-20 10:00:00', '2026-08-21 11:00:00'],
            'system_name': ['EES', 'FDC'],
            'plant': ['Fab12', 'Fab14'],
            'device': ['Tool-1', 'Tool-2'],
            'title': ['Issue 1', 'Issue 2'],
            'description': ['Desc 1', 'Desc 2'],
            'reporter': ['User1', 'User2']
        })
        df.to_csv(csv_path, index=False)
        
        loader = CsvCaseLoader(csv_path)
        result = loader.load_cases(
            start_date=datetime(2026, 8, 19),
            end_date=datetime(2026, 8, 22)
        )
        assert len(result) == 2
        assert list(result.columns) == ['case_id', 'created_at', 'system_name', 'category', 'plant', 'device', 'title', 'description', 'reporter']
    
    def test_load_missing_csv_raises(self):
        loader = CsvCaseLoader('/nonexistent/path.csv')
        with pytest.raises(FileNotFoundError):
            loader.load_cases(datetime.now() - timedelta(days=7), datetime.now())
    
    def test_date_filtering(self, tmp_path):
        csv_path = str(tmp_path / 'test.csv')
        df = pd.DataFrame({
            'case_id': ['C1', 'C2', 'C3'],
            'created_at': ['2026-08-18 10:00:00', '2026-08-20 10:00:00', '2026-08-22 10:00:00'],
            'system_name': ['EES', 'EES', 'EES'],
            'plant': ['Fab12', 'Fab12', 'Fab12'],
            'device': ['T1', 'T1', 'T1'],
            'title': ['A', 'B', 'C'],
            'description': ['D1', 'D2', 'D3'],
            'reporter': ['U1', 'U1', 'U1']
        })
        df.to_csv(csv_path, index=False)
        
        loader = CsvCaseLoader(csv_path)
        result = loader.load_cases(
            start_date=datetime(2026, 8, 19),
            end_date=datetime(2026, 8, 21)
        )
        assert len(result) == 1
        assert result.iloc[0]['case_id'] == 'C2'

    def test_future_schema_and_tool_extraction(self, tmp_path):
        """
        測試真實環境欄位 (caseid, createdatetime, fab, subject, username, productname, issuetype)
        驗證自動映射、時間格式轉換以及從 subject 智慧提取 tool_id
        """
        csv_path = str(tmp_path / 'real_world_cases.csv')
        df = pd.DataFrame({
            'caseid': ['case-20260825-00008', 'case-20260825-00009'],
            'createdatetime': ['2026/8/25 12:20:26 AM', '2026/8/25 2:45:10 PM'],
            'fab': ['F15', 'Fab 12A'],
            'subject': ['[ccop alarm:fdcfilecnt]f15_ypoctc的ftc...', 'F12A_Track-03 派工卡站'],
            'username': ['alex_chen', 'john_lin'],
            'productname': ['fdc', 'tcs/tap'],
            'issuetype': ['fdcfilecnt', '派工作業']
        })
        df.to_csv(csv_path, index=False)

        loader = CsvCaseLoader(csv_path)
        result = loader.load_cases(
            start_date=datetime(2026, 8, 25, 0, 0, 0),
            end_date=datetime(2026, 8, 25, 23, 59, 59)
        )

        assert len(result) == 2
        # 驗證欄位名稱已轉換為標準欄位
        assert list(result.columns) == ['case_id', 'created_at', 'system_name', 'category', 'plant', 'device', 'title', 'description', 'reporter']

        # 驗證第 1 筆 (F15 ypoctc, AM 時間, 類別)
        row1 = result.iloc[0]
        assert row1['case_id'] == 'case-20260825-00008'
        assert row1['created_at'] == pd.Timestamp('2026-08-25 00:20:26')
        assert row1['plant'] == 'F15'
        assert row1['device'] == 'ypoctc'
        assert row1['system_name'] == 'fdc'
        assert row1['category'] == 'fdcfilecnt'
        assert row1['reporter'] == 'alex_chen'
        assert row1['title'] == '[ccop alarm:fdcfilecnt]f15_ypoctc的ftc...'
        assert row1['description'] == '[ccop alarm:fdcfilecnt]f15_ypoctc的ftc...'

        # 驗證第 2 筆 (Fab 12A Track-03, PM 時間, 類別)
        row2 = result.iloc[1]
        assert row2['case_id'] == 'case-20260825-00009'
        assert row2['created_at'] == pd.Timestamp('2026-08-25 14:45:10')
        assert row2['plant'] == 'Fab 12A'
        assert row2['device'] == 'Track-03'
        assert row2['system_name'] == 'tcs/tap'
        assert row2['category'] == '派工作業'
        assert row2['reporter'] == 'john_lin'


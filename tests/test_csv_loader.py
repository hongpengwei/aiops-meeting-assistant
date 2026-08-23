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

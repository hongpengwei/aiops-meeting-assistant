import pytest
import pandas as pd
from src.ai.analyzer import AIAnalyzer

class TestAIAnalyzer:
    def test_mock_analysis(self, sample_config):
        analyzer = AIAnalyzer(sample_config)
        cases_df = pd.DataFrame({
            'case_id': ['C1', 'C2', 'C3'],
            'created_at': pd.to_datetime(['2026-08-22'] * 3),
            'system_name': ['TCS/TAP'] * 3,
            'category': ['派工作業', '設備通訊', '一般問題'],
            'plant': ['Fab 12A', 'Fab 12A', 'Fab 14A'],
            'device': ['Track-03', 'Track-03', 'Tool-10'],
            'title': ['Error 1', 'Error 2', 'Error 3'],
            'description': ['派工通訊中斷', '機台卡站', '一般問題'],
            'reporter': ['User1', 'User2', 'User3']
        })
        result = analyzer.analyze_system_cases('TCS/TAP', '2026-08-22', cases_df)
        assert isinstance(result, str)
        assert len(result) > 0
        assert 'Fab 12A' in result  # Should identify the hot spot
    
    def test_category_analysis(self, sample_config):
        analyzer = AIAnalyzer(sample_config)
        cases_df = pd.DataFrame({
            'case_id': ['C1', 'C2', 'C3'],
            'created_at': pd.to_datetime(['2026-08-22'] * 3),
            'system_name': ['TCS/TAP'] * 3,
            'category': ['設備通訊'] * 3,
            'plant': ['Fab 12A', 'Fab 12A', 'Fab 14A'],
            'device': ['Track-03', 'Track-03', 'Tool-10'],
            'title': ['Error 1', 'Error 2', 'Error 3'],
            'description': ['通訊逾時中斷', 'SECS/GEM 連線失敗', '連線異常'],
            'reporter': ['User1', 'User2', 'User3']
        })
        result = analyzer.analyze_category_cases('TCS/TAP', '設備通訊', '2026-08', cases_df)
        assert isinstance(result, str)
        assert len(result) > 0
        assert '設備通訊' in result
        assert 'Fab 12A' in result

    def test_empty_cases(self, sample_config):
        analyzer = AIAnalyzer(sample_config)
        result = analyzer.analyze_system_cases('EES', '2026-08-22', pd.DataFrame())
        assert '無' in result

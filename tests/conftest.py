import pytest
import pandas as pd
from datetime import datetime, timedelta

@pytest.fixture
def sample_config():
    """Return a minimal config dict for testing"""
    return {
        'data_source': {'type': 'csv', 'csv': {'file_path': './data/mock_cases.csv'}},
        'thresholds': {
            'daily': {'baseline_days': 7, 'multiplier': 1.4, 'min_spike_cases': 5},
            'weekly': {'baseline_weeks': 4, 'multiplier': 1.3, 'min_spike_cases': 10}
        },
        'ai': {'provider': 'mock', 'model_name': 'test', 'api_key_env_var': 'TEST_KEY', 'max_cases_to_analyze': 10},
        'notifications': {'local': {'enabled': False}, 'teams': {'enabled': False}, 'email': {'enabled': False}}
    }

@pytest.fixture
def sample_cases_df():
    """Create a sample DataFrame with case data spanning 14 days"""
    # Build data with normal counts for most days and a spike on the latest day
    rows = []
    base_date = datetime.now().date()
    systems = ['EES', 'TCS/TAP', 'FDC']
    
    # Normal days (days -13 to -1): ~2 cases per system per day
    for day_offset in range(13, 0, -1):
        date = base_date - timedelta(days=day_offset)
        for sys in systems:
            for i in range(2):
                rows.append({
                    'case_id': f'TEST-{day_offset}-{sys}-{i}',
                    'created_at': datetime.combine(date, datetime.min.time().replace(hour=10+i)),
                    'system_name': sys,
                    'plant': 'Fab 12A',
                    'device': 'Tool-01',
                    'title': f'Test issue {i}',
                    'description': f'Test description for {sys}',
                    'reporter': 'TestUser'
                })
    
    # Spike day (today): 15 cases for TCS/TAP (clearly above threshold)
    for i in range(15):
        rows.append({
            'case_id': f'TEST-0-TCS-{i}',
            'created_at': datetime.combine(base_date, datetime.min.time().replace(hour=9)),
            'system_name': 'TCS/TAP',
            'plant': 'Fab 12A',
            'device': 'Track-03',
            'title': f'Track-03 connection error {i}',
            'description': 'Track-03 派工通訊中斷',
            'reporter': 'TestUser'
        })
    # Normal count for other systems on spike day
    for sys in ['EES', 'FDC']:
        for i in range(2):
            rows.append({
                'case_id': f'TEST-0-{sys}-{i}',
                'created_at': datetime.combine(base_date, datetime.min.time().replace(hour=10)),
                'system_name': sys,
                'plant': 'Fab 14A',
                'device': 'Tool-05',
                'title': 'Normal issue',
                'description': 'Normal test case',
                'reporter': 'TestUser'
            })
    
    df = pd.DataFrame(rows)
    df['created_at'] = pd.to_datetime(df['created_at'])
    return df

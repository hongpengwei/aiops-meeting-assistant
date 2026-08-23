import os
from datetime import datetime
import pandas as pd
import requests
from src.loaders.base import BaseCaseLoader

class ApiCaseLoader(BaseCaseLoader):
    """
    REST API 載入器 (未來串接 Jira, ServiceNow 或公司內部工單系統 API 時使用)
    """

    def __init__(self, base_url: str, endpoint: str, token_env_var: str = "CORP_API_TOKEN"):
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        self.token = os.getenv(token_env_var, "")

    def load_cases(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        url = f"{self.base_url}{self.endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        params = {
            "start_time": start_date.isoformat(),
            "end_time": end_date.isoformat()
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        # 假設 API 回傳格式為 list of dicts，或 dict 中有 'items' / 'data'
        items = data.get("items", data) if isinstance(data, dict) else data

        df = pd.DataFrame(items)
        return self.validate_and_clean(df)

import os
import time
import logging
from datetime import datetime
import pandas as pd
import requests
from src.loaders.base import BaseCaseLoader

logger = logging.getLogger(__name__)


class ApiCaseLoader(BaseCaseLoader):
    """
    REST API 載入器 (未來串接 Jira, ServiceNow 或公司內部工單系統 API 時使用)
    內建 retry 機制與可配置的 timeout
    """

    MAX_RETRIES = 3
    TIMEOUT = 300  # 秒

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

        # Retry 機制：最多重試 3 次，指數退避
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=self.TIMEOUT)
                response.raise_for_status()

                data = response.json()
                # 假設 API 回傳格式為 list of dicts，或 dict 中有 'items' / 'data'
                items = data.get("items", data) if isinstance(data, dict) else data

                df = pd.DataFrame(items)
                return self.validate_and_clean(df)

            except requests.exceptions.RequestException as e:
                if attempt == self.MAX_RETRIES - 1:
                    logger.error(f"[API Loader] API 載入失敗 (已重試 {self.MAX_RETRIES} 次): {e}")
                    raise
                wait = 2 ** (attempt + 1)
                logger.warning(f"[API Loader] API 呼叫失敗，{wait} 秒後重試 (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                time.sleep(wait)

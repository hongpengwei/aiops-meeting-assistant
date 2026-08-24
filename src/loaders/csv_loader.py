import os
from datetime import datetime
import pandas as pd
from src.loaders.base import BaseCaseLoader

class CsvCaseLoader(BaseCaseLoader):
    """
    CSV / Excel 檔案載入器 (適用於 POC 階段或手動匯出資料)
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load_cases(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"找不到 Case 資料檔案: {self.file_path}，請確認路徑或先產生測試資料。")

        # 支援 .csv, .xlsx, .xls
        if self.file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(self.file_path)
        else:
            df = pd.read_csv(self.file_path)

        df = self.validate_and_clean(df)

        # 根據時間區間過濾 (相容 date 與 datetime)
        from datetime import date as dt_date
        if isinstance(start_date, dt_date) and not isinstance(start_date, datetime):
            start_ts = pd.to_datetime(datetime.combine(start_date, datetime.min.time()))
        else:
            start_ts = pd.to_datetime(start_date)

        if isinstance(end_date, dt_date) and not isinstance(end_date, datetime):
            end_ts = pd.to_datetime(datetime.combine(end_date, datetime.max.time().replace(microsecond=0)))
        else:
            end_ts = pd.to_datetime(end_date)

        filtered_df = df[(df["created_at"] >= start_ts) & (df["created_at"] <= end_ts)].copy()
        return filtered_df


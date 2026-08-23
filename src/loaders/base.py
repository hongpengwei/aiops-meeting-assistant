from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
import pandas as pd

# 標準欄位定義 (Standard Case Schema)
REQUIRED_COLUMNS = [
    "case_id",       # 案件唯一識別碼
    "created_at",    # 建立時間 (datetime)
    "system_name",   # 所屬系統名稱 (如 MES, WMS, ERP)
    "category",      # 案件類別 (如 設備通訊、派工異常、權限申請等)
    "plant",         # 廠區 / 地點 (如 Fab12, Fab14, HQ)
    "device",        # 機台 / 設備編號 (如 Track-01, Svr-02，若無可填未知)
    "title",         # 簡短標題
    "description",   # 提報人描述的詳細狀況與現象
    "reporter"       # 提報人姓名/工號
]

class BaseCaseLoader(ABC):
    """
    所有 Case 資料載入器的抽象基底類別 (Data Adapter Pattern)
    未來無論資料來源是 CSV, Excel, 資料庫還是 API，都必須實作此介面並回傳標準 DataFrame
    """

    @abstractmethod
    def load_cases(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """
        載入指定時間區間內的 Case 數據

        :param start_date: 起始時間 (含)
        :param end_date: 結束時間 (含)
        :return: 包含 REQUIRED_COLUMNS 欄位的 pandas DataFrame
        """
        pass

    def validate_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        驗證並標準化 DataFrame 格式
        """
        if df.empty:
            return pd.DataFrame(columns=REQUIRED_COLUMNS)

        df = df.copy()

        # 確保必要欄位存在，若來源缺少則補預設值
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = "N/A"

        # 確保 created_at 轉換為 datetime
        df["created_at"] = pd.to_datetime(df["created_at"])
        
        # 填充缺失值
        df["category"] = df["category"].replace("N/A", "未分類").fillna("未分類")
        df["plant"] = df["plant"].fillna("未知廠區")
        df["device"] = df["device"].fillna("未知機台/通用")
        df["title"] = df["title"].fillna("無標題")
        df["description"] = df["description"].fillna("無詳細描述")
        df["system_name"] = df["system_name"].fillna("未分類系統")

        return df[REQUIRED_COLUMNS]

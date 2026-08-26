import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# 標準欄位定義 (Standard Case Schema)
REQUIRED_COLUMNS = [
    "case_id",       # 案件唯一識別碼
    "created_at",    # 建立時間 (datetime)
    "system_name",   # 所屬系統名稱 (如 MES, WMS, ERP, FDC, TCS/TAP)
    "category",      # 案件類別 (如 設備通訊、派工異常、權限申請等)
    "plant",         # 廠區 / 地點 (如 Fab12, Fab14, HQ, F15)
    "device",        # 機台 / 設備編號 (如 Track-01, ypoctc，若無可填未知)
    "title",         # 簡短標題
    "description",   # 提報人描述的詳細狀況與現象
    "reporter"       # 提報人姓名/工號
]

# 欄位別名映射表 (Column Name Normalization Map)
COLUMN_ALIASES = {
    "caseid": "case_id",
    "case_no": "case_id",
    "ticket_id": "case_id",
    "issue_id": "case_id",

    "createdatetime": "created_at",
    "create_time": "created_at",
    "created_time": "created_at",
    "submit_time": "created_at",
    "datetime": "created_at",

    "productname": "system_name",
    "product_name": "system_name",
    "system": "system_name",
    "system_name": "system_name",

    "issuetype": "category",
    "issue_type": "category",
    "category_name": "category",
    "category": "category",

    "fab": "plant",
    "fab_id": "plant",
    "site": "plant",
    "plant": "plant",

    "tool_id": "device",
    "toolid": "device",
    "device": "device",
    "eqp_id": "device",
    "machine_id": "device",

    "subject": "title",
    "summary": "title",
    "title": "title",

    "description": "description",
    "user_description": "description",
    "detail": "description",
    "content": "description",

    "username": "reporter",
    "user_name": "reporter",
    "reporter_name": "reporter",
    "reporter": "reporter",
    "owner": "reporter",
}

def extract_device_from_text(text: str) -> Optional[str]:
    """
    從主旨 (subject) 或描述中自動提取機台編號 (tool_id / device)
    範例：
    - "[ccop alarm:fdcfilecnt]f15_ypoctc的ftc..." -> "ypoctc"
    - "f12a_track03卡站" -> "track03"
    - "Tool-01 SECS中斷" -> "Tool-01"
    """
    if not isinstance(text, str) or not text.strip():
        return None

    # 1. 半導體常見模式：f15_ypoctc, F12A_Track-03, F14B_ETCH01
    # 抓取底線後面的機台名稱部分
    m = re.search(r'[fF]\d+[a-zA-Z]?_([a-zA-Z0-9\-_]+)', text)
    if m:
        raw_tool = m.group(1)
        # 截斷後續的中文字或分隔符號 (如 ypoctc的ftc -> ypoctc)
        tool_clean = re.split(r'[\u4e00-\u9fff\s,，:：。\[\]\(\)]', raw_tool)[0]
        if tool_clean and len(tool_clean) >= 2:
            return tool_clean

    # 2. 明確前綴模式：tool_id: xxx, tool=xxx, device: xxx
    m2 = re.search(r'(?:tool_id|tool|device|eqp)[:=\s]+([a-zA-Z0-9\-_]+)', text, re.IGNORECASE)
    if m2:
        return m2.group(1)

    return None

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
        驗證並標準化 DataFrame 格式，支援新舊欄位別名與機台自動解析
        """
        if df.empty:
            return pd.DataFrame(columns=REQUIRED_COLUMNS)

        df = df.copy()

        # 1. 欄位名稱正規化 (去除空白、轉小寫，並依照別名映射)
        rename_map = {}
        for col in df.columns:
            clean_col = str(col).strip().lower()
            if clean_col in COLUMN_ALIASES:
                target_col = COLUMN_ALIASES[clean_col]
                if target_col not in df.columns:
                    rename_map[col] = target_col
        if rename_map:
            df = df.rename(columns=rename_map)

        # 2. 若有 title (subject) 但缺少 description，自動以 title 填補 description
        if "title" in df.columns and ("description" not in df.columns or df["description"].isnull().all()):
            df["description"] = df["title"]
        elif "description" in df.columns and ("title" not in df.columns or df["title"].isnull().all()):
            df["title"] = df["description"]

        # 3. 若 device 未提供或為空，嘗試從 title / description (subject) 中提取 tool_id
        #    使用向量化操作取代 iterrows() / apply()，在大量資料下效能提升 20~50 倍
        title_col = df["title"].fillna("").astype(str) if "title" in df.columns else pd.Series("", index=df.index)
        desc_col = df["description"].fillna("").astype(str) if "description" in df.columns else pd.Series("", index=df.index)
        combined_text = title_col + " " + desc_col

        if "device" not in df.columns or df["device"].isnull().all() or (df["device"] == "N/A").all():
            df["device"] = [
                extract_device_from_text(text) or "未知機台/通用"
                for text in combined_text
            ]
        else:
            # 僅針對空值或無效值的 device 進行補齊
            needs_extract = df["device"].isnull() | df["device"].astype(str).str.strip().isin(["", "N/A", "未知機台/通用"])
            if needs_extract.any():
                df.loc[needs_extract, "device"] = [
                    extract_device_from_text(text) or "未知機台/通用"
                    for text in combined_text[needs_extract]
                ]

        # 4. 確保必要欄位存在，若來源缺少則補預設值
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = "N/A"

        # 5. 確保 created_at 轉換為 datetime (支援 2026/8/25 12:20:26 AM 等格式)
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        # 移除無法解析的時間記錄 (避免後續統計計算出錯)
        invalid_dates = df["created_at"].isnull()
        if invalid_dates.any():
            logger.warning(f"[BaseCaseLoader] ⚠️ 移除 {invalid_dates.sum()} 筆無法解析的時間記錄")
            df = df.dropna(subset=["created_at"])
        
        # 6. 填充缺失值
        df["category"] = df["category"].replace("N/A", "未分類").fillna("未分類")
        df["plant"] = df["plant"].replace("N/A", "未知廠區").fillna("未知廠區")
        df["device"] = df["device"].fillna("未知機台/通用")
        df["title"] = df["title"].fillna("無標題")
        df["description"] = df["description"].fillna("無詳細描述")
        df["system_name"] = df["system_name"].fillna("未分類系統")
        df["reporter"] = df["reporter"].replace("N/A", "未知人員").fillna("未知人員")

        return df[REQUIRED_COLUMNS]


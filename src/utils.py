import logging
import sys

def setup_logging():
    """設定基本日誌格式"""
    # 確保 StreamHandler 使用 UTF-8 (透過 sys.stdout 輸出)
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger()

def fix_windows_encoding():
    """修復 Windows 下的 cp950 編碼問題"""
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

def get_logger(name):
    """取得指定名稱的 logger"""
    return logging.getLogger(name)

import os

def load_dotenv_if_present(env_path: str = "./.env") -> int:
    """
    載入 .env 檔案中的環境變數至 os.environ。
    優先使用 python-dotenv，若未安裝則使用內建輕量解析器作為 fallback。
    回傳成功載入的變數數量。
    """
    if not os.path.exists(env_path):
        return 0

    try:
        from dotenv import load_dotenv
        # load_dotenv 預設不會覆蓋已存在的環境變數 (override=False)
        load_dotenv(dotenv_path=env_path)
    except ImportError:
        # Fallback 簡易解析器
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[7:].strip()
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    # 去除引號
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    if key and key not in os.environ:
                        os.environ[key] = val
        except Exception as e:
            logging.getLogger(__name__).warning(f"解析 .env 檔案失敗: {e}")

    # 計算 .env 中定義的 key 數量
    count = 0
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    count += 1
    except Exception:
        pass
    return count

def mask_secret(secret: str, visible_start: int = 4, visible_end: int = 4) -> str:
    """
    對敏感字串進行遮罩處理 (如: AIzaSy1234567890 -> AIza****7890)
    """
    if not secret:
        return ""
    secret = str(secret).strip()
    if len(secret) <= (visible_start + visible_end):
        return "*" * len(secret)
    return f"{secret[:visible_start]}****{secret[-visible_end:]}"

import calendar
from datetime import date, datetime, timedelta
from typing import Tuple, Optional

def subtract_months(year: int, month: int, n: int) -> Tuple[int, int]:
    """計算 (year, month) 往前推 n 個月後的 (new_year, new_month)"""
    total_months = year * 12 + (month - 1) - n
    new_year = total_months // 12
    new_month = total_months % 12 + 1
    return new_year, new_month

def get_month_last_day(year: int, month: int) -> date:
    """取得指定年月的最後一天"""
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, last_day)

def get_yesterday_range(target_date: Optional[date] = None, history_days: int = 35) -> Tuple[datetime, datetime, date]:
    """
    每日晨會：取得昨日全天 (00:00:00 ~ 23:59:59) 及歷史載入區間
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

    start_date = target_date - timedelta(days=history_days)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time().replace(microsecond=0))
    return start_dt, end_dt, target_date

def get_weekly_range(target_date: Optional[date] = None, history_weeks: int = 8) -> Tuple[datetime, datetime, date]:
    """
    每週課會：取得上週目標日及歷史載入區間 (日曆日 00:00:00 ~ 23:59:59)
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

    start_date = target_date - timedelta(days=history_weeks * 7)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time().replace(microsecond=0))
    return start_dt, end_dt, target_date

def get_last_full_month_range(target_month_str: Optional[str] = None, history_months: int = 6) -> Tuple[datetime, datetime, str]:
    """
    每月課會：取得完整月份 (01 號 00:00:00 ~ 月底 23:59:59) 及歷史載入區間
    若未指定 target_month_str，預設為「已結算的完整上個月」 (例如 8 月跑則預設為 7 月)
    """
    if not target_month_str:
        today = date.today()
        # 上個月的年月
        last_m_year, last_m_month = subtract_months(today.year, today.month, 1)
        target_month_str = f"{last_m_year:04d}-{last_m_month:02d}"
    else:
        target_month_str = str(target_month_str)[:7]
        target_year, target_m = map(int, target_month_str.split("-"))
        last_m_year, last_m_month = target_year, target_m

    # 目標月起訖
    target_last_day = get_month_last_day(last_m_year, last_m_month)
    end_dt = datetime.combine(target_last_day, datetime.max.time().replace(microsecond=0))

    # 歷史起始月 (往前推 history_months)
    hist_start_year, hist_start_month = subtract_months(last_m_year, last_m_month, history_months)
    start_dt = datetime.combine(date(hist_start_year, hist_start_month, 1), datetime.min.time())

    return start_dt, end_dt, target_month_str


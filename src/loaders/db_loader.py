from datetime import datetime
import os
import pandas as pd
from src.loaders.base import BaseCaseLoader

class DatabaseCaseLoader(BaseCaseLoader):
    """
    關聯式資料庫載入器 (未來直接連線公司 Oracle / MSSQL / PostgreSQL / MySQL 時使用)
    需要安裝 sqlalchemy 及相應的 db driver (如 pyodbc, psycopg2, cx_Oracle 等)
    """

    def __init__(self, connection_string: str = "", query_template: str = "", connection_string_env_var: str = ""):
        # 優先使用環境變數，避免密碼寫在設定檔中
        if connection_string_env_var:
            self.connection_string = os.getenv(connection_string_env_var, connection_string)
        else:
            self.connection_string = connection_string
        self.query_template = query_template

    def load_cases(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        try:
            from sqlalchemy import create_engine, text
        except ImportError:
            raise ImportError("請先安裝 sqlalchemy 以啟用資料庫載入器: pip install sqlalchemy")

        engine = create_engine(self.connection_string)

        params = {
            "start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "end_date": end_date.strftime("%Y-%m-%d %H:%M:%S")
        }

        with engine.connect() as conn:
            df = pd.read_sql(text(self.query_template), conn, params=params)

        return self.validate_and_clean(df)

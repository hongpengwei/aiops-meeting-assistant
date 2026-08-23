from typing import Dict, Any
from src.loaders.base import BaseCaseLoader
from src.loaders.csv_loader import CsvCaseLoader
from src.loaders.db_loader import DatabaseCaseLoader
from src.loaders.api_loader import ApiCaseLoader

def create_data_loader(config: Dict[str, Any]) -> BaseCaseLoader:
    """
    工廠方法：根據 config 中的 data_source 設定建立對應的 Loader 物件
    """
    ds_config = config.get("data_source", {})
    ds_type = ds_config.get("type", "csv").lower()

    if ds_type in ("csv", "excel"):
        csv_cfg = ds_config.get("csv", {})
        file_path = csv_cfg.get("file_path", "./data/mock_cases.csv")
        return CsvCaseLoader(file_path=file_path)

    elif ds_type == "database":
        db_cfg = ds_config.get("database", {})
        conn_str = db_cfg.get("connection_string", "")
        query = db_cfg.get("query_template", "")
        return DatabaseCaseLoader(connection_string=conn_str, query_template=query)

    elif ds_type == "api":
        api_cfg = ds_config.get("api", {})
        base_url = api_cfg.get("base_url", "")
        endpoint = api_cfg.get("endpoint", "")
        token_env = api_cfg.get("token_env_var", "CORP_API_TOKEN")
        return ApiCaseLoader(base_url=base_url, endpoint=endpoint, token_env_var=token_env)

    else:
        raise ValueError(f"未知的資料來源型態: {ds_type}，支援的型態有: csv, excel, database, api")

"""
系統連線與環境一鍵健檢模組 (Health Checker)
功能：
1. 檢測 config.yaml 格式與 .env 環境變數載入狀況 (自動遮罩敏感資訊)
2. 檢測資料來源連線 (CSV 檔案讀取、資料庫 SQL 握手、API 端點連通)
3. 檢測 AI 模型服務連線與回應延遲 (Gemini / OpenAI / Custom HTTP)
4. 檢測推播通道 (Teams Webhook 格式、SMTP 伺服器 Socket 連通)
5. 產出清晰的終端診斷報表與故障排除指引
"""

import os
import sys
import time
import socket
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import yaml

from src.utils import load_dotenv_if_present, mask_secret

logger = logging.getLogger(__name__)


@dataclass
class CheckItem:
    category: str      # 類別 (例如: "環境設定", "資料來源", "AI 服務", "推播通道")
    name: str          # 項目名稱 (例如: "Gemini API 連線")
    status: str        # "PASS", "WARN", "FAIL"
    message: str       # 檢測結果摘要
    latency_ms: Optional[float] = None  # 延遲 (毫秒)
    hint: Optional[str] = None          # 排錯指引


class HealthChecker:
    def __init__(self, config_path: str = "./config/config.yaml", env_path: str = "./.env"):
        self.config_path = config_path
        self.env_path = env_path
        self.results: List[CheckItem] = []
        self.config: Dict[str, Any] = {}

    def run_all(self) -> bool:
        """
        執行所有健檢項目
        :return: True 若所有關鍵項目皆通過 (無 FAIL)，False 若有任何 FAIL
        """
        self.results = []
        
        # 1. 載入 .env 與驗證設定檔
        self._check_config_and_env()
        
        # 2. 檢測資料來源
        if self.config:
            self._check_data_source()
        
        # 3. 檢測 AI 服務
        if self.config:
            self._check_ai_service()
        
        # 4. 檢測通知推播
        if self.config:
            self._check_notifications()

        return not any(item.status == "FAIL" for item in self.results)

    def _check_config_and_env(self):
        """1. 環境設定與 .env 檢查"""
        # (1) 檢查 .env
        dotenv_count = load_dotenv_if_present(self.env_path)
        if os.path.exists(self.env_path):
            self.results.append(CheckItem(
                category="環境設定",
                name=".env 環境變數檔",
                status="PASS",
                message=f"已載入 {self.env_path} (包含 {dotenv_count} 個設定變數)"
            ))
        else:
            self.results.append(CheckItem(
                category="環境設定",
                name=".env 環境變數檔",
                status="WARN",
                message="未檢測到 .env 檔案 (系統將直接自系統環境變數讀取金鑰)",
                hint="可複製 .env.example 為 .env 以方便管理本地金鑰與連線字串"
            ))

        # (2) 檢查 config.yaml
        if not os.path.exists(self.config_path):
            self.results.append(CheckItem(
                category="環境設定",
                name="設定檔 (config.yaml)",
                status="FAIL",
                message=f"找不到設定檔: {self.config_path}",
                hint=f"請確認 {self.config_path} 是否存在"
            ))
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
            self.results.append(CheckItem(
                category="環境設定",
                name="設定檔 (config.yaml)",
                status="PASS",
                message=f"成功解析 YAML 設定檔 (模式: {self.config.get('data_source', {}).get('type', '未知')})"
            ))
        except Exception as e:
            self.results.append(CheckItem(
                category="環境設定",
                name="設定檔 (config.yaml)",
                status="FAIL",
                message=f"YAML 解析失敗: {e}",
                hint="請檢查 config.yaml 縮排與語法"
            ))

    def _check_data_source(self):
        """2. 資料來源連線檢查"""
        ds_cfg = self.config.get("data_source", {})
        ds_type = ds_cfg.get("type", "csv").lower()

        if ds_type in ("csv", "excel"):
            csv_path = ds_cfg.get("csv", {}).get("file_path", "./data/mock_cases.csv")
            if os.path.exists(csv_path):
                try:
                    import pandas as pd
                    start_t = time.perf_counter()
                    if ds_type == "csv":
                        df_head = pd.read_csv(csv_path, nrows=5)
                    else:
                        df_head = pd.read_excel(csv_path, nrows=5)
                    latency = (time.perf_counter() - start_t) * 1000.0

                    self.results.append(CheckItem(
                        category="資料來源",
                        name=f"{ds_type.upper()} 檔案讀取",
                        status="PASS",
                        message=f"檔案正常存在 ({csv_path})，欄位包含: {', '.join(df_head.columns[:4])}...",
                        latency_ms=latency
                    ))
                except Exception as e:
                    self.results.append(CheckItem(
                        category="資料來源",
                        name=f"{ds_type.upper()} 檔案讀取",
                        status="FAIL",
                        message=f"無法讀取檔案內容: {e}",
                        hint=f"請檢查檔案權限或格式是否損毀"
                    ))
            else:
                self.results.append(CheckItem(
                    category="資料來源",
                    name=f"{ds_type.upper()} 檔案存在性",
                    status="WARN",
                    message=f"檔案不存在: {csv_path} (首次執行時系統將自動生成測試數據)",
                    hint="執行 python scripts/generate_mock_data.py 可生成測試數據"
                ))

        elif ds_type == "database":
            db_cfg = ds_cfg.get("database", {})
            env_var = db_cfg.get("connection_string_env_var", "DB_CONNECTION_STRING")
            conn_str = os.getenv(env_var, "")

            if not conn_str:
                self.results.append(CheckItem(
                    category="資料來源",
                    name="資料庫連線變數",
                    status="FAIL",
                    message=f"環境變數 {env_var} 未設定！",
                    hint=f"請在 .env 或系統環境變數中設定 {env_var}='mssql+pyodbc://...'"
                ))
            else:
                masked_conn = mask_secret(conn_str, 10, 6)
                try:
                    from sqlalchemy import create_engine, text
                    start_t = time.perf_counter()
                    engine = create_engine(conn_str, connect_args={"timeout": 5} if "mssql" in conn_str else {})
                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    latency = (time.perf_counter() - start_t) * 1000.0

                    self.results.append(CheckItem(
                        category="資料來源",
                        name="資料庫 SQL 連線",
                        status="PASS",
                        message=f"成功連線至資料庫 ({masked_conn})",
                        latency_ms=latency
                    ))
                except ImportError:
                    self.results.append(CheckItem(
                        category="資料來源",
                        name="資料庫驅動套件",
                        status="WARN",
                        message="缺少 sqlalchemy 套件，無法進行資料庫連線測試",
                        hint="請執行 pip install sqlalchemy pyodbc"
                    ))
                except Exception as e:
                    self.results.append(CheckItem(
                        category="資料來源",
                        name="資料庫 SQL 連線",
                        status="FAIL",
                        message=f"資料庫連線失敗: {e}",
                        hint="請檢查資料庫伺服器網路、帳密與連線字串"
                    ))

        elif ds_type == "api":
            api_cfg = ds_cfg.get("api", {})
            base_url = api_cfg.get("base_url", "")
            token_env = api_cfg.get("token_env_var", "CORP_API_TOKEN")
            token = os.getenv(token_env, "")

            if not base_url:
                self.results.append(CheckItem(
                    category="資料來源",
                    name="API 設定",
                    status="FAIL",
                    message="未設定 api.base_url",
                    hint="請在 config.yaml 中填入 Ticket API base_url"
                ))
            else:
                try:
                    import requests
                    start_t = time.perf_counter()
                    headers = {"Authorization": f"Bearer {token}"} if token else {}
                    resp = requests.get(base_url, headers=headers, timeout=5)
                    latency = (time.perf_counter() - start_t) * 1000.0
                    self.results.append(CheckItem(
                        category="資料來源",
                        name="API 端點連通性",
                        status="PASS" if resp.status_code < 500 else "WARN",
                        message=f"HTTP 回應碼 {resp.status_code} ({base_url})",
                        latency_ms=latency
                    ))
                except Exception as e:
                    self.results.append(CheckItem(
                        category="資料來源",
                        name="API 端點連通性",
                        status="WARN",
                        message=f"無法連通 API 端點: {e}",
                        hint="請確認公司 VPN 是否開啟或 API 端點 URL 是否正確"
                    ))

    def _check_ai_service(self):
        """3. AI 模型服務檢查"""
        ai_cfg = self.config.get("ai", {})
        provider = ai_cfg.get("provider", "gemini").lower()
        model_name = ai_cfg.get("model_name", "gemini-2.5-flash")
        env_var = ai_cfg.get("api_key_env_var", "GEMINI_API_KEY")
        
        # 讀取 Key
        api_key = os.getenv(env_var, "").strip()
        if not api_key:
            api_key = str(ai_cfg.get("api_key", "")).strip()

        if provider == "mock":
            self.results.append(CheckItem(
                category="AI 服務",
                name="AI 模型引擎",
                status="PASS",
                message="目前設定為啟發式模擬模式 (Mock AI)，無需金鑰與外部連線"
            ))
            return

        if not api_key:
            self.results.append(CheckItem(
                category="AI 服務",
                name=f"AI 金鑰 ({provider})",
                status="WARN",
                message=f"未偵測到環境變數 {env_var} 或 API 金鑰！(執行時將自動 Fallback 降級為啟發式分析)",
                hint=f"請在 .env 中填入 {env_var}='your_api_key'"
            ))
            return

        masked_key = mask_secret(api_key, 6, 4)

        if provider == "gemini":
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                start_t = time.perf_counter()
                # 發送極輕量測試請求
                response = client.models.generate_content(
                    model=model_name,
                    contents="Say OK"
                )
                latency = (time.perf_counter() - start_t) * 1000.0
                reply_text = (response.text or "").strip()[:20]

                self.results.append(CheckItem(
                    category="AI 服務",
                    name=f"Google Gemini ({model_name})",
                    status="PASS",
                    message=f"API 連通成功 (Key: {masked_key}, 回應: '{reply_text}')",
                    latency_ms=latency
                ))
            except ImportError:
                self.results.append(CheckItem(
                    category="AI 服務",
                    name="Google GenAI SDK",
                    status="WARN",
                    message="未安裝 google-genai 套件",
                    hint="請執行 pip install google-genai"
                ))
            except Exception as e:
                self.results.append(CheckItem(
                    category="AI 服務",
                    name=f"Google Gemini ({model_name})",
                    status="WARN",
                    message=f"API 調用失敗: {e} (執行時將自動 Fallback 為啟發式分析)",
                    hint="請檢查 GEMINI_API_KEY 是否有效、網路連線或 API 配額"
                ))

        elif provider in ("openai", "openai_compatible", "azure", "internal_llm"):
            import requests
            base_url = ai_cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
            url = f"{base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            headers.update(ai_cfg.get("custom_headers", {}))
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5
            }
            try:
                start_t = time.perf_counter()
                resp = requests.post(url, headers=headers, json=payload, timeout=8)
                latency = (time.perf_counter() - start_t) * 1000.0
                if resp.status_code == 200:
                    self.results.append(CheckItem(
                        category="AI 服務",
                        name=f"OpenAI 相容端點 ({model_name})",
                        status="PASS",
                        message=f"API 連通成功 (Key: {masked_key})",
                        latency_ms=latency
                    ))
                else:
                    self.results.append(CheckItem(
                        category="AI 服務",
                        name=f"OpenAI 相容端點 ({model_name})",
                        status="WARN",
                        message=f"HTTP 回應碼 {resp.status_code}: {resp.text[:80]}",
                        hint="請檢查 base_url、金鑰權限與模型名稱"
                    ))
            except Exception as e:
                self.results.append(CheckItem(
                    category="AI 服務",
                    name=f"OpenAI 相容端點 ({model_name})",
                    status="WARN",
                    message=f"無法連通 LLM Gateway: {e}",
                    hint="請檢查 LLM Gateway 伺服器是否運行或 VPN 是否連線"
                ))

    def _check_notifications(self):
        """4. 推播通道檢查"""
        notif_cfg = self.config.get("notifications", {})

        # (1) 本地 output 目錄
        output_dir = notif_cfg.get("local", {}).get("output_dir", "./output")
        try:
            os.makedirs(output_dir, exist_ok=True)
            test_file = os.path.join(output_dir, ".health_check_test")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("test")
            if os.path.exists(test_file):
                os.remove(test_file)
            self.results.append(CheckItem(
                category="推播通道",
                name="本地報告目錄",
                status="PASS",
                message=f"目錄可正常寫入: {os.path.abspath(output_dir)}"
            ))
        except Exception as e:
            self.results.append(CheckItem(
                category="推播通道",
                name="本地報告目錄",
                status="FAIL",
                message=f"無法寫入本地報告目錄: {e}",
                hint=f"請檢查 {output_dir} 資料夾權限"
            ))

        # (2) Microsoft Teams
        teams_cfg = notif_cfg.get("teams", {})
        if teams_cfg.get("enabled", False):
            webhook_url = teams_cfg.get("webhook_url", "").strip()
            if webhook_url.startswith("https://"):
                self.results.append(CheckItem(
                    category="推播通道",
                    name="Teams Webhook",
                    status="PASS",
                    message=f"已啟用且格式合法 ({mask_secret(webhook_url, 25, 6)})"
                ))
            else:
                self.results.append(CheckItem(
                    category="推播通道",
                    name="Teams Webhook",
                    status="WARN",
                    message="已啟用但 webhook_url 似乎為空或格式不符",
                    hint="請在 config.yaml 填入有效的 Teams Incoming Webhook URL"
                ))
        else:
            self.results.append(CheckItem(
                category="推播通道",
                name="Teams Webhook",
                status="PASS",
                message="未啟用 (如需開啟請在 config.yaml 中將 notifications.teams.enabled 設為 true)"
            ))

        # (3) SMTP Email
        email_cfg = notif_cfg.get("email", {})
        if email_cfg.get("enabled", False):
            smtp_host = email_cfg.get("smtp_host", "smtp.company.com")
            smtp_port = int(email_cfg.get("smtp_port", 587))
            try:
                start_t = time.perf_counter()
                sock = socket.create_connection((smtp_host, smtp_port), timeout=4)
                sock.close()
                latency = (time.perf_counter() - start_t) * 1000.0
                self.results.append(CheckItem(
                    category="推播通道",
                    name="SMTP 郵件伺服器",
                    status="PASS",
                    message=f"Socket 連線成功 ({smtp_host}:{smtp_port})",
                    latency_ms=latency
                ))
            except Exception as e:
                self.results.append(CheckItem(
                    category="推播通道",
                    name="SMTP 郵件伺服器",
                    status="WARN",
                    message=f"無法建立 TCP Socket 連線至 {smtp_host}:{smtp_port} ({e})",
                    hint="請確認 SMTP 伺服器位址或公司防火牆設定"
                ))
        else:
            self.results.append(CheckItem(
                category="推播通道",
                name="SMTP 郵件伺服器",
                status="PASS",
                message="未啟用 (如需開啟請在 config.yaml 中將 notifications.email.enabled 設為 true)"
            ))

    def print_summary(self):
        """格式化終端輸出診斷報告"""
        print("\n" + "=" * 70)
        print("🩺 AIOps Ops Insight Assistant - 系統連線與環境健檢報告")
        print("=" * 70)

        # 分組輸出
        categories = ["環境設定", "資料來源", "AI 服務", "推播通道"]
        for cat in categories:
            items = [item for item in self.results if item.category == cat]
            if not items:
                continue
            print(f"\n📂 【{cat}】")
            for item in items:
                if item.status == "PASS":
                    badge = "✅ [PASS]"
                elif item.status == "WARN":
                    badge = "⚠️  [WARN]"
                else:
                    badge = "❌ [FAIL]"
                
                lat_str = f" ({item.latency_ms:.0f}ms)" if item.latency_ms is not None else ""
                print(f"  {badge} {item.name:<24}: {item.message}{lat_str}")
                if item.hint and item.status in ("WARN", "FAIL"):
                    print(f"       ↳ 💡 建議: {item.hint}")

        # 計算統計
        pass_count = sum(1 for i in self.results if i.status == "PASS")
        warn_count = sum(1 for i in self.results if i.status == "WARN")
        fail_count = sum(1 for i in self.results if i.status == "FAIL")

        print("\n" + "-" * 70)
        status_banner = "🎉 系統狀態良好，可隨時投入生產排程！" if fail_count == 0 else "🚨 發現關鍵失敗項目，請依照上方建議修復後再啟用排程。"
        print(f"📊 健檢統計：{pass_count} 通過 [PASS]  |  {warn_count} 警告 [WARN]  |  {fail_count} 失敗 [FAIL]")
        print(f"👉 總結：{status_banner}")
        print("=" * 70 + "\n")

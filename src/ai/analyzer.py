import os
from typing import Dict, Any, List
import pandas as pd
import requests
import logging
from src.ai.prompts import (
    CASE_ANALYSIS_SYSTEM_PROMPT, 
    CASE_ANALYSIS_USER_PROMPT_TEMPLATE,
    CATEGORY_ANALYSIS_USER_PROMPT_TEMPLATE
)

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """
    AI 案件分析器：負責調用 LLM 對異常系統/類別的 Case 描述進行語意分群與會議摘要
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("ai", {})
        self.provider = self.config.get("provider", "gemini").lower()
        self.model_name = self.config.get("model_name", "gemini-2.5-flash")
        self.api_key_env_var = self.config.get("api_key_env_var", "GEMINI_API_KEY")
        self.max_cases = self.config.get("max_cases_to_analyze", 50)
        self.api_key = os.getenv(self.api_key_env_var, "").strip()

        self._gemini_client = None
        if self.provider == "gemini" and self.api_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.api_key)
            except ImportError:
                logger.error("無法匯入 google.genai，請確認是否安裝。")

    def _format_case_lines(self, sample_df: pd.DataFrame) -> str:
        case_lines = []
        for idx, (_, row) in enumerate(sample_df.iterrows(), 1):
            plant = row.get("plant", "未知廠區")
            device = row.get("device", "未知設備")
            title = row.get("title", "")
            desc = row.get("description", "")
            reporter = row.get("reporter", "匿名")
            category = row.get("category", "")
            cat_str = f" | 類別: {category}" if category else ""
            case_lines.append(
                f"[{idx}] 廠區: {plant} | 設備: {device}{cat_str} | 提報人: {reporter}\n"
                f"    標題: {title}\n"
                f"    描述: {desc}"
            )
        return "\n\n".join(case_lines)

    def analyze_system_cases(
        self, 
        system_name: str, 
        target_period_str: str, 
        cases_df: pd.DataFrame
    ) -> str:
        """
        針對特定異常系統的案件描述進行 AI 深度歸因分析 (晨會 / 課會)
        """
        if cases_df.empty:
            return "無詳細案件資料可供分析。"

        sample_df = cases_df.head(self.max_cases)
        cases_text = self._format_case_lines(sample_df)

        user_prompt = CASE_ANALYSIS_USER_PROMPT_TEMPLATE.format(
            system_name=system_name,
            target_period_str=target_period_str,
            case_count=len(cases_df),
            displayed_count=len(sample_df),
            cases_text=cases_text
        )

        if not self.api_key or self.provider == "mock":
            logger.info(f"[AI Analyzer] ℹ️ 未檢測到 {self.api_key_env_var} 或設定為 Mock 模式，使用智慧啟發式 (Mock AI) 分析引擎...")
            return self._mock_heuristic_analysis(system_name, target_period_str, cases_df)

        try:
            if self.provider == "gemini":
                return self._call_gemini_api(user_prompt)
            elif self.provider in ("openai", "azure", "openai_compatible", "internal_llm"):
                return self._call_openai_compatible_api(user_prompt)
            elif self.provider == "custom_http":
                return self._call_custom_http_api(user_prompt)
            else:
                return self._call_gemini_api(user_prompt)
        except (requests.exceptions.RequestException, TimeoutError, ConnectionError, RuntimeError) as e:
            logger.warning(f"[AI Analyzer] ⚠️ AI API ({self.provider}) 調用失敗 ({e})，切換至智慧啟發式分析模式。")
            return self._mock_heuristic_analysis(system_name, target_period_str, cases_df)

    def analyze_category_cases(
        self,
        system_name: str,
        category_name: str,
        target_period_str: str,
        cases_df: pd.DataFrame
    ) -> str:
        """
        針對月報中暴增的特定「系統 + 類別」案件進行深度歸因分析 (月報專用)
        """
        if cases_df.empty:
            return f"無【{category_name}】相關詳細案件資料可供分析。"

        sample_df = cases_df.head(self.max_cases)
        cases_text = self._format_case_lines(sample_df)

        user_prompt = CATEGORY_ANALYSIS_USER_PROMPT_TEMPLATE.format(
            system_name=system_name,
            category_name=category_name,
            target_period_str=target_period_str,
            case_count=len(cases_df),
            displayed_count=len(sample_df),
            cases_text=cases_text
        )

        if not self.api_key or self.provider == "mock":
            logger.info(f"[AI Analyzer] ℹ️ 未檢測到 {self.api_key_env_var} 或設定為 Mock 模式，使用智慧啟發式類別分析引擎...")
            return self._mock_category_analysis(system_name, category_name, target_period_str, cases_df)

        try:
            if self.provider == "gemini":
                return self._call_gemini_api(user_prompt)
            elif self.provider in ("openai", "azure", "openai_compatible", "internal_llm"):
                return self._call_openai_compatible_api(user_prompt)
            elif self.provider == "custom_http":
                return self._call_custom_http_api(user_prompt)
            else:
                return self._call_gemini_api(user_prompt)
        except (requests.exceptions.RequestException, TimeoutError, ConnectionError, RuntimeError) as e:
            logger.warning(f"[AI Analyzer] ⚠️ AI API ({self.provider}) 調用失敗 ({e})，切換至智慧啟發式類別分析模式。")
            return self._mock_category_analysis(system_name, category_name, target_period_str, cases_df)

    def _call_gemini_api(self, user_prompt: str) -> str:
        """調用 Google GenAI SDK (Gemini)"""
        if not self._gemini_client:
            raise RuntimeError("Gemini Client 未初始化或缺少 google.genai 模組。")
            
        import time
        for attempt in range(3):
            try:
                response = self._gemini_client.models.generate_content(
                    model=self.model_name,
                    contents=f"{CASE_ANALYSIS_SYSTEM_PROMPT}\n\n{user_prompt}"
                )
                return response.text
            except Exception as e:
                if attempt == 2:
                    raise
                wait = 2 ** (attempt + 1)
                logger.warning(f'API 調用失敗，{wait} 秒後重試 (attempt {attempt+1}/3): {e}')
                time.sleep(wait)

    def _call_openai_compatible_api(self, user_prompt: str) -> str:
        """
        調用 OpenAI 相容端點 (支援 OpenAI, Azure OpenAI, Ollama, vLLM, 公司自建的私有 LLM Gateway)
        """
        import requests
        base_url = self.config.get("base_url", "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        custom_headers = self.config.get("custom_headers", {})
        headers.update(custom_headers)

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": CASE_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }

        import time
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt == 2:
                    raise
                wait = 2 ** (attempt + 1)
                logger.warning(f'API 調用失敗，{wait} 秒後重試 (attempt {attempt+1}/3): {e}')
                time.sleep(wait)

    def _call_custom_http_api(self, user_prompt: str) -> str:
        """調用公司完全自訂格式的 HTTP REST API"""
        import requests
        url = self.config.get("custom_endpoint_url", "")
        headers = self.config.get("custom_headers", {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "prompt": f"{CASE_ANALYSIS_SYSTEM_PROMPT}\n\n{user_prompt}",
            "model": self.model_name
        }

        import time
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                return data.get("text") or data.get("response") or data.get("output") or str(data)
            except Exception as e:
                if attempt == 2:
                    raise
                wait = 2 ** (attempt + 1)
                logger.warning(f'API 調用失敗，{wait} 秒後重試 (attempt {attempt+1}/3): {e}')
                time.sleep(wait)

    def _mock_heuristic_analysis(
        self, 
        system_name: str, 
        target_period_str: str, 
        cases_df: pd.DataFrame
    ) -> str:
        """
        智慧啟發式模擬分析 (晨會/課會模式) — 現象分群歸納格式
        """
        total = len(cases_df)
        sample_df = cases_df.head(self.max_cases)

        # 統計熱點
        plant_counts = cases_df["plant"].value_counts()
        top_plant = plant_counts.index[0] if len(plant_counts) > 0 else "未知廠區"
        top_plant_count = plant_counts.iloc[0] if len(plant_counts) > 0 else 0
        top_plant_pct = (top_plant_count / total * 100) if total > 0 else 0

        device_counts = cases_df["device"].value_counts()
        top_device = device_counts.index[0] if len(device_counts) > 0 else "未知機台"

        # 分群識別
        critical_keywords = ["中斷", "停線", "當機", "無法", "失敗", "crash", "down", "error", "逾時", "timeout", "卡站", "緊急"]
        cluster_a_cases = []
        routine_cases = []

        for idx, (_, row) in enumerate(sample_df.iterrows(), 1):
            desc = str(row.get("description", ""))
            title = str(row.get("title", ""))
            combined = (title + " " + desc).lower()

            if any(kw in combined for kw in critical_keywords):
                cluster_a_cases.append(f"#{idx}")
            else:
                routine_cases.append(f"#{idx}")

        cluster_a_str = ", ".join(cluster_a_cases[:5]) if cluster_a_cases else "無明顯群聚"
        if len(cluster_a_cases) > 5:
            cluster_a_str += f" 等共 {len(cluster_a_cases)} 筆"

        routine_count = max(0, total - len(cluster_a_cases))
        routine_sample = ", ".join(routine_cases[:3]) if routine_cases else "無"

        return f"""### 1. 🔍 案件現象分群與熱點分析 (Pattern Breakdown)

- **🔥 群組 A：{top_plant} / {top_device} 批次操作異常與通訊受阻**
  - **分佈範圍**：高度集中於 **【{top_plant} / {top_device}】**（佔比約 {top_plant_pct:.0f}%，共 {top_plant_count} 件）
  - **主要現象**：現場人員集中反映機台通訊逾時、狀態鎖定或派工受阻
  - **涉及案件**：Case {cluster_a_str}
  - **推測根因**：{top_plant} 之 {top_device} 近期維護或通訊交握異常，導致背景服務佇列阻塞

- **🟢 常態/零星個案**（共 {routine_count} 件，如 Case {routine_sample}）：
  - 屬於個別廠區之日常例行維運（如密碼重設、一般權限開通與單一操作諮詢），經評估無群聚性系統風險，維持日常維運 SOP 處理。

### 2. 📢 會議發言重點與行動建議 (Action Items)

1. 【現況回報】{target_period_str} {system_name} 案件數顯著偏高（共 {total} 件），主因集中於 {top_plant} 的 {top_device}。
2. 【建議處置】會後由負責 {top_plant} 的維運工程師協同廠端 IT 檢查 {top_device} 連線品質與通訊參數。"""

    def _mock_category_analysis(
        self,
        system_name: str,
        category_name: str,
        target_period_str: str,
        cases_df: pd.DataFrame
    ) -> str:
        """
        智慧啟發式模擬類別分析 (月報模式專用) — 現象分群歸納格式
        """
        total = len(cases_df)
        sample_df = cases_df.head(self.max_cases)

        plant_counts = cases_df["plant"].value_counts()
        top_plant = plant_counts.index[0] if len(plant_counts) > 0 else "未知廠區"
        top_plant_count = plant_counts.iloc[0] if len(plant_counts) > 0 else 0
        top_plant_pct = (top_plant_count / total * 100) if total > 0 else 0

        device_counts = cases_df["device"].value_counts()
        top_device = device_counts.index[0] if len(device_counts) > 0 else "未知機台"

        # 分群識別
        critical_keywords = ["中斷", "停線", "當機", "無法", "失敗", "crash", "down", "error", "逾時", "timeout", "卡站", "緊急"]
        cluster_a_cases = []
        routine_cases = []

        for idx, (_, row) in enumerate(sample_df.iterrows(), 1):
            desc = str(row.get("description", ""))
            title = str(row.get("title", ""))
            combined = (title + " " + desc).lower()

            if any(kw in combined for kw in critical_keywords):
                cluster_a_cases.append(f"#{idx}")
            else:
                routine_cases.append(f"#{idx}")

        cluster_a_str = ", ".join(cluster_a_cases[:5]) if cluster_a_cases else "無明顯群聚"
        if len(cluster_a_cases) > 5:
            cluster_a_str += f" 等共 {len(cluster_a_cases)} 筆"

        routine_count = max(0, total - len(cluster_a_cases))
        routine_sample = ", ".join(routine_cases[:3]) if routine_cases else "無"

        return f"""### 1. 🔍 【{category_name}】問題現象分群 (Pattern Breakdown)

- **🔥 主要集中問題：{top_plant} / {top_device} 之【{category_name}】頻發異常**
  - **熱點分佈**：主要集中於 **【{top_plant} / {top_device}】**（佔比約 {top_plant_pct:.0f}%，共 {top_plant_count} 件）
  - **現象描述**：執行【{category_name}】流程時頻繁出現交握逾時、佇列積壓或操作卡站
  - **涉及案件**：Case {cluster_a_str} （可供調閱現場描述）
  - **可能導因**：{top_plant} 該設備於本月份發生通訊參數設定異動或背景服務資源飽和

- **🟢 分散/常態個案**（共 {routine_count} 件，如 Case {routine_sample}）：
  - 屬於分散於其他廠區之獨立單一事件，無明顯群聚或跨機台擴散趨勢，維持例行維運監控。

### 2. 📢 月會改善行動方案 (Action Items)

1. 【短期措施】請負責 {system_name} 的維運同仁針對 {top_plant} 的 {top_device} 進行通訊參數校驗與快取清理。
2. 【長期預防】建立【{category_name}】專屬的預警閾值與定期健檢機制，避免跨月重複累積。"""




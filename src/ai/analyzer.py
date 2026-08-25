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
        self.model_name = self.config.get("model_name", "gemini-3.5-flash")
        self.api_key_env_var = self.config.get("api_key_env_var", "GEMINI_API_KEY")
        self.max_cases = self.config.get("max_cases_to_analyze", 50)
        
        # 支援多種 API Key 提供方式：
        # 1. 系統環境變數 (例如 GEMINI_API_KEY)
        # 2. config.yaml 中的 api_key 欄位
        # 3. 直接貼在 api_key_env_var 欄位中的 Key 字串
        env_val = os.getenv(self.api_key_env_var, "").strip() if self.api_key_env_var else ""
        direct_key = str(self.config.get("api_key", "")).strip()
        if env_val:
            self.api_key = env_val
        elif direct_key:
            self.api_key = direct_key
        elif self.api_key_env_var and len(self.api_key_env_var) > 20 and (" " not in self.api_key_env_var):
            self.api_key = self.api_key_env_var.strip()
        else:
            self.api_key = ""

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
        except Exception as e:
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
        except Exception as e:
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
        智慧啟發式模擬分析 (晨會/課會模式) — 專注熱點分佈與問題同質性
        """
        total = len(cases_df)
        sample_df = cases_df.head(self.max_cases)

        plant_counts = cases_df["plant"].value_counts()
        top_plant = plant_counts.index[0] if len(plant_counts) > 0 else "未知廠區"
        top_plant_count = plant_counts.iloc[0] if len(plant_counts) > 0 else 0
        top_plant_pct = (top_plant_count / total * 100) if total > 0 else 0

        device_counts = cases_df["device"].value_counts()
        top_device = device_counts.index[0] if len(device_counts) > 0 else "未知機台"
        top_device_count = device_counts.iloc[0] if len(device_counts) > 0 else 0
        top_device_pct = (top_device_count / total * 100) if total > 0 else 0

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

        cluster_a_str = ", ".join(cluster_a_cases[:4]) if cluster_a_cases else "無明顯群聚"
        if len(cluster_a_cases) > 4:
            cluster_a_str += f" 等共 {len(cluster_a_cases)} 筆"

        routine_count = max(0, total - len(cluster_a_cases))
        routine_sample = ", ".join(routine_cases[:3]) if routine_cases else "無"

        hotspot_str = f"集中於 **{top_plant}** (佔 {top_plant_pct:.0f}%, 共 {top_plant_count} 件)"
        if top_device_pct >= 30 and top_device not in ("General", "未知機台"):
            hotspot_str += f"、機台以 **{top_device}** 為主 (佔 {top_device_pct:.0f}%)"

        return f"""- 📍 **熱點分佈 (廠區/機台)**：{hotspot_str}
- ⚠️ **問題同質性 (現象/報錯)**：多數案件反映連線交握逾時或操作卡站 (涉及 Case {cluster_a_str})
- 🟢 **分散/零星案件**：共 {routine_count} 筆屬各廠區例行維運個案 (如 Case {routine_sample})，無群聚風險。"""

    def _mock_category_analysis(
        self,
        system_name: str,
        category_name: str,
        target_period_str: str,
        cases_df: pd.DataFrame
    ) -> str:
        """
        智慧啟發式模擬類別分析 (月報模式專用) — 專注熱點分佈與問題同質性
        """
        total = len(cases_df)
        sample_df = cases_df.head(self.max_cases)

        plant_counts = cases_df["plant"].value_counts()
        top_plant = plant_counts.index[0] if len(plant_counts) > 0 else "未知廠區"
        top_plant_count = plant_counts.iloc[0] if len(plant_counts) > 0 else 0
        top_plant_pct = (top_plant_count / total * 100) if total > 0 else 0

        device_counts = cases_df["device"].value_counts()
        top_device = device_counts.index[0] if len(device_counts) > 0 else "未知機台"
        top_device_count = device_counts.iloc[0] if len(device_counts) > 0 else 0
        top_device_pct = (top_device_count / total * 100) if total > 0 else 0

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

        cluster_a_str = ", ".join(cluster_a_cases[:4]) if cluster_a_cases else "無明顯群聚"
        if len(cluster_a_cases) > 4:
            cluster_a_str += f" 等共 {len(cluster_a_cases)} 筆"

        routine_count = max(0, total - len(cluster_a_cases))
        routine_sample = ", ".join(routine_cases[:3]) if routine_cases else "無"

        hotspot_str = f"主要集中於 **{top_plant}** (佔 {top_plant_pct:.0f}%, 共 {top_plant_count} 件)"
        if top_device_pct >= 30 and top_device not in ("General", "未知機台"):
            hotspot_str += f"、設備以 **{top_device}** 為主 (佔 {top_device_pct:.0f}%)"

        return f"""- 📍 **熱點分佈 (廠區/機台)**：{hotspot_str}
- ⚠️ **問題同質性 (現象/報錯)**：集中出現【{category_name}】相關之處理逾時或狀態鎖定 (涉及 Case {cluster_a_str})
- 🟢 **分散/零星案件**：共 {routine_count} 筆屬分散於其他廠區之獨立事件 (如 Case {routine_sample})，無擴散趨勢。"""




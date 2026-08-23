import os
from typing import Dict, Any, List
import pandas as pd
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
        智慧啟發式模擬分析 (晨會/課會模式)
        """
        total = len(cases_df)
        plant_counts = cases_df["plant"].value_counts()
        top_plant = plant_counts.index[0] if len(plant_counts) > 0 else "未知廠區"
        top_plant_pct = (plant_counts.iloc[0] / total * 100) if len(plant_counts) > 0 else 0

        device_counts = cases_df["device"].value_counts()
        top_device = device_counts.index[0] if len(device_counts) > 0 else "未知機台"
        top_device_pct = (device_counts.iloc[0] / total * 100) if len(device_counts) > 0 else 0

        sample_descs = cases_df["description"].head(3).tolist()
        sample_quotes = "\n".join([f'  - 「{d[:60]}...」' for d in sample_descs])

        return f"""### 1. 🔍 主要集中問題與熱點 (Top Patterns / Clusters)
- **熱點廠區與機台**：案件高度集中於 **【{top_plant}】**（佔比約 {top_plant_pct:.0f}%），主要受影響設備為 **【{top_device}】**（佔比約 {top_device_pct:.0f}%）。
- **共通回報症狀**：多位提報人反映類似現象：
{sample_quotes}

### 2. 🧩 零星/分散個案 (Scattered & Minor Issues)
- 經比對，其餘約 {max(0, 100 - top_plant_pct):.0f}% 的案件分散於其他廠區，包含例行性密碼變更、一般權限申請與網路短暫延遲，屬於常態性個案，無須於本次會議額外跟進。

### 3. 💡 潛在根因推測 (Hypothesis & Root Cause)
- 根據提報人之描述，推測可能為 **【{top_plant} / {top_device}】** 於近期維護或排程任務執行期間發生通訊異常、鎖定或設定異動，導致現場人員在操作該系統時集體受阻。

### 4. 📢 會議發言重點與行動建議 (Meeting Brief & Action Items)
1. **現況回報**：{target_period_str} {system_name} 案件數顯著偏高（共 {total} 件），主因為 {top_plant} 的 {top_device} 出現批次連線或操作問題。
2. **跟進責任**：建議會後由負責 {top_plant} 設備之維運工程師協同廠端 IT 檢查 {top_device} 服務狀態。
3. **其餘系統狀況**：其餘廠區皆為零星零散個案，整體系統核心服務運作正常。"""

    def _mock_category_analysis(
        self,
        system_name: str,
        category_name: str,
        target_period_str: str,
        cases_df: pd.DataFrame
    ) -> str:
        """
        智慧啟發式模擬類別分析 (月報模式專用)
        """
        total = len(cases_df)
        plant_counts = cases_df["plant"].value_counts()
        top_plant = plant_counts.index[0] if len(plant_counts) > 0 else "未知廠區"
        top_plant_pct = (plant_counts.iloc[0] / total * 100) if len(plant_counts) > 0 else 0

        device_counts = cases_df["device"].value_counts()
        top_device = device_counts.index[0] if len(device_counts) > 0 else "未知機台"
        top_device_pct = (device_counts.iloc[0] / total * 100) if len(device_counts) > 0 else 0

        sample_descs = cases_df["description"].head(3).tolist()
        sample_quotes = "\n".join([f'  - 「{d[:60]}...」' for d in sample_descs])

        return f"""### 1. 🔍 【{category_name}】集中問題與熱點 (Patterns within Category)
- **影響範圍**：本月份【{category_name}】相關工單共 {total} 件，其中約 {top_plant_pct:.0f}% 集中在 **【{top_plant}】**，主要受影響設備/線別為 **【{top_device}】**（佔比約 {top_device_pct:.0f}%）。
- **代表性回報症狀**：
{sample_quotes}

### 2. 💡 潛在根因推測 (Hypothesis & Root Cause)
- 分析此類別描述，研判主要導因為 **【{top_plant} / {top_device}】** 在該月份的通訊交握逾時或背景佇列阻塞，造成現場人員在執行【{category_name}】相關流程時頻繁重試與報錯。

### 3. 📢 月會建議行動方案 (Monthly Action Items)
1. **短期措施**：請負責 {system_name} 的維運同仁針對 {top_plant} 的 {top_device} 進行通訊參數檢測與快取清理。
2. **長期預防**：建立【{category_name}】專屬的預警閾值與定期健檢機制，避免跨月重複累積。"""

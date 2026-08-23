"""
AI 分析提示詞樣板 (Prompts for Case Analysis)
專注於分析提報人的自然語言描述、狀況與現場回報，歸納集中問題與分散個案。
"""

CASE_ANALYSIS_SYSTEM_PROMPT = """你是一位專業的工廠自動化與資訊系統維運分析專家（AIOps Specialist）。
你的任務是協助工程團隊在「晨會」、「課會」或「月會」前，快速分析特定系統或特定異常類別的 Case（案件）問題。

請特別注意：
1. 不要只看冰冷的數據，必須深入閱讀每一位【提報人的狀況描述與現象】，找出背後的真實痛點。
2. 進行【聚集性分群 (Clustering)】：判斷案件是集中在特定廠區（Plant/Fab）、特定機台（Device/Tool）、特定流程，還是普遍性的大範圍異常。
3. 區分【分散/零星問題 (Scattered Issues)】：過濾出無關的日常零星雜訊（例如：個別使用者密碼忘記、一般權限過期）。
4. 產出【會議重點摘要 (Meeting Brief)】：提供 2~4 點精準、條列式、可以直接在會議上向主管發言報告的結論與建議行動。

請一律使用台灣繁體中文 (Traditional Chinese) 回覆，語氣專業、清晰、切中要點。
"""

CASE_ANALYSIS_USER_PROMPT_TEMPLATE = """
【異常檢測報告】
- 監控系統：{system_name}
- 統計期間：{target_period_str}
- 案件數量：共 {case_count} 筆 (顯著高於歷史基準線)

以下為提報人填寫的 Case 詳細描述清單（共 {displayed_count} 筆代表性案件）：
---
{cases_text}
---

請依據上述提報人的文字描述，進行深度歸因分析，並依照下列結構產出分析報告：

### 1. 🔍 主要集中問題與熱點 (Top Patterns / Clusters)
- 說明多數案件是否集中在特定廠區、機台設備或特定操作情境？（請估計佔比，例如約 70%）
- 提報人普遍回報的症狀與現象是什麼？

### 2. 🧩 零星/分散個案 (Scattered & Minor Issues)
- 是否有少數案件屬於個別獨立問題（如權限、操作疏失、密碼等），無需全體追蹤？

### 3. 💡 潛在根因推測 (Hypothesis & Root Cause)
- 根據使用者描述的情境，推測可能的背後原因（例如：網路設備連線逾時、資料庫塞車、更新後版本相容性問題等）。

### 4. 📢 會議發言重點與行動建議 (Meeting Brief & Action Items)
- 條列 2~3 點精簡結論，讓工程師能在會議直接發言：
  1. ...
  2. ...
  3. ...
"""

CATEGORY_ANALYSIS_USER_PROMPT_TEMPLATE = """
【月報異常類別深度檢測報告】
- 監控系統：{system_name}
- 異常類別：【{category_name}】
- 統計月份：{target_period_str}
- 類別案件數：共 {case_count} 筆 (本月暴增重點類別)

以下為提報人在【{category_name}】填寫的 Case 詳細描述清單（共 {displayed_count} 筆代表性案件）：
---
{cases_text}
---

請依據上述提報人針對【{category_name}】的文字描述，進行深度歸因分析，並依照下列結構產出分析報告：

### 1. 🔍 類別集中問題與熱點 (Patterns within Category)
- 此類別的案件是否高度集中在特定廠區、機台設備、特定操作批次？（請給出佔比與受影響對象）
- 現場反映的主要現象與具體錯誤訊息為何？

### 2. 💡 潛在根因推測 (Hypothesis & Root Cause)
- 為什麼這個月份此特定類別會大幅增加？可能的原因為何（如排程異動、硬體老化、特定批次參數異常、網路設定變更等）？

### 3. 📢 月會建議行動方案 (Monthly Action Items)
- 條列 2~3 點改善行動與後續追蹤事項，供月會討論定案。
"""

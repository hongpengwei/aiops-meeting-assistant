# 🤖 AIOps 會議智能監控與歸因簡報助手 (Ops Insight Assistant)

專為**每日晨會**（檢視昨日 vs 前 7 天）與**每週課會**（檢視上週 vs 歷史週平均）設計的自動化監控與 AI 歸因簡報系統。

---

## 🌟 核心特色

1. **節省會前準備時間**：開會前自動計算各系統 Case 數量波動與增長率，免去人工查表統計。
2. **統計快篩 + AI 深度歸因**：
   - 🟢 **數量正常**：自動推播「全系統正常，無突發異常」，不耗費任何 AI Token。
   - 🔴 **數量暴增**：自動打包提報人的**自然語言描述與狀況回報**交由 AI 分析，判斷是「特定機台/廠區集中異常」還是「零星分散個案」，並直接整理出 3 點會議發言重點。
3. **無痛切換資料來源 (Data Adapter Pattern)**：
   - 現階段：使用手動匯出或產生的 CSV / Excel 檔案。
   - 未來：只需在 `config.yaml` 改設定，即可直連公司 SQL 資料庫或 Jira / ServiceNow API，**核心程式碼一行都不用改**。
4. **支援多種 AI 連線模式**：支援 Google Gemini、OpenAI、Azure、企業私有 LLM Gateway、本地 Ollama / vLLM 或自訂 HTTP 端點，並具備離線自動 Fallback 防護。
5. **多管道推播**：支援本機 HTML/Markdown 報表、Microsoft Teams 頻道通知與 Email 發信。

---

## 📁 專案目錄結構

```text
0823/
├── config/
│   └── config.yaml             # 系統核心設定 (資料來源、閾值、AI 模型、推播)
├── data/
│   └── mock_cases.csv          # 測試用的歷史 Case 數據 (包含真實中文狀況描述)
├── output/                     # 自動生成的 Markdown 與 HTML 視覺化簡報
├── src/
│   ├── __init__.py
│   ├── utils.py                # 共用工具模組 (logging 設定、Windows 編碼修復)
│   ├── loaders/                # 資料讀取抽象層 (轉接器模式)
│   │   ├── __init__.py
│   │   ├── base.py             # 抽象資料介面 (BaseCaseLoader 與欄位標準化)
│   │   ├── csv_loader.py       # CSV / Excel 讀取器 (現階段)
│   │   ├── db_loader.py        # 資料庫讀取器範本 (未來對接 SQL)
│   │   ├── api_loader.py       # API 讀取器範本 (未來對接 Jira/ServiceNow)
│   │   └── factory.py          # Loader 工廠模式
│   ├── analytics/
│   │   ├── __init__.py
│   │   └── detector.py         # 統計異常檢測引擎 (每日 7 天均線 / 每週歷史週平均)
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── analyzer.py         # AI 描述分析與語意分群 (Gemini / OpenAI / Custom API)
│   │   └── prompts.py          # 結構化 Prompt 樣板
│   └── notifications/
│       ├── __init__.py
│       ├── reporter.py         # 報告產生器 (Jinja2 模板渲染 Markdown / HTML)
│       ├── teams.py            # Microsoft Teams Webhook 推播
│       └── email_sender.py     # Email (SMTP) 發信模組
├── templates/
│   ├── report.md.j2            # Markdown 報告 Jinja2 模板
│   └── report.html.j2          # HTML 報告 Jinja2 模板
├── tests/                      # 單元測試
│   ├── conftest.py             # 共用 pytest fixtures
│   ├── test_detector.py        # 異常檢測邏輯測試
│   ├── test_csv_loader.py      # CSV 載入與篩選測試
│   └── test_analyzer.py        # AI 分析器 Mock 模式測試
├── deploy/
│   └── systemd/                # Linux Systemd Service 與 Timer 定時排程檔
│       ├── aiops-daily.service
│       └── aiops-daily.timer
├── scripts/
│   ├── __init__.py
│   ├── generate_mock_data.py   # 生成逼真測試數據的腳本
│   └── setup_windows_scheduler.ps1 # Windows 工作排程器一鍵註冊腳本
├── main.py                     # 主程式入口 (支援 --mode daily / --mode weekly)
├── scheduler.py                # Python 定時排程守護服務 (跨平台/伺服器)
├── run_daily.bat / .sh         # 每日晨會啟動腳本 (Windows / Linux)
├── run_weekly.bat / .sh        # 每週課會啟動腳本 (Windows / Linux)
├── Dockerfile                  # Docker 映像檔建置設定
├── docker-compose.yml          # Docker Compose 一鍵部署設定
├── requirements.txt            # Python 套件依賴
├── pytest.ini                  # 測試設定
└── README.md                   # 說明文件
```

---

## 🛡️ 獨立虛擬環境隔離機制 (Zero System Pollution)

本專案採用 **完全隔離的 `.venv` 虛擬環境機制**，確保所有 Python 套件只會安裝在專案目錄內，**100% 不會影響您本機系統或其他專案的 Python 環境**！

### ⚡ 自動建立與防護機制
所有的啟動腳本（`run_daily.bat/.sh`、`run_weekly.bat/.sh`）均內建**智慧環境檢測**：
1. **首次執行**：自動在本專案目錄下建立獨立的 `.venv/` 資料夾，並在虛擬環境內部安裝依賴套件。
2. **後續排程執行**：自動載入 `.venv` 執行，完全不干涉系統全域環境。

---

## 🚀 快速上手 (Quick Start)

### 🪟 Windows 環境：
1. **一鍵建立獨立虛擬環境**：
   雙擊執行 [`setup_env.bat`](file:///c:/Users/hongp/OneDrive/桌面/0823/setup_env.bat)（或在終端機輸入 `.\setup_env.bat`）。
2. **生成測試數據**：
   ```powershell
   python scripts/generate_mock_data.py
   ```
3. **執行每日晨會分析**：
   雙擊執行 [`run_daily.bat`](file:///c:/Users/hongp/OneDrive/桌面/0823/run_daily.bat)

---

### 🐧 Linux Server 環境：
1. **一鍵建立獨立虛擬環境**：
   ```bash
   chmod +x setup_env.sh run_*.sh
   ./setup_env.sh
   ```
2. **生成測試數據**：
   ```bash
   source .venv/bin/activate
   python3 scripts/generate_mock_data.py
   ```
3. **執行每日晨會分析**：
   ```bash
   ./run_daily.sh
   ```

---

## 🗄️ 資料庫欄位限制與對應說明 (Database Schema)

系統**完全不限制**公司資料庫的原始結構，也不需要修改現有資料表。我們在系統內部定義了標準欄位，透過 SQL 的 `AS` 別名即可輕鬆對接：

### 📊 各系統 Case 數量統計表

| 系統名稱 | 目標期數量 | 基準平均 | 增長率 | 狀態 |
| :--- | :---: | :---: | :---: | :--- |
| `ees` | 1 件 | 2.4 件 | -59% | 🟢 正常 |
| `fdc` | 1 件 | 2.6 件 | -61% | 🟢 正常 |
| `others` | 4 件 | 2.6 件 | +56% | 🟢 正常 |
| `tcs/tap` | 24 件 | 2.7 件 | +784% | 🔴 **異常暴增** |

---
## 🤖 AI 深度歸因分析與會議發言重點

### 系統：`tcs/tap`

### 1. 🔍 主要集中問題與熱點 (Top Patterns / Clusters)
- **熱點廠區與機台**：案件高度集中於 **【Fab 12A】**（佔比約 88%），主要受影響設備為 **【Track-03】**（佔比約 83%）。
- **共通回報症狀**：多位提報人反映類似現象：
  - 「Track-03 派工作業異常中斷，畫面上顯示 Remote Host Closed Connection...」
  - 「Fab 12A Track-03 刷批次條碼後跳出 SECS/GEM 通訊逾時 (ERR_TIMEOUT_0x8004)...」
  - 「Fab 12A Track-03 機台生產完畢後無法回傳結果至 TCS/TAP，已卡站 20 分鐘...」

### 📋 欄位需求清單

| 欄位層級 | 標準欄位名稱 | 說明 | 若資料庫沒有此欄位？ |
| :--- | :--- | :--- | :--- |
| 🔴 **必要** | `created_at` | 案件建立時間 | **必備**（用來統計昨日、前 7 天或上週） |
| 🔴 **必要** | `system_name` | 所屬系統名稱 (如 MES, WMS) | **必備**（用來區分各系統案件量） |
| 🔴 **必要** | `description` | 提報人描述的狀況與文字 | **必備**（供 AI 閱讀歸因；若只有 `title` 亦可） |
| 🟡 **加分** | `plant` / `fab` | 廠區或地點 (如 Fab 12, Fab 14) | 若無，系統自動補「未知廠區」，**不影響執行** |
| 🟡 **加分** | `device` / `tool` | 機台或設備編號 (如 Track-03) | 若無，系統自動補「General」，**不影響執行** |
| 🟢 **選填** | `case_id` | 工單編號 / 單號 | 若無，系統自動生成流水號 |
| 🟢 **選填** | `reporter` | 提報人姓名 / 工號 | 若無，系統自動填「匿名」 |

### 💡 SQL 對接範例 (`config/config.yaml`)

假設公司資料表的欄位名稱完全不同（如 `TKT_ID`, `LOG_TIME`, `APP_NAME`, `ISSUE_MEMO`, `SITE`），只需在 SQL 查詢中使用 `AS`：

```yaml
data_source:
  type: "database"
  database:
    connection_string: "mssql+pyodbc://user:password@server/dbname?driver=ODBC+Driver+17+for+SQL+Server"
    query_template: |
      SELECT 
        TKT_ID       AS case_id,       -- 單號
        LOG_TIME     AS created_at,    -- 建立時間
        APP_NAME     AS system_name,   -- 系統名稱
        ISSUE_MEMO   AS description,   -- 提報人描述
        SITE         AS plant          -- 廠區
      FROM COMPANY_TICKETS_TABLE
      WHERE LOG_TIME >= :start_date AND LOG_TIME <= :end_date
```

---

## 🤖 AI Model 換成自己的 API 設定指南

系統在 [`src/ai/analyzer.py`](file:///c:/Users/hongp/OneDrive/桌面/0823/src/ai/analyzer.py) 內建支援了 **3 種主流 API 模式**，只要修改 [`config/config.yaml`](file:///c:/Users/hongp/OneDrive/桌面/0823/config/config.yaml) 即可切換：

### 模式 1：使用 Google Gemini (官方 API)
1. 設定環境變數：
   ```powershell
   $env:GEMINI_API_KEY = "AIzaSy..."
   ```
2. 設定 `config/config.yaml`：
   ```yaml
   ai:
     provider: "gemini"
     model_name: "gemini-2.5-flash"      # 或 gemini-1.5-pro
     api_key_env_var: "GEMINI_API_KEY"
   ```

### 模式 2：使用公司內部私有 LLM 平台 / Azure / Ollama / vLLM (OpenAI 相容標準)
*(企業自建的內部 AI 網關或私有模型多採用此標準)*
1. 設定環境變數：
   ```powershell
   $env:CORP_LLM_KEY = "your_internal_token"
   ```
2. 設定 `config/config.yaml`：
   ```yaml
   ai:
     provider: "openai_compatible"
     base_url: "https://internal-llm.company.com/v1"  # 公司 LLM 網關或 http://localhost:11434/v1
     model_name: "llama-3-70b-instruct"               # 公司支援的模型名稱
     api_key_env_var: "CORP_LLM_KEY"
     
     # 若公司網關需要額外 Header (選填)：
     custom_headers:
       X-Client-Id: "ops-meeting-assistant"
   ```

### 模式 3：使用公司自訂格式的 HTTP REST API
```yaml
ai:
  provider: "custom_http"
  custom_endpoint_url: "https://ai-service.company.com/api/v1/analyze"
  api_key_env_var: "CORP_API_TOKEN"
  model_name: "custom-model"
```

> 🛡️ **自動降級保護 (Fallback)**：若未設定金鑰或網路暫時斷線，系統會自動切換至「智慧啟發式分析 (Mock AI)」，確保晨會前不會因為 API 異常而中斷！

---

## 📢 Teams 與 Email 推播設定

### 1. Microsoft Teams Webhook 推播
1. 在 Teams 頻道中新增「傳入 Webhook (Incoming Webhook)」並複製 URL。
2. 在 `config/config.yaml` 中啟用：
   ```yaml
   notifications:
     teams:
       enabled: true
       webhook_url: "https://outlook.office.com/webhook/xxxx/IncomingWebhook/yyyy"
   ```

### 2. Email (SMTP) 發信
在 `config/config.yaml` 中設定 SMTP 伺服器與收件人：
```yaml
notifications:
  email:
    enabled: true
    smtp_host: "smtp.company.com"
    smtp_port: 587
    use_tls: true
    sender: "ops-assistant@company.com"
    recipients:
      - "team-lead@company.com"
      - "ops-team@company.com"
    username_env_var: "SMTP_USER"
    password_env_var: "SMTP_PASSWORD"
```

---

## ⏰ 如何設定週期性自動執行？ (3 種方式)

我們提供了 **3 種不同的定時排程方式**，您可以依據執行環境自由選擇：

---

### 方法 1：Windows 工作排程器 (最推薦，本機免常駐)
電腦開機後，Windows 會在後台指定時間自動啟動執行，**即使關閉終端機也會自動跑**。

#### 💡 一鍵自動註冊 (PowerShell)：
以系統管理員身分開啟 PowerShell，執行以下指令：
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows_scheduler.ps1
```
> 註冊完成後，系統會自動在：
> - **週一至週五 08:30** 自動執行每日晨會分析 (`run_daily.bat`)
> - **每週一 09:00** 自動執行每週課會分析 (`run_weekly.bat`)

#### 🛠️ 手動設定方式：
1. 按 `Win + R` 輸入 `taskschd.msc` 開啟「工作排程器」。
2. 點選「建立基本工作」 ➔ 設定名稱（如：`AIOps_晨會`）。
3. 觸發程序選「每天」或「每週」，時間設為 `08:30`。
4. 動作選「啟動程式」，瀏覽選擇專案目錄下的 [`run_daily.bat`](file:///c:/Users/hongp/OneDrive/桌面/0823/run_daily.bat) 即可。

---

### 方法 2：Python 守護進程 (跨平台 / 伺服器適用)
直接在背景啟動 Python 排程守護腳本：
```bash
python scheduler.py
```
* 內建精準時間比對，預設週一至週五 08:30 跑晨會、週一 09:00 跑課會。
* 時間可在 [`scheduler.py`](file:///c:/Users/hongp/OneDrive/桌面/0823/scheduler.py) 最上方的 `DAILY_TIME` 與 `WEEKLY_TIME` 變數自由調整。

---

### 方法 3：Linux 伺服器排程 (Crontab / Systemd / Docker)

在 Linux Server 環境下，我們提供以下 **3 種企業級維運部署方案**：

#### 方案 A：使用 Crontab (最輕量簡便)
1. 賦予腳本執行權限：
   ```bash
   chmod +x run_daily.sh run_weekly.sh
   ```
2. 輸入 `crontab -e` 加入定時排程：
   ```bash
   # 1. 每日晨會：週一至週五 08:30 執行
   30 8 * * 1-5 /bin/bash /opt/aiops-assistant/run_daily.sh >> /var/log/aiops_daily.log 2>&1

   # 2. 每週課會：每週一 09:00 執行
   00 9 * * 1 /bin/bash /opt/aiops-assistant/run_weekly.sh >> /var/log/aiops_weekly.log 2>&1
   ```

---

#### 方案 B：使用 Linux Systemd Timer (企業伺服器首選，支援日誌與狀態監控)
1. 將 systemd 設定檔複製到系統目錄：
   ```bash
   sudo cp deploy/systemd/aiops-daily.* /etc/systemd/system/
   sudo systemctl daemon-reload
   ```
2. 啟動定時器並設定開機自啟：
   ```bash
   sudo systemctl enable --now aiops-daily.timer
   ```
3. 查看排程狀態與即時日誌：
   ```bash
   # 查看下一次觸發時間
   systemctl list-timers --all | grep aiops
   
   # 查看執行日誌
   journalctl -u aiops-daily.service -f
   ```

---

#### 方案 C：使用 Docker / Docker Compose 容器化部署
若伺服器支援 Docker，可直接一鍵容器化在背景運行：
```bash
# 啟動容器
docker compose up -d

# 查看容器運行日誌
docker compose logs -f
```

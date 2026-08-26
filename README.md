# 🤖 AIOps 會議智能監控與歸因簡報助手 (Ops Insight Assistant)

專為**每日晨會**（昨日 vs 前 7 天）、**每週課會**（上週 vs 歷史週平均）與**每月課會**（系統級 + 類別級兩層深度檢測）設計的自動化監控與 AI 歸因簡報系統。

---

## 🌟 核心特色

1. **節省會前準備時間**：開會前自動計算各系統 Case 數量波動與增長率，免去人工查表統計。
2. **三種分析模式**：
   - ☀️ **每日晨會 (`--mode daily`)**：比較昨日 vs 前 7 天均線，快速掌握昨日突發問題。
   - 📅 **每週課會 (`--mode weekly`)**：比較上週 vs 過去 4 週週平均，掌握中短期趨勢。
   - 📊 **每月課會 (`--mode monthly`)**：**兩層深度檢測**（第 1 層：系統總量暴增檢測 ➔ 第 2 層：深入比對該系統哪些具體 Category/類別暴增），AI 只聚焦暴增類別的描述進行精準歸因！
3. **統計快篩 + AI 深度歸因**：
   - 🟢 **數量正常**：自動推播「全系統正常，無突發異常」，不耗費任何 AI Token。
   - 🔴 **數量暴增**：自動打包提報人的**自然語言描述與狀況回報**交由 AI 分析，判斷是「特定機台/廠區集中異常」還是「零星分散個案」，並直接整理出 3 點會議發言重點與行動方案。
4. **無痛切換資料來源 (Data Adapter Pattern)**：
   - 現階段：使用手動匯出或產生的 CSV / Excel 檔案。
   - 未來：只需在 `config.yaml` 改設定，即可直連公司 SQL 資料庫或 Jira / ServiceNow API，**核心程式碼一行都不用改**。
5. **支援多種 AI 連線模式**：支援 Google Gemini、OpenAI、Azure、企業私有 LLM Gateway、本地 Ollama / vLLM 或自訂 HTTP 端點，並具備離線自動 Fallback 防護。
6. **多管道推播**：支援本機 HTML/Markdown 報表、Microsoft Teams 頻道通知與 Email 發信。

---

## 📁 專案目錄結構

```text
0823/
├── config/
│   └── config.yaml             # 系統核心設定 (資料來源、閾值、AI 模型、推播)
├── data/
│   └── mock_cases.csv          # 測試用的歷史 Case 數據 (包含真實中文狀況描述與 category)
├── output/                     # 自動生成的 Markdown 與 HTML 視覺化簡報
├── src/
│   ├── __init__.py
│   ├── utils.py                # 共用工具模組 (logging 設定、Windows 編碼修復)
│   ├── loaders/                # 資料讀取抽象層 (轉接器模式)
│   │   ├── __init__.py
│   │   ├── base.py             # 抽象資料介面 (BaseCaseLoader 與欄位標準化)
│   │   ├── csv_loader.py       # CSV / Excel 讀取器 (現階段)
│   │   ├── db_loader.py        # 資料庫讀取器 (支援環境變數讀取連線字串)
│   │   ├── api_loader.py       # API 讀取器 (內建 retry 機制與 timeout 300s)
│   │   └── factory.py          # Loader 工廠模式
│   ├── analytics/
│   │   ├── __init__.py
│   │   └── detector.py         # 統計異常檢測引擎 (日/週/月兩層檢測)
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── analyzer.py         # AI 描述分析與語意分群 (Gemini / OpenAI / Custom API)
│   │   └── prompts.py          # 結構化 Prompt 樣板 (掃讀友善格式：嚴重度表格 + 分群摘要)
│   └── notifications/
│       ├── __init__.py
│       ├── base.py             # 通知發送器抽象介面 (BaseNotifier)
│       ├── reporter.py         # 報告渲染器 + 推播協調器 (ReportRenderer + ReportGenerator)
│       ├── teams.py            # Microsoft Teams Webhook 推播
│       └── email_sender.py     # Email (SMTP) 發信模組
├── templates/
│   ├── report.md.j2            # 晨會/課會 Markdown 報告模板
│   ├── report.html.j2          # 晨會/課會 HTML 報告模板
│   ├── monthly_report.md.j2    # 每月課會 Markdown 兩層分析模板
│   └── monthly_report.html.j2  # 每月課會 HTML 兩層分析模板
├── tests/                      # 單元測試 (pytest)
│   ├── conftest.py             # 共用 pytest fixtures
│   ├── test_detector.py        # 日/週異常檢測測試
│   ├── test_monthly_detector.py # 每月兩層異常檢測測試
│   ├── test_csv_loader.py      # CSV 載入與篩選測試
│   └── test_analyzer.py        # AI 分析器測試
├── deploy/
│   └── systemd/                # Linux Systemd Service 與 Timer 定時排程檔
│       ├── aiops-daily.service
│       └── aiops-daily.timer
├── scripts/
│   ├── __init__.py
│   ├── generate_mock_data.py   # 生成逼真測試數據的腳本 (含跨月與多類別)
│   └── setup_windows_scheduler.ps1 # Windows 工作排程器一鍵註冊腳本
├── main.py                     # 主程式入口 (支援 --mode daily / --mode weekly / --mode monthly)
├── scheduler.py                # Python 定時排程守護服務 (跨平台/伺服器)
├── run_daily.bat / .sh         # 每日晨會啟動腳本 (Windows / Linux)
├── run_weekly.bat / .sh        # 每週課會啟動腳本 (Windows / Linux)
├── run_monthly.bat / .sh       # 每月課會啟動腳本 (Windows / Linux)
├── Dockerfile                  # Docker 映像檔建置設定 (支援可選依賴安裝)
├── docker-compose.yml          # Docker Compose 一鍵部署設定
├── requirements.txt            # Python 核心套件依賴
├── requirements-extras.txt     # 可選套件依賴 (AI / DB / Excel)
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
3. **執行會議分析**：
   - 每日晨會：雙擊執行 [`run_daily.bat`](file:///c:/Users/hongp/OneDrive/桌面/0823/run_daily.bat)
   - 每週課會：雙擊執行 [`run_weekly.bat`](file:///c:/Users/hongp/OneDrive/桌面/0823/run_weekly.bat)
   - 每月課會：雙擊執行 [`run_monthly.bat`](file:///c:/Users/hongp/OneDrive/桌面/0823/run_monthly.bat)（或 `python main.py --mode monthly`）

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
3. **執行會議分析**：
   - 每日晨會：`./run_daily.sh`
   - 每週課會：`./run_weekly.sh`
   - 每月課會：`./run_monthly.sh`

---

## ⚡ 使用者接入指南 — 只需兩步

> 💡 **不需要改任何一行程式碼！** 不管是接 AI、接資料庫還是接 API，使用者只需要做兩件事：

| 步驟 | 做什麼 | 在哪裡做 |
|:---:|------|------|
| **①** | 修改 `config/config.yaml` | 切換 `data_source.type` 或 `ai.provider`，填入對應設定 |
| **②** | 設定環境變數 | 設定 API Key / DB 連線字串等敏感資訊 |

### 快速範例

**接 AI（Gemini）**：
```powershell
# 步驟 1: config.yaml 已經預設好 Gemini，不需要改
# 步驟 2: 設定環境變數
$env:GEMINI_API_KEY = "AIzaSy..."
```

**接公司資料庫**：
```powershell
# 步驟 1: 修改 config.yaml → data_source.type 改為 "database"，調整 SQL query
# 步驟 2: 設定環境變數
$env:DB_CONNECTION_STRING = "mssql+pyodbc://user:password@server/dbname?driver=ODBC+Driver+17+for+SQL+Server"
```

**接公司 API（Jira / ServiceNow）**：
```powershell
# 步驟 1: 修改 config.yaml → data_source.type 改為 "api"，填入 base_url 和 endpoint
# 步驟 2: 設定環境變數
$env:CORP_API_TOKEN = "your_api_token"
```

> ⚠️ **安全提醒**：所有密碼與 API Key 均透過環境變數讀取，**切勿直接寫在 `config.yaml` 中**。

---

## 🗄️ 資料庫欄位限制與對應說明 (Database Schema)

系統**完全不限制**公司資料庫的原始結構，也不需要修改現有資料表。我們在系統內部定義了標準欄位，透過 SQL 的 `AS` 別名即可輕鬆對接：

### 📋 欄位需求清單

| 欄位層級 | 標準欄位名稱 | 說明 | 若資料庫沒有此欄位？ |
| :--- | :--- | :--- | :--- |
| 🔴 **必要** | `created_at` | 案件建立時間 | **必備**（用來統計昨日、前 7 天、上週或歷史月份） |
| 🔴 **必要** | `system_name` | 所屬系統名稱 (如 MES, WMS) | **必備**（用來區分各系統案件量） |
| 🔴 **必要** | `description` | 提報人描述的狀況與文字 | **必備**（供 AI 閱讀歸因；若只有 `title` 亦可） |
| 🟡 **加分** | `category` | 案件分類/類別 (如 設備通訊、派工異常) | 若無，系統自動補「未分類」，**月報模式將自動改為全系統綜合歸因** |
| 🟡 **加分** | `plant` / `fab` | 廠區或地點 (如 Fab 12, Fab 14) | 若無，系統自動補「未知廠區」，**不影響執行** |
| 🟡 **加分** | `device` / `tool` | 機台或設備編號 (如 Track-03) | 若無，系統自動補「General」，**不影響執行** |
| 🟢 **選填** | `case_id` | 工單編號 / 單號 | 若無，系統自動生成流水號 |
| 🟢 **選填** | `reporter` | 提報人姓名 / 工號 | 若無，系統自動填「匿名」 |

### 💡 SQL 對接範例 (`config/config.yaml`)

假設公司資料表的欄位名稱完全不同（如 `TKT_ID`, `LOG_TIME`, `APP_NAME`, `CAT_NAME`, `ISSUE_MEMO`, `SITE`），只需在 SQL 查詢中使用 `AS`：

```yaml
data_source:
  type: "database"
  database:
    # 連線字串從環境變數讀取 (不要把密碼寫在這裡！)
    connection_string_env_var: "DB_CONNECTION_STRING"
    query_template: |
      SELECT 
        TKT_ID       AS case_id,       -- 單號
        LOG_TIME     AS created_at,    -- 建立時間
        APP_NAME     AS system_name,   -- 系統名稱
        CAT_NAME     AS category,      -- 案件類別 (月報兩層分析依據)
        ISSUE_MEMO   AS description,   -- 提報人描述
        SITE         AS plant          -- 廠區
      FROM COMPANY_TICKETS_TABLE
      WHERE LOG_TIME >= :start_date AND LOG_TIME <= :end_date
```

然後設定環境變數：
```powershell
# Windows
$env:DB_CONNECTION_STRING = "mssql+pyodbc://user:password@server/dbname?driver=ODBC+Driver+17+for+SQL+Server"

# Linux
export DB_CONNECTION_STRING="mssql+pyodbc://user:password@server/dbname?driver=ODBC+Driver+17+for+SQL+Server"
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
> - **每月 1 號 09:30** 自動執行每月課會分析 (`run_monthly.bat`)

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
* 內建精準時間比對，預設週一至週五 08:30 跑晨會、週一 09:00 跑課會、每月 1 號 09:30 跑月會。
* 時間可在 [`scheduler.py`](file:///c:/Users/hongp/OneDrive/桌面/0823/scheduler.py) 最上方的變數自由調整。

---

### 方法 3：Linux 伺服器排程 (Crontab / Systemd / Docker)

在 Linux Server 環境下，我們提供以下 **3 種企業級維運部署方案**：

#### 方案 A：使用 Crontab (最輕量簡便)
1. 賦予腳本執行權限：
   ```bash
   chmod +x run_daily.sh run_weekly.sh run_monthly.sh
   ```
2. 輸入 `crontab -e` 加入定時排程：
   ```bash
   # 1. 每日晨會：週一至週五 08:30 執行
   30 8 * * 1-5 /bin/bash /opt/aiops-assistant/run_daily.sh >> /var/log/aiops_daily.log 2>&1

   # 2. 每週課會：每週一 09:00 執行
   00 9 * * 1 /bin/bash /opt/aiops-assistant/run_weekly.sh >> /var/log/aiops_weekly.log 2>&1

   # 3. 每月課會：每月 1 號 09:30 執行
   30 9 1 * * /bin/bash /opt/aiops-assistant/run_monthly.sh >> /var/log/aiops_monthly.log 2>&1
   ```

---

#### 方案 B：使用 Linux Systemd Timer (企業伺服器首選，支援日誌與狀態監控)
1. 將 systemd 設定檔複製到系統目錄：
   ```bash
   sudo cp deploy/systemd/aiops-* /etc/systemd/system/
   sudo systemctl daemon-reload
   ```
2. 啟動定時器並設定開機自啟：
   ```bash
   sudo systemctl enable --now aiops-daily.timer aiops-weekly.timer aiops-monthly.timer
   ```
3. 查看排程狀態與即時日誌：
   ```bash
   # 查看下一次觸發時間清單
   systemctl list-timers --all | grep aiops
   
   # 查看執行日誌 (例如查看月會執行紀錄)
   journalctl -u aiops-monthly.service -f
   ```

---

## 🛠️ 排程常見調整指南 (修改時間、更改星期幾、停用排程)

針對不同環境，如何調整排程設定：

### 1. 如何修改開會時間？
| 執行環境 | 如何修改 |
| :--- | :--- |
| **Windows 工作排程器** | 按 `Win + R` 輸入 `taskschd.msc` ➔ 連點任務（如 `AIOps_Morning_Meeting_Daily`） ➔ 點「觸發程序」頁籤 ➔ 編輯時間 ➔ 確定 |
| **Python 守護腳本 (`scheduler.py`)** | 打開 `scheduler.py` 修改頂部常數：`DAILY_TIME = "08:00"` / `WEEKLY_TIME = "08:30"` / `MONTHLY_TIME = "09:00"` |
| **Linux Systemd** | 編輯 `deploy/systemd/aiops-*.timer` 中的 `OnCalendar` 時間，執行 `sudo systemctl daemon-reload` |

### 2. 課會不是星期一，如何改為「星期幾」？
* **Windows 工作排程器**：在 `taskschd.msc` 編輯 `AIOps_Section_Meeting_Weekly` ➔ 觸發程序中改勾選「星期三」或「星期五」即可；或修改 `scripts/setup_windows_scheduler.ps1` 中的 `-DaysOfWeek Wednesday`。
* **Python 守護腳本**：修改 `scheduler.py` 中的 `WEEKLY_DAY`（`0`=週一、`1`=週二、`2`=週三、`3`=週四、`4`=週五）。
* **Linux Systemd**：修改 `aiops-weekly.timer` 中的 `OnCalendar=Wed *-*-* 09:00:00`（改為 `Tue`, `Wed`, `Thu`, `Fri`）。

### 3. 如何暫時停用 / 關閉特定排程（例如不想跑每月課會）？
* **Windows 工作排程器**：
  - 介面：在 `taskschd.msc` 找到 `AIOps_Section_Meeting_Monthly` ➔ **按右鍵 ➔ 點「停用 (Disable)」**。
  - 指令：`Disable-ScheduledTask -TaskName "AIOps_Section_Meeting_Monthly"`
* **Python 守護腳本**：在 `scheduler.py` 內將 monthly 的 `if day_of_month == ...` 邏輯註解掉（加上 `#`）後重啟。
* **Linux Systemd**：執行 `sudo systemctl stop aiops-monthly.timer && sudo systemctl disable aiops-monthly.timer`。

---

#### 方案 C：使用 Docker / Docker Compose 容器化部署
若伺服器支援 Docker，可直接一鍵容器化在背景運行：
```bash
# 基本啟動 (僅包含核心依賴)
docker compose up -d

# 若需要使用 AI (Gemini) 或資料庫功能，需安裝可選依賴：
docker build --build-arg INSTALL_EXTRAS=true -t aiops-assistant .
docker run -d --name aiops -e GEMINI_API_KEY="your_key" aiops-assistant

# 查看容器運行日誌
docker compose logs -f
```

> 💡 `requirements-extras.txt` 包含 `google-genai`、`sqlalchemy`、`pyodbc`、`openpyxl`，使用 `--build-arg INSTALL_EXTRAS=true` 時才會安裝。

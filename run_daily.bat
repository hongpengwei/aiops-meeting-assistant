@echo off
chcp 65001 > nul
:: 移動到專案所在目錄
cd /d "%~dp0"

:: 1. 檢查虛擬環境是否存在，若不存在則自動建立並安裝依賴 (防止污染本機環境)
if not exist ".venv\Scripts\activate.bat" (
    echo [AIOps] 正在為您建立獨立虛擬環境 (.venv)...
    python -m venv .venv
    echo [AIOps] 正在安裝必要套件...
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

:: 2. 執行分析
echo [AIOps] 正在執行每日晨會分析 (使用獨立虛擬環境)...
python main.py --mode daily

echo [AIOps] 執行完成！

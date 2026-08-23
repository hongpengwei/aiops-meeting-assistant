@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo =========================================================
echo 🛡️ 正在為您建立獨立虛擬環境 (.venv)，保證不影響系統...
echo =========================================================

if not exist ".venv" (
    python -m venv .venv
    echo ✅ .venv 虛擬環境建立完成！
) else (
    echo ℹ️ .venv 虛擬環境已存在。
)

echo 📦 正在虛擬環境內安裝依賴套件...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo =========================================================
echo 🎉 虛擬環境配置完成！所有套件均隔離在 .venv 資料夾內。
echo =========================================================
pause

#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "========================================================="
echo "🛡️ 正在為您建立獨立虛擬環境 (.venv)，保證不影響系統..."
echo "========================================================="

if [ ! -d ".venv" ]; then
    python3 -m venv .venv || { echo "❌ 建立 venv 失敗，請確認已安裝 python3-venv (Ubuntu/Debian: sudo apt install python3-venv)"; exit 1; }
    echo "✅ .venv 虛擬環境建立完成！"
else
    echo "ℹ️ .venv 虛擬環境已存在。"
fi

echo "📦 正在虛擬環境內安裝依賴套件..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "========================================================="
echo "🎉 虛擬環境配置完成！所有套件均隔離在 .venv 資料夾內。"
echo "========================================================="

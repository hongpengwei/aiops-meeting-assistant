#!/usr/bin/env bash
# ==============================================================================
# AIOps 每週課會分析啟動腳本 (Linux / macOS) - 具備虛擬環境自動隔離保護
# ==============================================================================

# 切換至腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# 1. 檢查虛擬環境是否存在，若不存在則自動建立並安裝依賴 (防止污染系統 Python)
if [ ! -f ".venv/bin/activate" ]; then
    echo "[AIOps] 正在為您建立獨立虛擬環境 (.venv)..."
    python3 -m venv .venv || { echo "❌ 建立 venv 失敗，請確認已安裝 python3-venv (Ubuntu/Debian: sudo apt install python3-venv)"; exit 1; }
    source .venv/bin/activate
    echo "[AIOps] 正在安裝必要套件..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# 2. 執行分析
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [AIOps] 正在執行每週課會分析 (虛擬環境模式)..."
python3 main.py --mode weekly
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [AIOps] 每週課會分析完成！"

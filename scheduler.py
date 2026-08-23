import time
import sys
from datetime import datetime
import subprocess

# 解決 Windows console cp950 編碼問題
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

DAILY_TIME = "08:30"   # 每天晨會執行時間 (HH:MM)
WEEKLY_DAY = 0         # 每週幾執行課會 (0=週一, 1=週二, ..., 6=週日)
WEEKLY_TIME = "09:00"  # 每週課會執行時間 (HH:MM)

def run_job(mode: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{now_str}] ⏰ 觸發定時任務: {mode.upper()} 模式...")
    try:
        cmd = [sys.executable, "main.py", "--mode", mode]
        subprocess.run(cmd, check=True)
        print(f"[{now_str}] ✅ {mode.upper()} 任務執行完成！")
    except Exception as e:
        print(f"[{now_str}] ❌ {mode.upper()} 任務執行失敗: {e}")

def main():
    print("=" * 60)
    print("🤖 AIOps 定時排程守護服務 (Python Scheduler Daemon)")
    print(f"📅 每日晨會排程: 每週一至週五 {DAILY_TIME}")
    print(f"📅 每週課會排程: 每週一 {WEEKLY_TIME}")
    print("=" * 60)
    print("🟢 守護服務運行中，按 Ctrl + C 可結束服務...\n")

    last_daily_run = None
    last_weekly_run = None

    while True:
        now = datetime.now()
        today_date_str = now.strftime("%Y-%m-%d")
        current_hm = now.strftime("%H:%M")
        weekday = now.weekday() # 0 = Monday

        # 1. 檢查每日晨會 (週一到週五的指定時間)
        if weekday < 5 and current_hm == DAILY_TIME and last_daily_run != today_date_str:
            last_daily_run = today_date_str
            run_job("daily")

        # 2. 檢查每週課會 (週一的指定時間)
        if weekday == WEEKLY_DAY and current_hm == WEEKLY_TIME and last_weekly_run != today_date_str:
            last_weekly_run = today_date_str
            run_job("weekly")

        # 每 20 秒檢查一次
        time.sleep(20)

if __name__ == "__main__":
    main()

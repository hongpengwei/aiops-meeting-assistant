import time
import sys
import logging
from datetime import datetime
import subprocess

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

DAILY_TIME = "08:30"
WEEKLY_DAY = 0
WEEKLY_TIME = "09:00"

def run_job(mode: str, max_retries: int = 3):
    logger.info(f"⏰ 觸發定時任務: {mode.upper()} 模式...")
    
    for attempt in range(1, max_retries + 1):
        try:
            cmd = [sys.executable, "main.py", "--mode", mode]
            subprocess.run(cmd, check=True)
            logger.info(f"✅ {mode.upper()} 任務執行完成！")
            return
        except Exception as e:
            logger.error(f"❌ {mode.upper()} 任務執行失敗 (嘗試 {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                logger.info(f"🔄 等待 10 秒後重試...")
                time.sleep(10)
    
    logger.error(f"❌ {mode.upper()} 任務多次重試後仍失敗。")

def main():
    logger.info("=" * 60)
    logger.info("🤖 AIOps 定時排程守護服務 (Python Scheduler Daemon)")
    logger.info(f"📅 每日晨會排程: 每週一至週五 {DAILY_TIME}")
    logger.info(f"📅 每週課會排程: 每週一 {WEEKLY_TIME}")
    logger.info("=" * 60)
    logger.info("🟢 守護服務運行中，按 Ctrl + C 可結束服務...\n")

    last_daily_run = None
    last_weekly_run = None

    while True:
        now = datetime.now()
        today_date_str = now.strftime("%Y-%m-%d")
        current_hm = now.strftime("%H:%M")
        weekday = now.weekday()

        # 每日任務檢查 (週一至週五)
        if weekday < 5 and current_hm >= DAILY_TIME and last_daily_run != today_date_str:
            last_daily_run = today_date_str
            run_job("daily")

        # 每週任務檢查 (週一)
        if weekday == WEEKLY_DAY and current_hm >= WEEKLY_TIME and last_weekly_run != today_date_str:
            last_weekly_run = today_date_str
            run_job("weekly")

        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n🛑 守護服務已手動停止。")

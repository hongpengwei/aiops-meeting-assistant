import os
import sys

# 確保專案根目錄在 sys.path 中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import random
from datetime import datetime, timedelta
import pandas as pd
import logging

from src.utils import fix_windows_encoding

# 解決 Windows console cp950 編碼問題
fix_windows_encoding()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "mock_cases.csv")


def generate_mock_data(output_path: str = DEFAULT_DATA_PATH, days: int = 120):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    random.seed(42)
    
    # 基準日期 (以今天為基準，往前推 N 天，支援月報跨月統計)
    base_date = datetime.now().date()
    start_date = base_date - timedelta(days=days)
    
    systems = ["ees", "tcs/tap", "fdc", "others"]
    plants = ["F12A", "F12B", "F14A", "F14B", "F15", "F18"]
    reporters = ["alex_chen", "john_lin", "kevin_wang", "david_li", "eric_huang", "sam_liu", "chris_chao", "tony_chang"]
    
    # 一般日常零星問題 (類別, 標題, 描述)
    routine_issues = [
        ("帳號與權限", "帳號無法登入", "使用者更換密碼後無法登入系統認證失敗"),
        ("報表與查詢", "報表下載超時", "月報匯出功能等待超過3分鐘未回應"),
        ("帳號與權限", "使用者權限申請", "新進同仁開通基本查詢與資料維護權限"),
        ("週邊設備", "標籤列印失敗", "條碼標籤機無法收到列印指令顯示離線"),
        ("系統效能", "畫面卡頓延遲", "尖峰時段操作介面稍有延遲"),
        ("資料維護", "誤刪資料復原請求", "操作員申請協助回復未確認工單狀態")
    ]

    # 各系統一般業務描述庫
    system_routine_issues = {
        "ees": [
            ("PM保養", "PM保養工單結案失敗", "年度PM完成後於EES點選完工無法同步更新狀態"),
            ("配方管理", "Recipe參數上傳逾時", "修改參數後上傳EES主機回應逾時"),
            ("零件壽命", "Parts壽命計數未重置", "更換消耗性零件後EES介面仍顯示壽命過期警告"),
            ("帳號與權限", "權限開通申請", "廠端新進作業員申請基礎檢視權限")
        ],
        "tcs/tap": [
            ("設備通訊", "Load Port載入訊號延遲", "OHT天車放置晶圓盒後TAP交握訊號延遲約10秒"),
            ("派工作業", "單一機台派工等待", "機台換批時派工佇列稍有延遲重整後正常"),
            ("自動搬運", "搬運指令確認", "自動搬運系統指令重試後成功進料"),
            ("系統效能", "主機回應微幅延遲", "尖峰排程時段TCS主機反應時間稍有波動"),
            ("帳號與權限", "操作員權限異動", "作業員請假交接暫時調整TAP機台控制權限"),
            ("報表與查詢", "搬運歷史紀錄匯出", "工程師申請匯出昨日OHT搬運統計報表")
        ],
        "fdc": [
            ("感測器異常", "Sensor取樣頻率異常", "單一Sensor SVID採樣週期跳動"),
            ("腔體警報", "腔體壓力單點警報", "腔體即時壓力短暫碰觸UCL邊界"),
            ("模型維護", "模型微調通知", "例行性FDC演算法閾值微調驗證"),
            ("資料採集", "Log傳輸佇列累積", "短暫網路震盪導致FDC Log採集延遲")
        ],
        "others": [
            ("帳號與權限", "密碼重設申請", "工程師忘記密碼導致帳號被鎖定"),
            ("帳號與權限", "新帳號權限開通", "廠端新進作業員申請基礎檢視權限"),
            ("週邊設備", "印表機連線異常", "標籤列印機無法收到網路列印指令")
        ]
    }

    # tcs/tap 異常暴增問題的描述庫 (特定機台/廠區集中異常)
    tap_anomaly_issues = [
        ("派工作業", "派工通訊中斷", "按Dispatch沒有反應卡在通訊等待狀態"),
        ("設備通訊", "機台刷條碼無回應", "刷批次條碼後跳出SECS/GEM通訊逾時(ERR_TIMEOUT_0x8004)"),
        ("派工作業", "機台卡站無法下線", "生產完畢後無法回傳結果至TCS/TAP卡站逾時"),
        ("設備通訊", "主機連線中斷", "軟體跳出與TCS/TAP主機中斷連線重啟依然失敗"),
        ("資料過帳", "批次過帳失敗", "派工作業異常中斷顯示Remote Host Closed Connection"),
        ("設備通訊", "設備狀態異常鎖定", "設備燈號變紅TCS介面顯示處於Invalid State"),
        ("配方管理", "配方下載逾時", "準備跑新批次時TAP下載Recipe失敗顯示網路逾時"),
        ("設備通訊", "現場緊急通訊異常", "黃光區無法進料請派員確認網路或主機連線")
    ]

    rows = []
    case_counter = 0

    from src.utils import subtract_months

    logger.info(f"🔄 開始生成過去 {days} 天的模擬 Case 數據 (系統: {', '.join(systems)})...")

    # 判斷目標月份 (以上個完整月作為月報分析異常注入目標)
    last_m_year, last_m_month = subtract_months(base_date.year, base_date.month, 1)
    target_month_str = f"{last_m_year:04d}-{last_m_month:02d}"
    yesterday = base_date - timedelta(days=1)

    for day_offset in range(days + 1):
        current_date = start_date + timedelta(days=day_offset)
        is_yesterday = (current_date == yesterday) # 設定昨天為晨會異常日
        is_target_month = (current_date.strftime("%Y-%m") == target_month_str)

        for sys_name in systems:
            # 正常情況下每個系統每天 1 ~ 3 筆 Case
            case_count = random.randint(1, 3)
            
            # 若為昨天且為 tcs/tap，製造「晨會/課會日暴增」異常
            if is_yesterday and sys_name == "tcs/tap":
                case_count = 24
            elif is_target_month and sys_name == "tcs/tap":
                # 在目標月份中，tcs/tap 活躍 (每天 3~6 筆)，製造「月報級異常」
                case_count = random.randint(3, 6)

            for _ in range(case_count):
                case_counter += 1
                case_id = f"case-{current_date.strftime('%Y%m%d')}-{case_counter:05d}"
                
                # 隨機產生當天的小時與分鐘 (12小時制 AM/PM)
                hour = random.randint(8, 20)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                created_dt = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute, seconds=second)
                # 格式範例：2026/8/25 12:20:26 AM / PM
                hour_12 = created_dt.hour % 12
                if hour_12 == 0:
                    hour_12 = 12
                am_pm = "AM" if created_dt.hour < 12 else "PM"
                createdatetime_str = f"{created_dt.year}/{created_dt.month}/{created_dt.day} {hour_12}:{created_dt.minute:02d}:{created_dt.second:02d} {am_pm}"
                
                reporter = random.choice(reporters)

                # 如果是昨天且是 tcs/tap 的異常集中群 (85% 機率集中在 F12A Track-03)
                if is_yesterday and sys_name == "tcs/tap" and random.random() < 0.85:
                    plant = "F12A"
                    device = "Track-03"
                    category, title, desc = random.choice(tap_anomaly_issues)
                elif is_target_month and sys_name == "tcs/tap" and random.random() < 0.60:
                    plant = random.choice(["F12A", "F12B"])
                    device = "Track-03" if random.random() < 0.5 else f"Tool-{random.randint(10, 30)}"
                    category, title, desc = random.choice(tap_anomaly_issues)
                else:
                    plant = random.choice(plants)
                    device = f"Tool-{random.randint(10, 99)}" if random.random() > 0.4 else "General"
                    specific_list = system_routine_issues.get(sys_name, routine_issues)
                    category, title, desc = random.choice(specific_list)

                # 主旨包含 tool_id，如 [ccop alarm:fdcfilecnt]f15_ypoctc的ftc...
                fab_tag = plant.lower().replace(" ", "")
                subject = f"[{sys_name} alarm:{category}]{fab_tag}_{device}的{desc}"

                rows.append({
                    "caseid": case_id,
                    "createdatetime": createdatetime_str,
                    "fab": plant,
                    "subject": subject,
                    "username": reporter,
                    "productname": sys_name,
                    "issuetype": category
                })

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"✅ 成功生成 {len(df)} 筆真實格式測試資料，已儲存至: {os.path.abspath(output_path)}")
    return df

if __name__ == "__main__":
    generate_mock_data()

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

def generate_mock_data(output_path: str = "./data/mock_cases.csv", days: int = 120):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    random.seed(42)
    
    # 基準日期 (以今天為基準，往前推 N 天，支援月報跨月統計)
    base_date = datetime.now().date()
    start_date = base_date - timedelta(days=days)
    
    systems = ["ees", "tcs/tap", "fdc", "others"]
    plants = ["Fab 12A", "Fab 12B", "Fab 14A", "Fab 14B", "Fab 15", "Fab 18"]
    
    # 一般日常零星問題 (類別, 標題, 描述)
    routine_issues = [
        ("帳號與權限", "帳號無法登入", "使用者表示更換密碼後無法登入系統，跳出認證失敗訊息"),
        ("報表與查詢", "報表下載超時", "點擊月報匯出功能後等待超過3分鐘未回應，請協助確認排程"),
        ("帳號與權限", "使用者權限申請", "新進同仁需開通基本查詢與資料維護權限，主管已簽核"),
        ("週邊設備", "標籤列印失敗", "條碼標籤機無法收到列印指令，顯示離線狀態"),
        ("系統效能", "畫面卡頓延遲", "下午尖峰時段操作介面稍有延遲，約5秒後恢復"),
        ("資料維護", "誤刪資料復原請求", "操作員不小心將未確認工單作廢，申請協助回復狀態")
    ]

    # 各系統一般業務描述庫
    system_routine_issues = {
        "ees": [
            ("PM保養", "PM 保養工單結案失敗", "機台完成年度 PM 後，於 EES 點選完工無法同步更新狀態"),
            ("配方管理", "Recipe 參數上傳逾時", "設備工程師修改參數後上傳 EES 主機回應逾時"),
            ("零件壽命", "Parts 壽命計數未重置", "更換消耗性零件後，EES 介面仍顯示壽命過期警告"),
            ("帳號與權限", "權限開通申請", "廠端新進作業員申請基礎檢視權限")
        ],
        "tcs/tap": [
            ("設備通訊", "Load Port 載入訊號延遲", "OHT 天車放置晶圓盒後，TAP 交握訊號延遲約 10 秒"),
            ("派工作業", "單一機台派工等待", "機台換批時派工佇列稍有延遲，重整後已正常"),
            ("自動搬運", "搬運指令確認", "自動搬運系統指令重試後成功進料"),
            ("系統效能", "主機回應微幅延遲", "尖峰排程時段 TCS 主機反應時間稍有波動"),
            ("帳號與權限", "操作員權限異動", "作業員請假交接，暫時調整 TAP 機台控制權限"),
            ("報表與查詢", "搬運歷史紀錄匯出", "工程師申請匯出昨日 OHT 搬運統計報表")
        ],
        "fdc": [
            ("感測器異常", "Sensor 取樣頻率異常", "偵測到單一 Sensor SVID 採樣週期跳動，已通知設備檢查"),
            ("腔體警報", "腔體壓力單點警報", "腔體即時壓力短暫碰觸 UCL 邊界，隨後恢復正常"),
            ("模型維護", "模型微調通知", "例行性 FDC 演算法閾值微調驗證"),
            ("資料採集", "Log 傳輸佇列累積", "短暫網路震盪導致 FDC Log 採集有 30 秒延遲")
        ],
        "others": [
            ("帳號與權限", "密碼重設申請", "工程師忘記密碼導致帳號被鎖定"),
            ("帳號與權限", "新帳號權限開通", "廠端新進作業員申請基礎檢視權限"),
            ("週邊設備", "印表機連線異常", "標籤列印機無法收到網路列印指令")
        ]
    }

    # tcs/tap 異常暴增問題的描述庫 (特定機台/廠區集中異常)
    tap_anomaly_issues = [
        ("派工作業", "Track-03 派工通訊中斷", "現場反映 Fab 12A 的 Track-03 機台按 Dispatch 沒有反應，卡在通訊等待狀態"),
        ("設備通訊", "機台刷條碼無回應", "Fab 12A Track-03 刷批次條碼後跳出 SECS/GEM 通訊逾時 (ERR_TIMEOUT_0x8004)"),
        ("派工作業", "機台卡站無法下線", "Fab 12A Track-03 機台生產完畢後無法回傳結果至 TCS/TAP，已卡站 20 分鐘"),
        ("設備通訊", "Track-03 連線中斷", "機台軟體跳出與 TCS/TAP 主機中斷連線，重啟後依然無法連上"),
        ("資料過帳", "Fab12A 批次過帳失敗", "Track-03 派工作業異常中斷，畫面上顯示 Remote Host Closed Connection"),
        ("設備通訊", "設備狀態異常鎖定", "Fab 12A Track-03 設備燈號變紅，TCS 介面顯示機台處於 Invalid State"),
        ("配方管理", "配方下載逾時", "Track-03 準備跑新批次時，TAP 下載 Recipe 失敗，顯示網路逾時"),
        ("設備通訊", "現場緊急呼叫", "Fab 12A 黃光區 Track-03 機台無法進料，請盡速派員確認網路或主機連線")
    ]

    reporters = ["林工程師", "陳技術員", "張組長", "王作業員", "李副理", "黃專員", "劉工程師", "趙技術員"]
    
    rows = []
    case_counter = 1000

    logger.info(f"🔄 開始生成過去 {days} 天的模擬 Case 數據 (系統: {', '.join(systems)})...")

    # 判斷目標月份 (近 30 天為當月/最近一個分析月)
    current_month_str = base_date.strftime("%Y-%m")

    for day_offset in range(days + 1):
        current_date = start_date + timedelta(days=day_offset)
        is_yesterday = (day_offset == days - 1) # 設定昨天為晨會異常日
        is_target_month = (current_date.strftime("%Y-%m") == current_month_str)

        for sys_name in systems:
            # 正常情況下每個系統每天 1 ~ 3 筆 Case
            case_count = random.randint(1, 3)
            
            # 若為昨天且為 tcs/tap，製造「晨會/課會日暴增」異常
            if is_yesterday and sys_name == "tcs/tap":
                case_count = 24
            elif is_target_month and sys_name == "tcs/tap":
                # 在當前月份中，tcs/tap 稍微活躍 (每天 3~6 筆)，製造「月報級異常」
                case_count = random.randint(3, 6)
            
            for _ in range(case_count):
                case_counter += 1
                case_id = f"INC-{current_date.strftime('%Y%m%d')}-{case_counter}"
                
                # 隨機產生當天的小時與分鐘
                hour = random.randint(8, 20)
                minute = random.randint(0, 59)
                created_at = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
                
                reporter = random.choice(reporters)

                # 如果是昨天且是 tcs/tap 的異常集中群 (85% 機率集中在 Fab 12A Track-03)
                if is_yesterday and sys_name == "tcs/tap" and random.random() < 0.85:
                    plant = "Fab 12A"
                    device = "Track-03"
                    category, title, desc = random.choice(tap_anomaly_issues)
                elif is_target_month and sys_name == "tcs/tap" and random.random() < 0.60:
                    # 在目標月份中，偏重出現「設備通訊」與「派工作業」這兩大類異常
                    plant = random.choice(["Fab 12A", "Fab 12B"])
                    device = "Track-03" if random.random() < 0.5 else f"Tool-{random.randint(10, 30)}"
                    category, title, desc = random.choice(tap_anomaly_issues)
                else:
                    plant = random.choice(plants)
                    device = f"Tool-{random.randint(10, 99)}" if random.random() > 0.4 else "General"
                    # 依系統挑選一般描述
                    specific_list = system_routine_issues.get(sys_name, routine_issues)
                    category, title, desc = random.choice(specific_list)

                rows.append({
                    "case_id": case_id,
                    "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "system_name": sys_name,
                    "category": category,
                    "plant": plant,
                    "device": device,
                    "title": title,
                    "description": desc,
                    "reporter": reporter
                })

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"✅ 成功生成 {len(df)} 筆測試資料 (含 category 欄位)，已儲存至: {os.path.abspath(output_path)}")
    return df

if __name__ == "__main__":
    generate_mock_data()

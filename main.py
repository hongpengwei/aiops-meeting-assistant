import argparse
import os
import sys
from datetime import datetime, timedelta
import yaml
import pandas as pd
import logging

from src.utils import setup_logging, fix_windows_encoding

# 解決 Windows console cp950 編碼問題
fix_windows_encoding()
logger = logging.getLogger(__name__)

from src.loaders.factory import create_data_loader
from src.analytics.detector import AnomalyDetector
from src.ai.analyzer import AIAnalyzer
from src.notifications.reporter import ReportGenerator

def load_config(config_path: str = "./config/config.yaml") -> dict:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"找不到設定檔: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_pipeline(mode: str = "daily", target_date_str: str = None, config_path: str = "./config/config.yaml"):
    setup_logging()
    logger.info("=" * 60)
    logger.info("🚀 啟動 AIOps 晨會 / 課會智能監控分析系統")
    logger.info(f"⏰ 執行模式: {mode.upper()} (晨會模式: daily | 課會模式: weekly)")
    logger.info("=" * 60)

    # 1. 載入設定
    config = load_config(config_path)
    logger.info(f"[1/5] ⚙️ 設定檔載入成功 (資料來源模式: {config.get('data_source', {}).get('type')})")

    # 2. 建立 DataLoader 並抓取資料
    loader = create_data_loader(config)
    
    # 決定抓取的時間區間 (向前抓取足夠的歷史資料，例如 30 天)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=35)
    
    try:
        df = loader.load_cases(start_date=start_date, end_date=end_date)
        logger.info(f"[2/5] 📦 成功讀取 {len(df)} 筆 Case 歷史資料")
    except FileNotFoundError as e:
        if os.environ.get("AIOPS_ENV") == "production":
            raise RuntimeError(f"在 production 環境下無法讀取資料，且禁止自動生成測試數據！原始錯誤: {e}") from e
        
        logger.warning(f"[2/5] ⚠️ {e}")
        logger.info("💡 正在自動為您生成測試數據 (scripts/generate_mock_data.py)...")
        from scripts.generate_mock_data import generate_mock_data
        generate_mock_data()
        df = loader.load_cases(start_date=start_date, end_date=end_date)
        logger.info(f"[2/5] 📦 成功讀取 {len(df)} 筆 Case 歷史資料")

    # 3. 執行統計異常檢測
    detector = AnomalyDetector(config)
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date() if target_date_str else None

    if mode == "daily":
        result = detector.analyze_daily(df, target_date=target_date)
    else:
        result = detector.analyze_weekly(df, target_week_end=target_date)

    logger.info(f"[3/5] 📊 統計檢測完成！")
    logger.info(f"  - 統計期間: {result.target_period_str}")
    logger.info(f"  - 基準區間: {result.baseline_period_str}")
    logger.info(f"  - 異常狀態: {'🔴 偵測到異常數量暴增' if result.is_anomaly_detected else '🟢 全系統運作正常'}")

    for s in result.systems:
        status_icon = "🔴" if s.is_anomaly else "🟢"
        logger.info(f"    {status_icon} {s.system_name:<15}: 當期 {s.target_count:>2} 件 (基準均值 {s.baseline_avg:>4.1f} 件) | {s.reason}")

    # 4. AI 深度歸因分析 (若有異常系統才觸發)
    ai_analyses = {}
    if result.is_anomaly_detected:
        logger.info(f"[4/5] 🤖 啟動 AI 案件文字描述深度歸因 (共 {len(result.anomalous_systems)} 個系統需分析)...")
        ai_analyzer = AIAnalyzer(config)
        
        for sys_metric in result.anomalous_systems:
            sys_name = sys_metric.system_name
            sys_cases_df = result.target_cases_df[result.target_cases_df["system_name"] == sys_name]
            logger.info(f"  🔍 正在分析 [{sys_name}] 的 {len(sys_cases_df)} 筆提報人描述...")
            
            analysis_text = ai_analyzer.analyze_system_cases(
                system_name=sys_name,
                target_period_str=result.target_period_str,
                cases_df=sys_cases_df
            )
            ai_analyses[sys_name] = analysis_text
    else:
        logger.info(f"[4/5] 🟢 無異常系統，略過 AI 分析步驟 (節省 Token 與運算成本)")

    # 5. 產出報告並推播
    logger.info(f"[5/5] 📢 產出會議簡報與推播發送...")
    reporter = ReportGenerator(config)
    md_content, html_content = reporter.generate_and_dispatch(result, ai_analyses)

    logger.info("=" * 60)
    logger.info("✅ 全部作業完成！以下為會前簡報重點預覽：")
    logger.info("=" * 60)
    logger.info("\n" + md_content)
    logger.info("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="AIOps 晨會 / 課會智能監控與歸因助手")
    parser.add_argument(
        "--mode", 
        choices=["daily", "weekly"], 
        default="daily", 
        help="執行模式: daily (每日晨會: 昨日 vs 前7天) 或 weekly (每週課會: 上週 vs 過去週平均)"
    )
    parser.add_argument(
        "--target-date", 
        type=str, 
        default=None, 
        help="指定分析日期 (格式: YYYY-MM-DD)，若未指定預設取昨日/最新一天"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="./config/config.yaml", 
        help="設定檔路徑"
    )

    args = parser.parse_args()
    run_pipeline(mode=args.mode, target_date_str=args.target_date, config_path=args.config)

if __name__ == "__main__":
    main()

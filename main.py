import argparse
import os
import sys
from datetime import datetime, timedelta
import yaml
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from src.utils import (
    setup_logging,
    fix_windows_encoding,
    get_yesterday_range,
    get_weekly_range,
    get_last_full_month_range
)

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

def run_pipeline(mode: str = "daily", target_date_str: str = None, config_path: str = "./config/config.yaml", cli_plants: str = None):
    setup_logging()
    logger.info("=" * 60)
    logger.info("🚀 啟動 AIOps 晨會 / 課會 / 月會智能監控分析系統")
    mode_name_map = {"daily": "晨會模式 (昨日全天 vs 前7天)", "weekly": "課會模式 (上週完整週 vs 過去週均)", "monthly": "月會模式 (上月全月: 系統級 -> 類別級兩層檢測)"}
    logger.info(f"⏰ 執行模式: {mode.upper()} ({mode_name_map.get(mode, mode)})")
    logger.info("=" * 60)

    # 1. 載入設定
    config = load_config(config_path)
    logger.info(f"[1/5] ⚙️ 設定檔載入成功 (資料來源模式: {config.get('data_source', {}).get('type')})")

    # 判斷目標廠區 (CLI 參數優先，其次為 config.yaml 中的 thresholds.<mode>.plants)
    mode_cfg = config.get("thresholds", {}).get(mode, {})
    if cli_plants:
        target_plants = [p.strip() for p in cli_plants.split(",") if p.strip()]
    else:
        cfg_plants = mode_cfg.get("plants", [])
        if isinstance(cfg_plants, str):
            target_plants = [p.strip() for p in cfg_plants.split(",") if p.strip()]
        elif isinstance(cfg_plants, list):
            target_plants = [str(p).strip() for p in cfg_plants if str(p).strip()]
        else:
            target_plants = []

    plants_str = ", ".join(target_plants) if target_plants else "全廠區"

    # 2. 根據模式計算精確的日曆完整週期邊界 (避免滑動時間誤差)
    if mode == "daily":
        start_date, end_date, target_date = get_yesterday_range(target_date_str, history_days=35)
        period_desc = f"目標昨日: {target_date}"
    elif mode == "weekly":
        start_date, end_date, target_date = get_weekly_range(target_date_str, history_weeks=8)
        period_desc = f"目標週結束日: {target_date}"
    else:  # monthly
        start_date, end_date, target_month_str_calc = get_last_full_month_range(target_date_str, history_months=6)
        period_desc = f"目標月份: {target_month_str_calc}"

    logger.info(f"📅 統計區間鎖定: {period_desc} (資料載入範圍: {start_date.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_date.strftime('%Y-%m-%d %H:%M:%S')})")

    # 建立 DataLoader 並抓取資料
    loader = create_data_loader(config)
    
    try:
        df = loader.load_cases(start_date=start_date, end_date=end_date)
        logger.info(f"[2/5] 📦 成功讀取 {len(df)} 筆 Case 歷史資料")
    except FileNotFoundError as e:
        if os.environ.get("AIOPS_ENV") == "production":
            raise RuntimeError(f"在 production 環境下無法讀取資料，且禁止自動生成測試數據！原始錯誤: {e}") from e
        
        # 僅在 CSV 模式下才嘗試自動生成測試數據
        data_source_type = config.get("data_source", {}).get("type", "csv")
        if data_source_type != "csv":
            raise RuntimeError(f"資料來源類型為 '{data_source_type}'，無法自動生成測試數據。請檢查連線設定。原始錯誤: {e}") from e

        csv_path = config.get("data_source", {}).get("csv", {}).get("file_path", "./data/mock_cases.csv")
        logger.warning(f"[2/5] ⚠️ {e}")
        logger.info(f"💡 正在自動為您生成測試數據至 {csv_path} (scripts/generate_mock_data.py)...")
        from scripts.generate_mock_data import generate_mock_data
        generate_mock_data(days=180, output_path=csv_path)
        df = loader.load_cases(start_date=start_date, end_date=end_date)
        logger.info(f"[2/5] 📦 成功讀取 {len(df)} 筆 Case 歷史資料")

    # 廠區過濾 (若有指定特定廠區)
    if target_plants and not df.empty:
        orig_count = len(df)
        target_plants_upper = {p.upper() for p in target_plants}
        df = df[df["plant"].astype(str).str.strip().str.upper().isin(target_plants_upper)]
        logger.info(f"🏭 廠區篩選鎖定: 【{plants_str}】 (篩選後筆數: {len(df)} / 原始筆數: {orig_count})")
    else:
        logger.info(f"🏭 廠區分析範圍: 【{plants_str}】")

    # 3. 執行統計異常檢測
    detector = AnomalyDetector(config)

    if mode == "daily":
        result = detector.analyze_daily(df, target_date=target_date, plants_str=plants_str)
    elif mode == "weekly":
        result = detector.analyze_weekly(df, target_week_end=target_date, plants_str=plants_str)
    else:  # monthly
        result = detector.analyze_monthly(df, target_month=target_month_str_calc, plants_str=plants_str)


    logger.info(f"[3/5] 📊 統計檢測完成！")
    logger.info(f"  - 統計期間: {result.target_period_str}")
    logger.info(f"  - 基準區間: {result.baseline_period_str}")
    logger.info(f"  - 分析廠區: {result.plants_str}")
    logger.info(f"  - 異常狀態: {'🔴 偵測到異常數量暴增' if result.is_anomaly_detected else '🟢 全系統運作正常'}")

    for s in result.systems:
        status_icon = "🔴" if s.is_anomaly else "🟢"
        logger.info(f"    {status_icon} {s.system_name:<15}: 當期 {s.target_count:>2} 件 (基準均值 {s.baseline_avg:>4.1f} 件) | {s.reason}")
        if result.anomalous_categories and s.system_name in result.anomalous_categories:
            for cat_m in result.anomalous_categories[s.system_name]:
                logger.info(f"      ↳ 🔴 類別【{cat_m.category_name}】: 當期 {cat_m.target_count} 件 (基準均值 {cat_m.baseline_avg:.1f} 件) | {cat_m.reason}")

    # 4. AI 深度歸因分析 (若有異常才觸發)
    ai_analyses = {}
    if result.is_anomaly_detected:
        ai_analyzer = AIAnalyzer(config)

        if mode in ["weekly", "monthly"]:
            # 週報與月報模式：支援系統級與類別級兩層深度歸因
            total_anom_cats = sum(len(cats) for cats in result.anomalous_categories.values())
            period_unit = "月" if mode == "monthly" else "週"
            logger.info(f"\n[4/5] 🤖 啟動{period_unit}報 AI 類別文字描述深度歸因 (共 {len(result.anomalous_systems)} 個系統總量暴增、{total_anom_cats} 個類別暴增需分析)...")

            # 使用 ThreadPoolExecutor 併發呼叫 AI API，減少多系統/類別暴增時的等待時間
            futures = {}
            with ThreadPoolExecutor(max_workers=4) as executor:
                for sys_metric in result.systems:
                    sys_name = sys_metric.system_name
                    anom_cats = result.anomalous_categories.get(sys_name, [])

                    if anom_cats:
                        for cat_metric in anom_cats:
                            cat_name = cat_metric.category_name
                            cat_cases_df = result.target_cases_df[
                                (result.target_cases_df["system_name"] == sys_name) & 
                                (result.target_cases_df["category"] == cat_name)
                            ]
                            unit_str = "當月" if mode == "monthly" else "當週"
                            avg_str = "月均" if mode == "monthly" else "週均"
                            key = f"系統 `{sys_name}` - 類別【{cat_name}】({unit_str} {cat_metric.target_count} 件, {avg_str} {cat_metric.baseline_avg:.1f} 件)"
                            logger.info(f"  🔍 提交分析任務 [{sys_name}] 類別【{cat_name}】({len(cat_cases_df)} 筆描述)...")
                            future = executor.submit(
                                ai_analyzer.analyze_category_cases,
                                system_name=sys_name,
                                category_name=cat_name,
                                target_period_str=result.target_period_str,
                                cases_df=cat_cases_df
                            )
                            futures[future] = key
                    elif sys_metric.is_anomaly:
                        sys_cases_df = result.target_cases_df[result.target_cases_df["system_name"] == sys_name]
                        key = f"系統 `{sys_name}` (全案件綜合歸因)"
                        logger.info(f"  🔍 提交分析任務 [{sys_name}] 全類別 ({len(sys_cases_df)} 筆描述)...")
                        future = executor.submit(
                            ai_analyzer.analyze_system_cases,
                            system_name=sys_name,
                            target_period_str=result.target_period_str,
                            cases_df=sys_cases_df
                        )
                        futures[future] = key

                # 收集併發結果
                for future in as_completed(futures):
                    key = futures[future]
                    try:
                        ai_analyses[key] = future.result()
                        logger.info(f"  ✅ {key} 分析完成")
                    except Exception as e:
                        logger.error(f"  ❌ {key} 分析失敗: {e}")
                        ai_analyses[key] = f"AI 分析失敗: {e}"
        else:
            # 晨會模式：系統級綜合歸因
            logger.info(f"\n[4/5] 🤖 啟動 AI 案件文字描述深度歸因 (共 {len(result.anomalous_systems)} 個系統需分析)...")
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
        logger.info(f"\n[4/5] 🟢 無異常系統/類別，略過 AI 分析步驟 (節省 Token 與運算成本)")

    # 5. 產出報告並推播
    logger.info(f"\n[5/5] 📢 產出會議簡報與推播發送...")
    reporter = ReportGenerator(config)
    md_content, html_content = reporter.generate_and_dispatch(result, ai_analyses)

    logger.info("=" * 60)
    logger.info("✅ 全部作業完成！以下為會前簡報重點預覽：")
    logger.info("=" * 60)
    logger.info("\n" + md_content)
    logger.info("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="AIOps 晨會 / 課會 / 月會智能監控與歸因助手")
    parser.add_argument(
        "--mode", 
        choices=["daily", "weekly", "monthly"], 
        default="daily", 
        help="執行模式: daily (每日晨會: 昨日 vs 前7天), weekly (每週課會: 上週 vs 過去週均), monthly (每月課會: 系統級+類別級兩層檢測)"
    )
    parser.add_argument(
        "--target-date", 
        type=str, 
        default=None, 
        help="指定分析日期/月份 (格式: YYYY-MM-DD 或 YYYY-MM)，若未指定預設取最新日/最新月"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="./config/config.yaml", 
        help="設定檔路徑"
    )
    parser.add_argument(
        "--plant", "--plants",
        dest="plants",
        type=str,
        default=None,
        help="指定分析廠區 (如: F12A 或逗號分隔多廠區 F12A,F14B)。未指定時讀取 config.yaml 各模式設定"
    )

    args = parser.parse_args()
    run_pipeline(mode=args.mode, target_date_str=args.target_date, config_path=args.config, cli_plants=args.plants)

if __name__ == "__main__":
    main()

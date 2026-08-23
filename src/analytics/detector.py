from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd

@dataclass
class SystemMetrics:
    system_name: str
    target_count: int
    baseline_avg: float
    baseline_std: float
    diff: float
    growth_rate: float        # 增長百分比 (e.g. +150.0%)
    is_anomaly: bool
    reason: str = ""

@dataclass
class AnomalyDetectionResult:
    mode: str                 # 'daily' 或 'weekly'
    target_period_str: str    # 目標期間標籤 (例如: "2026-08-22")
    baseline_period_str: str  # 基準期間標籤 (例如: "2026-08-15 ~ 2026-08-21 (前7天)")
    is_anomaly_detected: bool
    systems: List[SystemMetrics] = field(default_factory=list)
    anomalous_systems: List[SystemMetrics] = field(default_factory=list)
    target_cases_df: pd.DataFrame = field(default_factory=pd.DataFrame)

class AnomalyDetector:
    """
    統計異常檢測引擎：
    - 晨會 (daily): 比較昨日 vs 前 7 天平均
    - 課會 (weekly): 比較上週 vs 過去 N 週週平均
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("thresholds", {})
        self.daily_cfg = self.config.get("daily", {"baseline_days": 7, "multiplier": 1.4, "min_spike_cases": 5})
        self.weekly_cfg = self.config.get("weekly", {"baseline_weeks": 4, "multiplier": 1.3, "min_spike_cases": 10})

    def analyze_daily(self, df: pd.DataFrame, target_date: Optional[datetime.date] = None) -> AnomalyDetectionResult:
        """
        每日晨會分析：昨日 vs 前 7 天
        """
        if df.empty:
            return AnomalyDetectionResult(
                mode="daily",
                target_period_str=str(target_date or "N/A"),
                baseline_period_str="N/A",
                is_anomaly_detected=False
            )

        df = df.copy()
        df["date"] = df["created_at"].dt.date

        # 若未指定 target_date，預設取資料中最晚的一天
        if target_date is None:
            target_date = df["date"].max()

        baseline_days = self.daily_cfg.get("baseline_days", 7)
        multiplier = self.daily_cfg.get("multiplier", 1.4)
        min_spike = self.daily_cfg.get("min_spike_cases", 5)

        baseline_start_date = target_date - timedelta(days=baseline_days)
        baseline_end_date = target_date - timedelta(days=1)

        # 拆分目標日與基準區間
        target_df = df[df["date"] == target_date]
        baseline_df = df[(df["date"] >= baseline_start_date) & (df["date"] <= baseline_end_date)]

        # 計算所有出現過的系統清單
        all_systems = sorted(list(set(df["system_name"].unique())))

        system_metrics_list = []
        anomalous_systems = []

        # 基準天數（實際有幾天）
        actual_baseline_days = max(1, (baseline_end_date - baseline_start_date).days + 1)

        for sys_name in all_systems:
            sys_target_df = target_df[target_df["system_name"] == sys_name]
            target_count = len(sys_target_df)

            sys_base_df = baseline_df[baseline_df["system_name"] == sys_name]
            # 計算基準期每日 counts
            daily_counts = sys_base_df.groupby("date").size()
            # 補齊沒有 case 的日期為 0
            base_avg = len(sys_base_df) / actual_baseline_days
            base_std = daily_counts.std() if len(daily_counts) > 1 else 0.0

            diff = target_count - base_avg
            growth_rate = ((target_count - base_avg) / max(base_avg, 1.0)) * 100.0

            is_anomaly = False
            reason = ""

            # 異常判定規則：
            # 1. 超過平均值 * multiplier
            # 2. 且增加的絕對數量 >= min_spike_cases
            if target_count >= (base_avg * multiplier) and diff >= min_spike:
                is_anomaly = True
                reason = f"昨日 {target_count} 件，超過前 {actual_baseline_days} 天平均 ({base_avg:.1f} 件) 達 {growth_rate:+.0f}% (增加 {diff:+.1f} 件)"
            elif target_count == 0 and base_avg == 0:
                reason = "運作正常，無案件"
            else:
                reason = f"正常範圍 (昨日 {target_count} 件 / 平均 {base_avg:.1f} 件)"

            metric = SystemMetrics(
                system_name=sys_name,
                target_count=target_count,
                baseline_avg=base_avg,
                baseline_std=base_std,
                diff=diff,
                growth_rate=growth_rate,
                is_anomaly=is_anomaly,
                reason=reason
            )
            system_metrics_list.append(metric)
            if is_anomaly:
                anomalous_systems.append(metric)

        return AnomalyDetectionResult(
            mode="daily",
            target_period_str=str(target_date),
            baseline_period_str=f"{baseline_start_date} ~ {baseline_end_date} (前 {actual_baseline_days} 天)",
            is_anomaly_detected=len(anomalous_systems) > 0,
            systems=system_metrics_list,
            anomalous_systems=anomalous_systems,
            target_cases_df=target_df
        )

    def analyze_weekly(self, df: pd.DataFrame, target_week_end: Optional[datetime.date] = None) -> AnomalyDetectionResult:
        """
        每週課會分析：上週 (7天) vs 過去 N 週
        """
        if df.empty:
            return AnomalyDetectionResult(
                mode="weekly",
                target_period_str=str(target_week_end or "N/A"),
                baseline_period_str="N/A",
                is_anomaly_detected=False
            )

        df = df.copy()
        df["date"] = df["created_at"].dt.date

        if target_week_end is None:
            target_week_end = df["date"].max()

        # 上週 7 天
        target_week_start = target_week_end - timedelta(days=6)

        baseline_weeks = self.weekly_cfg.get("baseline_weeks", 4)
        multiplier = self.weekly_cfg.get("multiplier", 1.3)
        min_spike = self.weekly_cfg.get("min_spike_cases", 10)

        baseline_start_date = target_week_start - timedelta(days=baseline_weeks * 7)
        baseline_end_date = target_week_start - timedelta(days=1)

        target_df = df[(df["date"] >= target_week_start) & (df["date"] <= target_week_end)]
        baseline_df = df[(df["date"] >= baseline_start_date) & (df["date"] <= baseline_end_date)]

        all_systems = sorted(list(set(df["system_name"].unique())))

        system_metrics_list = []
        anomalous_systems = []

        for sys_name in all_systems:
            sys_target_df = target_df[target_df["system_name"] == sys_name]
            target_count = len(sys_target_df)

            sys_base_df = baseline_df[baseline_df["system_name"] == sys_name]
            # 歷史週平均
            base_weekly_avg = len(sys_base_df) / max(baseline_weeks, 1)

            diff = target_count - base_weekly_avg
            growth_rate = ((target_count - base_weekly_avg) / max(base_weekly_avg, 1.0)) * 100.0

            is_anomaly = False
            reason = ""

            if target_count >= (base_weekly_avg * multiplier) and diff >= min_spike:
                is_anomaly = True
                reason = f"當週 {target_count} 件，超過過去 {baseline_weeks} 週平均 ({base_weekly_avg:.1f} 件) 達 {growth_rate:+.0f}% (增加 {diff:+.1f} 件)"
            else:
                reason = f"正常範圍 (當週 {target_count} 件 / 週平均 {base_weekly_avg:.1f} 件)"

            metric = SystemMetrics(
                system_name=sys_name,
                target_count=target_count,
                baseline_avg=base_weekly_avg,
                baseline_std=0.0,
                diff=diff,
                growth_rate=growth_rate,
                is_anomaly=is_anomaly,
                reason=reason
            )
            system_metrics_list.append(metric)
            if is_anomaly:
                anomalous_systems.append(metric)

        return AnomalyDetectionResult(
            mode="weekly",
            target_period_str=f"{target_week_start} ~ {target_week_end} (當週)",
            baseline_period_str=f"{baseline_start_date} ~ {baseline_end_date} (前 {baseline_weeks} 週)",
            is_anomaly_detected=len(anomalous_systems) > 0,
            systems=system_metrics_list,
            anomalous_systems=anomalous_systems,
            target_cases_df=target_df
        )

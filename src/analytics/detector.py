import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

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

    def _analyze_common(
        self,
        df: pd.DataFrame,
        target_df: pd.DataFrame,
        baseline_df: pd.DataFrame,
        baseline_periods: int,
        multiplier: float,
        min_spike: int,
        mode: str,
        target_period_str: str,
        baseline_period_str: str,
        is_weekly: bool = False
    ) -> AnomalyDetectionResult:
        all_systems = sorted(df["system_name"].unique())

        system_metrics_list = []
        anomalous_systems = []

        target_counts = target_df.groupby("system_name").size() if not target_df.empty else pd.Series(dtype=int)
        baseline_totals = baseline_df.groupby("system_name").size() if not baseline_df.empty else pd.Series(dtype=int)

        if not baseline_df.empty:
            if is_weekly:
                baseline_df = baseline_df.copy()
                baseline_start_date = baseline_df["date"].min()
                # Calculate week index
                baseline_df["week"] = (pd.to_datetime(baseline_df["date"]) - pd.to_datetime(baseline_start_date)).dt.days // 7
                daily_or_weekly_counts = baseline_df.groupby(["system_name", "week"]).size()
            else:
                daily_or_weekly_counts = baseline_df.groupby(["system_name", "date"]).size()
        else:
            daily_or_weekly_counts = pd.Series(dtype=int)

        for sys_name in all_systems:
            target_count = int(target_counts.get(sys_name, 0))
            baseline_total = int(baseline_totals.get(sys_name, 0))
            
            base_avg = baseline_total / max(baseline_periods, 1)

            if sys_name in daily_or_weekly_counts:
                sys_counts = daily_or_weekly_counts[sys_name]
                base_std = sys_counts.std() if len(sys_counts) > 1 else 0.0
            else:
                base_std = 0.0

            diff = target_count - base_avg
            growth_rate = ((target_count - base_avg) / max(base_avg, 1.0)) * 100.0

            is_anomaly = False
            reason = ""

            if target_count >= (base_avg * multiplier) and diff >= min_spike:
                is_anomaly = True
                if is_weekly:
                    reason = f"當週 {target_count} 件，超過過去 {baseline_periods} 週平均 ({base_avg:.1f} 件) 達 {growth_rate:+.0f}% (增加 {diff:+.1f} 件)"
                else:
                    reason = f"昨日 {target_count} 件，超過前 {baseline_periods} 天平均 ({base_avg:.1f} 件) 達 {growth_rate:+.0f}% (增加 {diff:+.1f} 件)"
            elif not is_weekly and target_count == 0 and base_avg == 0:
                reason = "運作正常，無案件"
            else:
                if is_weekly:
                    reason = f"正常範圍 (當週 {target_count} 件 / 週平均 {base_avg:.1f} 件)"
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
            mode=mode,
            target_period_str=target_period_str,
            baseline_period_str=baseline_period_str,
            is_anomaly_detected=len(anomalous_systems) > 0,
            systems=system_metrics_list,
            anomalous_systems=anomalous_systems,
            target_cases_df=target_df
        )

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

        if target_date is None:
            target_date = df["date"].max()

        baseline_days = self.daily_cfg.get("baseline_days", 7)
        multiplier = self.daily_cfg.get("multiplier", 1.4)
        min_spike = self.daily_cfg.get("min_spike_cases", 5)

        baseline_start_date = target_date - timedelta(days=baseline_days)
        baseline_end_date = target_date - timedelta(days=1)

        target_df = df[df["date"] == target_date]
        baseline_df = df[(df["date"] >= baseline_start_date) & (df["date"] <= baseline_end_date)]

        actual_baseline_days = max(1, (baseline_end_date - baseline_start_date).days + 1)
        baseline_period_str = f"{baseline_start_date} ~ {baseline_end_date} (前 {actual_baseline_days} 天)"

        return self._analyze_common(
            df=df,
            target_df=target_df,
            baseline_df=baseline_df,
            baseline_periods=actual_baseline_days,
            multiplier=multiplier,
            min_spike=min_spike,
            mode="daily",
            target_period_str=str(target_date),
            baseline_period_str=baseline_period_str,
            is_weekly=False
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

        target_week_start = target_week_end - timedelta(days=6)

        baseline_weeks = self.weekly_cfg.get("baseline_weeks", 4)
        multiplier = self.weekly_cfg.get("multiplier", 1.3)
        min_spike = self.weekly_cfg.get("min_spike_cases", 10)

        baseline_start_date = target_week_start - timedelta(days=baseline_weeks * 7)
        baseline_end_date = target_week_start - timedelta(days=1)

        target_df = df[(df["date"] >= target_week_start) & (df["date"] <= target_week_end)]
        baseline_df = df[(df["date"] >= baseline_start_date) & (df["date"] <= baseline_end_date)]

        actual_baseline_weeks = max(baseline_weeks, 1)
        baseline_period_str = f"{baseline_start_date} ~ {baseline_end_date} (前 {baseline_weeks} 週)"
        target_period_str = f"{target_week_start} ~ {target_week_end} (當週)"

        return self._analyze_common(
            df=df,
            target_df=target_df,
            baseline_df=baseline_df,
            baseline_periods=actual_baseline_weeks,
            multiplier=multiplier,
            min_spike=min_spike,
            mode="weekly",
            target_period_str=target_period_str,
            baseline_period_str=baseline_period_str,
            is_weekly=True
        )

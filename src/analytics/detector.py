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
class CategoryMetrics:
    system_name: str
    category_name: str
    target_count: int
    baseline_avg: float
    diff: float
    growth_rate: float        # 增長百分比
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

@dataclass
class MonthlyDetectionResult:
    """
    月報兩層異常檢測結果：
    第 1 層：系統級 Case 總量暴增檢測
    第 2 層：針對暴增系統，深入檢測哪些具體 Category 異常暴增
    """
    mode: str = "monthly"
    target_period_str: str = ""
    baseline_period_str: str = ""
    is_anomaly_detected: bool = False
    systems: List[SystemMetrics] = field(default_factory=list)
    anomalous_systems: List[SystemMetrics] = field(default_factory=list)
    # 每個系統所有類別統計：{ "tcs/tap": [CategoryMetrics, ...] }
    system_categories: Dict[str, List[CategoryMetrics]] = field(default_factory=dict)
    # 暴增類別（供 AI 聚焦歸因分析）：{ "tcs/tap": [CategoryMetrics, ...] }
    anomalous_categories: Dict[str, List[CategoryMetrics]] = field(default_factory=dict)
    target_cases_df: pd.DataFrame = field(default_factory=pd.DataFrame)

class AnomalyDetector:
    """
    統計異常檢測引擎：
    - 晨會 (daily): 比較昨日 vs 前 7 天平均
    - 課會 (weekly): 比較上週 vs 過去 N 週週平均
    - 月會 (monthly): 兩層檢測 (本月系統總量 vs 過去 N 月均值 -> 異常系統的各 Category 深入比對)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("thresholds", {})
        self.daily_cfg = self.config.get("daily", {"baseline_days": 7, "multiplier": 1.4, "min_spike_cases": 5})
        self.weekly_cfg = self.config.get("weekly", {"baseline_weeks": 4, "multiplier": 1.3, "min_spike_cases": 10})
        self.monthly_cfg = self.config.get("monthly", {
            "baseline_months": 3,
            "multiplier": 1.3,
            "min_spike_cases": 15,
            "category_multiplier": 1.5,
            "category_min_spike": 5,
            "top_n_categories": 5
        })

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

    def analyze_monthly(self, df: pd.DataFrame, target_month: Optional[str] = None) -> MonthlyDetectionResult:
        """
        每月課會分析 (兩層檢測)：
        1. 第一層 (系統級)：本月 vs 過去 N 個月月平均
        2. 第二層 (類別級)：針對暴增系統，比對各 Category 數量與月均值，揪出暴增類別
        """
        if df.empty:
            return MonthlyDetectionResult(
                target_period_str=str(target_month or "N/A"),
                baseline_period_str="N/A",
                is_anomaly_detected=False
            )

        df = df.copy()
        df["month_str"] = df["created_at"].dt.strftime("%Y-%m")
        if "category" not in df.columns:
            df["category"] = "未分類"
        df["category"] = df["category"].fillna("未分類")

        if target_month is None:
            target_month = df["month_str"].max()
        else:
            # 支援傳入 YYYY-MM 或 YYYY-MM-DD
            target_month = str(target_month)[:7]

        baseline_months_count = self.monthly_cfg.get("baseline_months", 3)
        sys_multiplier = self.monthly_cfg.get("multiplier", 1.3)
        sys_min_spike = self.monthly_cfg.get("min_spike_cases", 15)
        cat_multiplier = self.monthly_cfg.get("category_multiplier", 1.5)
        cat_min_spike = self.monthly_cfg.get("category_min_spike", 5)
        top_n_cat = self.monthly_cfg.get("top_n_categories", 5)

        # 取得所有可用月份 (排序)
        all_months = sorted(df["month_str"].unique())
        if target_month in all_months:
            t_idx = all_months.index(target_month)
            baseline_months_list = all_months[max(0, t_idx - baseline_months_count):t_idx]
        else:
            # 若 target_month 不在資料中，取 target_month 之前的月份
            baseline_months_list = [m for m in all_months if m < target_month][-baseline_months_count:]

        target_df = df[df["month_str"] == target_month]
        baseline_df = df[df["month_str"].isin(baseline_months_list)]
        actual_baseline_months = max(1, len(baseline_months_list))

        if baseline_months_list:
            baseline_period_str = f"{baseline_months_list[0]} ~ {baseline_months_list[-1]} (前 {actual_baseline_months} 個月)"
        else:
            baseline_period_str = f"前 {baseline_months_count} 個月 (無完整歷史)"

        # ==========================================
        # 第 1 層：系統級檢測 (System Level)
        # ==========================================
        all_systems = sorted(df["system_name"].unique())
        system_metrics_list = []
        anomalous_systems = []

        target_sys_counts = target_df.groupby("system_name").size() if not target_df.empty else pd.Series(dtype=int)
        baseline_sys_totals = baseline_df.groupby("system_name").size() if not baseline_df.empty else pd.Series(dtype=int)

        for sys_name in all_systems:
            target_count = int(target_sys_counts.get(sys_name, 0))
            baseline_total = int(baseline_sys_totals.get(sys_name, 0))
            base_avg = baseline_total / actual_baseline_months

            diff = target_count - base_avg
            growth_rate = ((target_count - base_avg) / max(base_avg, 1.0)) * 100.0

            is_anomaly = False
            if target_count >= (base_avg * sys_multiplier) and diff >= sys_min_spike:
                is_anomaly = True
                reason = f"本月 {target_count} 件，超過前 {actual_baseline_months} 個月月均 ({base_avg:.1f} 件) 達 {growth_rate:+.0f}% (增加 {diff:+.1f} 件)"
            elif target_count == 0 and base_avg == 0:
                reason = "運作正常，無案件"
            else:
                reason = f"正常範圍 (本月 {target_count} 件 / 月均 {base_avg:.1f} 件)"

            metric = SystemMetrics(
                system_name=sys_name,
                target_count=target_count,
                baseline_avg=base_avg,
                baseline_std=0.0,
                diff=diff,
                growth_rate=growth_rate,
                is_anomaly=is_anomaly,
                reason=reason
            )
            system_metrics_list.append(metric)
            if is_anomaly:
                anomalous_systems.append(metric)

        # ==========================================
        # 第 2 層：類別級深入檢測 (Category Level)
        # 針對暴增系統 (或全系統)，展開所有 category 比對
        # ==========================================
        system_categories: Dict[str, List[CategoryMetrics]] = {}
        anomalous_categories: Dict[str, List[CategoryMetrics]] = {}

        # 優先分析暴增系統，若無暴增系統則可依需求處理
        for sys_metric in system_metrics_list:
            sys_name = sys_metric.system_name
            sys_target_df = target_df[target_df["system_name"] == sys_name]
            sys_base_df = baseline_df[baseline_df["system_name"] == sys_name]

            # 抓取該系統所有出現過的 category
            all_cats = sorted(set(sys_target_df["category"].unique()).union(set(sys_base_df["category"].unique())))
            if not all_cats:
                continue

            target_cat_counts = sys_target_df.groupby("category").size() if not sys_target_df.empty else pd.Series(dtype=int)
            base_cat_totals = sys_base_df.groupby("category").size() if not sys_base_df.empty else pd.Series(dtype=int)

            cat_metrics_list = []
            sys_anom_cats = []

            for cat_name in all_cats:
                cat_target_count = int(target_cat_counts.get(cat_name, 0))
                cat_base_total = int(base_cat_totals.get(cat_name, 0))
                cat_base_avg = cat_base_total / actual_baseline_months

                cat_diff = cat_target_count - cat_base_avg
                cat_growth_rate = ((cat_target_count - cat_base_avg) / max(cat_base_avg, 1.0)) * 100.0

                is_cat_anomaly = False
                cat_reason = ""

                # 類別異常判定：增長倍數 >= category_multiplier 且 差額 >= category_min_spike
                if cat_target_count >= (cat_base_avg * cat_multiplier) and cat_diff >= cat_min_spike:
                    is_cat_anomaly = True
                    cat_reason = f"暴增：本月 {cat_target_count} 件 (月均 {cat_base_avg:.1f} 件, {cat_growth_rate:+.0f}%)"
                else:
                    cat_reason = f"正常 (本月 {cat_target_count} 件 / 月均 {cat_base_avg:.1f} 件)"

                c_metric = CategoryMetrics(
                    system_name=sys_name,
                    category_name=cat_name,
                    target_count=cat_target_count,
                    baseline_avg=cat_base_avg,
                    diff=cat_diff,
                    growth_rate=cat_growth_rate,
                    is_anomaly=is_cat_anomaly,
                    reason=cat_reason
                )
                cat_metrics_list.append(c_metric)
                if is_cat_anomaly:
                    sys_anom_cats.append(c_metric)

            # 依案件數量由大到小排序
            cat_metrics_list.sort(key=lambda x: x.target_count, reverse=True)
            # 異常類別依增加量排序，並取 Top N
            sys_anom_cats.sort(key=lambda x: x.diff, reverse=True)
            sys_anom_cats = sys_anom_cats[:top_n_cat]

            system_categories[sys_name] = cat_metrics_list
            if sys_anom_cats:
                anomalous_categories[sys_name] = sys_anom_cats

        is_anomaly = len(anomalous_systems) > 0 or len(anomalous_categories) > 0

        return MonthlyDetectionResult(
            mode="monthly",
            target_period_str=f"{target_month} (當月)",
            baseline_period_str=baseline_period_str,
            is_anomaly_detected=is_anomaly,
            systems=system_metrics_list,
            anomalous_systems=anomalous_systems,
            system_categories=system_categories,
            anomalous_categories=anomalous_categories,
            target_cases_df=target_df
        )

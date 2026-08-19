# -*- coding: utf-8 -*-
"""异动检测核心算法

基于相对基准的三维异动检测：

| 维度 | 相对基准 | 数据来源 |
|------|----------|----------|
| 量比偏离 | 个股量比 vs 同批股票均值 | 当前批次 |
| 换手率偏离 | 个股换手率 vs 同批均值 | 当前批次 |
| 超额收益 | 个股涨跌幅 vs 同批均值 | 当前批次 |

v1 使用同批股票均值作为板块代理（适用于同类股/自选股场景）。
单只股票场景（n=1）回退到绝对阈值检测。

检测结果传递给 formatter 直接渲染，不对输出格式做任何假设。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from statistics import mean
from typing import Dict, List, Optional, Tuple

from .types import RiskSignal, StockData

logger = logging.getLogger(__name__)


# =============================================================================
# 阈值配置
# =============================================================================

@dataclass(init=False)
class DetectorThresholds:
    """异动检测阈值参数，支持按需定制"""

    # 量比偏离（倍数 vs 同批均值）
    volume_ratio_watch: float = 1.5
    volume_ratio_warn: float = 2.0
    volume_ratio_danger: float = 3.0

    # 换手率偏离（倍数 vs 同批均值）
    turnover_rate_watch: float = 1.5
    turnover_rate_warn: float = 2.5
    turnover_rate_danger: float = 4.0

    # 绝对阈值（n=1 单只场景回退）
    turnover_rate_pct_watch: float = 5.0
    turnover_rate_pct_warn: float = 10.0
    turnover_rate_pct_danger: float = 15.0

    # 超额收益（百分点）
    excess_return_watch: float = 2.5
    excess_return_warn: float = 5.0
    excess_return_danger: float = 8.0

    # 涨跌幅绝对阈值（单只场景回退）
    change_abs_watch: float = 5.0
    change_abs_warn: float = 7.0
    change_abs_danger: float = 9.8

    def __init__(
        self,
        volume_ratio_watch: float = 1.5,
        volume_ratio_warn: float = 2.0,
        volume_ratio_danger: float = 3.0,
        turnover_rate_watch: float = 1.5,
        turnover_rate_warn: float = 2.5,
        turnover_rate_danger: float = 4.0,
        turnover_rate_pct_watch: float = 5.0,
        turnover_rate_pct_warn: float = 10.0,
        turnover_rate_pct_danger: float = 15.0,
        excess_return_watch: float = 2.5,
        excess_return_warn: float = 5.0,
        excess_return_danger: float = 8.0,
        change_abs_watch: float = 5.0,
        change_abs_warn: float = 7.0,
        change_abs_danger: float = 9.8,
        **legacy_kwargs,
    ):
        # Backward-compat: accept old Chinese field names (simplified + traditional)
        legacy_map = {
            "volume_ratio_关注": "volume_ratio_watch",       # simplified
            "volume_ratio_關注": "volume_ratio_watch",       # traditional
            "volume_ratio_警告": "volume_ratio_warn",        # same in both
            "volume_ratio_危险": "volume_ratio_danger",      # simplified
            "volume_ratio_危險": "volume_ratio_danger",      # traditional
            "turnover_rate_关注": "turnover_rate_watch",       # simplified
            "turnover_rate_關注": "turnover_rate_watch",       # traditional
            "turnover_rate_警告": "turnover_rate_warn",        # same in both
            "turnover_rate_危险": "turnover_rate_danger",      # simplified
            "turnover_rate_危險": "turnover_rate_danger",      # traditional
            "turnover_rate_pct_关注": "turnover_rate_pct_watch",       # simplified
            "turnover_rate_pct_關注": "turnover_rate_pct_watch",       # traditional
            "turnover_rate_pct_警告": "turnover_rate_pct_warn",        # same in both
            "turnover_rate_pct_危险": "turnover_rate_pct_danger",      # simplified
            "turnover_rate_pct_危險": "turnover_rate_pct_danger",      # traditional
            "excess_return_关注": "excess_return_watch",       # simplified
            "excess_return_關注": "excess_return_watch",       # traditional
            "excess_return_警告": "excess_return_warn",        # same in both
            "excess_return_危险": "excess_return_danger",      # simplified
            "excess_return_危險": "excess_return_danger",      # traditional
            "change_abs_关注": "change_abs_watch",       # simplified
            "change_abs_關注": "change_abs_watch",       # traditional
            "change_abs_警告": "change_abs_warn",        # same in both
            "change_abs_危险": "change_abs_danger",      # simplified
            "change_abs_危險": "change_abs_danger",      # traditional
        }
        values = {
            "volume_ratio_watch": volume_ratio_watch,
            "volume_ratio_warn": volume_ratio_warn,
            "volume_ratio_danger": volume_ratio_danger,
            "turnover_rate_watch": turnover_rate_watch,
            "turnover_rate_warn": turnover_rate_warn,
            "turnover_rate_danger": turnover_rate_danger,
            "turnover_rate_pct_watch": turnover_rate_pct_watch,
            "turnover_rate_pct_warn": turnover_rate_pct_warn,
            "turnover_rate_pct_danger": turnover_rate_pct_danger,
            "excess_return_watch": excess_return_watch,
            "excess_return_warn": excess_return_warn,
            "excess_return_danger": excess_return_danger,
            "change_abs_watch": change_abs_watch,
            "change_abs_warn": change_abs_warn,
            "change_abs_danger": change_abs_danger,
        }
        for key, value in legacy_kwargs.items():
            mapped = legacy_map.get(key)
            if mapped is None:
                raise TypeError(f"DetectorThresholds got unexpected keyword argument '{key}'")
            values[mapped] = value
        for key, value in values.items():
            setattr(self, key, value)


# 默认阈值
DEFAULT_THRESHOLDS = DetectorThresholds()


# =============================================================================
# 辅助函数
# =============================================================================

def _level_from_threshold(
    value: float,
    threshold_watch: float,
    threshold_warn: float,
    threshold_danger: float,
) -> int:
    """根据阈值判断风险等级

    Args:
        value: 检测值
        threshold_watch: 关注阈值
        threshold_warn: 警告阈值
        threshold_danger: 危险阈值

    Returns:
        1=关注🔸, 2=警告🔶, 3=危险🔴, 0=无信号
    """
    if value >= threshold_danger:
        return 3
    if value >= threshold_warn:
        return 2
    if value >= threshold_watch:
        return 1
    return 0


def _has_upside_risk_confirmation(stock: StockData, thresholds: DetectorThresholds) -> bool:
    """Return whether a large upward move has extra overheating evidence.

    A positive limit-up move is a strong event, but not automatically a level-3
    risk. Upgrade it only when quote-side evidence also shows overheated volume
    or turnover. Falling limit moves keep their higher risk by direction.
    """
    if stock.volume_ratio >= thresholds.volume_ratio_danger:
        return True
    if 0 < stock.turnover_rate >= thresholds.turnover_rate_pct_warn:
        return True
    return False


def _calibrate_price_move_level(
    stock: StockData,
    level: int,
    thresholds: DetectorThresholds,
) -> Tuple[int, str]:
    """Calibrate absolute/relative price move level by direction and context."""
    if level < 3 or stock.change_percent <= 0:
        return level, ""
    if _has_upside_risk_confirmation(stock, thresholds):
        return level, "，且量能或换手同步过热"
    return 2, "，上涨方向未见量比/换手同步过热，按强异动观察"


# =============================================================================
# 各维度检测函数（内部）
# =============================================================================

def _detect_volume_ratio(
    stock: StockData,
    group_mean: float,
    thresholds: DetectorThresholds,
) -> Optional[RiskSignal]:
    """量比偏离检测

    个股量比 vs 同批股票均值量比。n=1 时使用绝对阈值。
    """
    vr = stock.volume_ratio
    if vr <= 0:
        return None

    if group_mean > 0:
        # 相对检测：偏离倍数
        ratio = vr / group_mean
        level = _level_from_threshold(
            ratio,
            thresholds.volume_ratio_watch,
            thresholds.volume_ratio_warn,
            thresholds.volume_ratio_danger,
        )
        deviation_unit = "x"
        deviation_val = ratio
        description = (
            f"量比{vr:.2f} vs 均值{group_mean:.2f}，"
            f"为均值的{ratio:.1f}倍"
        )
    else:
        return None

    if level == 0:
        return None

    return RiskSignal(
        stock_code=stock.code,
        risk_type="量比偏离",
        level=level,
        deviation_value=deviation_val,
        deviation_unit=deviation_unit,
        description=description,
    )


def _detect_turnover_rate(
    stock: StockData,
    group_mean: float,
    thresholds: DetectorThresholds,
    n_stocks: int,
) -> Optional[RiskSignal]:
    """换手率偏离检测

    有同批数据时使用相对倍数，单只时回退绝对百分比阈值。
    """
    tr = stock.turnover_rate
    if tr <= 0 or tr > 100:
        return None

    if n_stocks >= 2 and group_mean > 0:
        # 相对检测
        ratio = tr / group_mean
        level = _level_from_threshold(
            ratio,
            thresholds.turnover_rate_watch,
            thresholds.turnover_rate_warn,
            thresholds.turnover_rate_danger,
        )
        deviation_unit = "x"
        deviation_val = ratio
        description = (
            f"换手率{tr:.1f}% vs 均值{group_mean:.1f}%，"
            f"为均值的{ratio:.1f}倍"
        )
    else:
        # 绝对阈值
        level = _level_from_threshold(
            tr,
            thresholds.turnover_rate_pct_watch,
            thresholds.turnover_rate_pct_warn,
            thresholds.turnover_rate_pct_danger,
        )
        deviation_unit = "%"
        deviation_val = tr
        description = f"换手率{tr:.1f}%，超过常规交易活跃度阈值"

    if level == 0:
        return None

    return RiskSignal(
        stock_code=stock.code,
        risk_type="换手率偏高",
        level=level,
        deviation_value=deviation_val,
        deviation_unit=deviation_unit,
        description=description,
    )


def _detect_excess_return(
    stock: StockData,
    group_mean_change: float,
    thresholds: DetectorThresholds,
    n_stocks: int,
) -> Optional[RiskSignal]:
    """超额收益检测

    个股涨跌幅 vs 同批均值涨跌幅的绝对偏离。
    n=1 时使用涨跌幅绝对值阈值。
    """
    change = stock.change_percent

    if n_stocks >= 2:
        # 相对基准：偏离均值幅度
        diff = abs(change - group_mean_change)
        level = _level_from_threshold(
            diff,
            thresholds.excess_return_watch,
            thresholds.excess_return_warn,
            thresholds.excess_return_danger,
        )
        direction = "跑赢" if change > group_mean_change else "跑输"
        deviation_unit = "百分点"
        deviation_val = diff
        description = (
            f"个股涨跌幅{change:+.1f}%，"
            f"同批均值{group_mean_change:+.1f}%，"
            f"{direction}{diff:.1f}个百分点"
        )
        level, note = _calibrate_price_move_level(stock, level, thresholds)
        description += note
    else:
        # 单只回退：绝对值判定
        abs_change = abs(change)
        level = _level_from_threshold(
            abs_change,
            thresholds.change_abs_watch,
            thresholds.change_abs_warn,
            thresholds.change_abs_danger,
        )
        deviation_unit = "%"
        deviation_val = abs_change
        description = f"涨跌幅绝对值{abs_change:.1f}%"
        level, note = _calibrate_price_move_level(stock, level, thresholds)
        description += note

    if level == 0:
        return None

    return RiskSignal(
        stock_code=stock.code,
        risk_type="超额收益异动",
        level=level,
        deviation_value=deviation_val,
        deviation_unit=deviation_unit,
        description=description,
    )


# =============================================================================
# 公开入口
# =============================================================================

def detect(
    stocks: List[StockData],
    thresholds: Optional[DetectorThresholds] = None,
    sector_benchmarks: Optional[Dict[str, StockData]] = None,
) -> List[RiskSignal]:
    """检测股票异动信号

    Args:
        stocks: 同批次获取的股票数据列表（数量≥1）
        thresholds: 阈值参数，默认使用 DEFAULT_THRESHOLDS
        sector_benchmarks: {code: 板块代理StockData}，由外部数据源提供。
            提供后该股票的相对基准将使用板块均值而非同批均值。
            可覆盖同批均值和单只回退逻辑。

    Returns:
        按风险等级降序排列的异动信号列表

    Raises:
        ValueError: stocks 为空

    Notes:
        - 板块基准优先 > 同批均值(n≥2) > 绝对阈值(n=1)
        - 有板块基准的股票单只也能做相对偏离检测
        - 每只股票可能在多个维度产生信号
        - 返回结果按 level 降序排列（危险优先）
    """
    if not stocks:
        raise ValueError("stocks 不能为空")

    thresholds = thresholds or DEFAULT_THRESHOLDS
    benchmarks = sector_benchmarks or {}
    n = len(stocks)

    # 计算同批均值（仅在无板块基准时使用）
    group_mean_vr = mean(s.volume_ratio for s in stocks if s.volume_ratio > 0) if n >= 2 else 0.0
    group_mean_tr = mean(s.turnover_rate for s in stocks if s.turnover_rate > 0) if n >= 2 else 0.0
    group_mean_change = mean(s.change_percent for s in stocks) if n >= 2 else 0.0

    signals: List[RiskSignal] = []

    for stock in stocks:
        # 有板块基准时使用板块均值，否则用同批均值
        bench = benchmarks.get(stock.code)
        bm_vr = bench.volume_ratio if bench and bench.volume_ratio > 0 else group_mean_vr
        bm_tr = bench.turnover_rate if bench and bench.turnover_rate > 0 else group_mean_tr
        bm_change = bench.change_percent if bench else group_mean_change

        # 有板块基准且 n=1 时强制使用板块基准（不退化到绝对阈值）
        effective_n = max(n, 2) if bench else n

        for detector_fn in [
            _detect_volume_ratio,
            _detect_turnover_rate,
            _detect_excess_return,
        ]:
            try:
                if detector_fn == _detect_turnover_rate:
                    sig = detector_fn(stock, bm_tr, thresholds, effective_n)
                elif detector_fn == _detect_excess_return:
                    sig = detector_fn(stock, bm_change, thresholds, effective_n)
                else:
                    sig = detector_fn(stock, bm_vr, thresholds)

                if sig is not None:
                    signals.append(sig)
            except Exception as e:
                logger.warning(
                    "检测异常 [%s] %s: %s",
                    stock.code,
                    detector_fn.__name__,
                    e,
                )
                continue

    # 按风险等级降序排列（同级内保持检测顺序）
    signals.sort(key=lambda s: s.level, reverse=True)

    return signals


# v1 简易别名（推荐使用 detect）
detect_anomalies = detect

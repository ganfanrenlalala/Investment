# -*- coding: utf-8 -*-
"""Quote quality checks and normalization."""

from __future__ import annotations

from dataclasses import replace
import math
from typing import Iterable, List, Sequence, Tuple

from .types import StockData


# A provider field above this level is frequently a unit/field-index error.
# It can be a real value for a newly listed stock, so keep the threshold
# conservative and make the metric unavailable instead of inventing a value.
EXTREME_A_SHARE_TURNOVER_RATE = 50.0


def _is_finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _raw(stock: StockData) -> dict:
    return stock.raw if isinstance(stock.raw, dict) else {}


def _turnover_is_untrusted(stock: StockData) -> bool:
    if stock.market not in {"sh", "sz"} or not _is_finite(stock.turnover_rate):
        return False

    source = str(_raw(stock).get("turnover_rate_source") or "")
    if source == "provider_field_untrusted":
        return True
    return stock.turnover_rate > EXTREME_A_SHARE_TURNOVER_RATE and source != "derived_float_shares"


def assess_quote_quality(stocks: Sequence[StockData]) -> List[str]:
    """Return human-readable quality notes for suspicious market metrics."""
    notes: List[str] = []
    for stock in stocks:
        issues: List[str] = []
        if not _is_finite(stock.current_price) or stock.current_price <= 0:
            issues.append("现价不可用")
        price_fields = (stock.prev_close, stock.open_price, stock.high, stock.low)
        if any(not _is_finite(value) or value < 0 for value in price_fields):
            issues.append("价格字段不可用或存在负值")
        if (
            _is_finite(stock.high)
            and _is_finite(stock.low)
            and stock.high > 0
            and stock.low > 0
            and stock.high < stock.low
        ):
            issues.append("最高价低于最低价")
        if not _is_finite(stock.volume) or stock.volume < 0:
            issues.append("成交量不可用或为负")
        if not _is_finite(stock.amount) or stock.amount < 0:
            issues.append("成交额不可用或为负")
        if not _is_finite(stock.volume_ratio) or stock.volume_ratio < 0:
            issues.append("量比不可用或为负")
        if (
            not _is_finite(stock.turnover_rate)
            or stock.turnover_rate < 0
            or stock.turnover_rate > 100
        ):
            issues.append("换手率不可用或超出常规范围")
        if _turnover_is_untrusted(stock):
            issues.append("换手率极端或来源不可信")
        if (
            not _is_finite(stock.change_percent)
            or abs(stock.change_percent) > 30
        ) and stock.market in {"sh", "sz"}:
            issues.append("A股涨跌幅超出常规范围")

        if issues:
            notes.append(f"{stock.code} {stock.name}：{'；'.join(issues)}。")
    return notes


def normalize_quote_data(stocks: Iterable[StockData]) -> Tuple[List[StockData], List[str]]:
    """Normalize quote records while preserving the StockData public type.

    Suspicious optional metrics are set to zero so downstream formatters show
    `—` and detectors do not create misleading signals from bad provider fields.
    Core price data is not fabricated.
    """
    normalized: List[StockData] = []
    notes: List[str] = []

    for stock in stocks:
        if not _is_finite(stock.current_price) or stock.current_price <= 0:
            notes.append(f"{stock.code} {stock.name}：现价不可用，已从分析输入中剔除。")
            continue

        updates = {}
        stock_notes: List[str] = []

        if not _is_finite(stock.volume_ratio) or stock.volume_ratio < 0:
            updates["volume_ratio"] = 0.0
            stock_notes.append("量比无效，已按不可用处理")

        if (
            not _is_finite(stock.turnover_rate)
            or stock.turnover_rate < 0
            or stock.turnover_rate > 100
            or _turnover_is_untrusted(stock)
        ):
            updates["turnover_rate"] = 0.0
            stock_notes.append("换手率不可用、极端或来源不可信，已按不可用处理")

        if not _is_finite(stock.volume) or stock.volume < 0:
            updates["volume"] = 0
            stock_notes.append("成交量无效，已按不可用处理")

        if not _is_finite(stock.amount) or stock.amount < 0:
            updates["amount"] = 0.0
            stock_notes.append("成交额无效，已按不可用处理")

        for field_name in ("prev_close", "open_price", "high", "low"):
            value = getattr(stock, field_name)
            if not _is_finite(value) or value < 0:
                updates[field_name] = 0.0
                stock_notes.append(f"{field_name}价格字段无效，已按不可用处理")

        if (
            _is_finite(stock.high)
            and _is_finite(stock.low)
            and stock.high > 0
            and stock.low > 0
            and stock.high < stock.low
        ):
            updates["high"] = 0.0
            updates["low"] = 0.0
            stock_notes.append("最高价低于最低价，价格区间已按不可用处理")

        if (
            stock.market in {"sh", "sz"}
            and (not _is_finite(stock.change_percent) or abs(stock.change_percent) > 30)
        ):
            updates["change_percent"] = 0.0
            stock_notes.append("A股涨跌幅异常，已按不可用处理")

        normalized_stock = replace(stock, **updates) if updates else stock
        normalized.append(normalized_stock)

        if stock_notes:
            notes.append(f"{stock.code} {stock.name}：{'；'.join(stock_notes)}。")

    return normalized, notes

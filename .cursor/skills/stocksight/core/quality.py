# -*- coding: utf-8 -*-
"""Quote quality checks and normalization."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, List, Sequence, Tuple

from .types import StockData


def assess_quote_quality(stocks: Sequence[StockData]) -> List[str]:
    """Return human-readable quality notes for suspicious market metrics."""
    notes: List[str] = []
    for stock in stocks:
        issues: List[str] = []
        if stock.current_price <= 0:
            issues.append("现价不可用")
        if stock.prev_close < 0 or stock.open_price < 0 or stock.high < 0 or stock.low < 0:
            issues.append("价格字段存在负值")
        if stock.high > 0 and stock.low > 0 and stock.high < stock.low:
            issues.append("最高价低于最低价")
        if stock.volume < 0:
            issues.append("成交量为负")
        if stock.amount < 0:
            issues.append("成交额为负")
        if stock.volume_ratio < 0:
            issues.append("量比为负")
        if stock.turnover_rate < 0 or stock.turnover_rate > 100:
            issues.append("换手率不可用或超出常规范围")
        if abs(stock.change_percent) > 30 and stock.market in {"sh", "sz"}:
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
        updates = {}
        stock_notes: List[str] = []

        if stock.volume_ratio < 0:
            updates["volume_ratio"] = 0.0
            stock_notes.append("量比为负，已按不可用处理")

        if stock.turnover_rate < 0 or stock.turnover_rate > 100:
            updates["turnover_rate"] = 0.0
            stock_notes.append("换手率不可用或超出常规范围，已按不可用处理")

        if stock.volume < 0:
            updates["volume"] = 0
            stock_notes.append("成交量为负，已按不可用处理")

        if stock.amount < 0:
            updates["amount"] = 0.0
            stock_notes.append("成交额为负，已按不可用处理")

        normalized_stock = replace(stock, **updates) if updates else stock
        normalized.append(normalized_stock)

        if stock_notes:
            notes.append(f"{stock.code} {stock.name}：{'；'.join(stock_notes)}。")

    return normalized, notes

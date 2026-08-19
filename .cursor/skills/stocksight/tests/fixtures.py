# -*- coding: utf-8 -*-
"""Shared test fixtures for StockSight."""

from core import NewsItem, ReportData, RiskSignal, StockData


def sample_stock(**overrides):
    data = {
        "code": "600001",
        "name": "Sample",
        "current_price": 10.0,
        "prev_close": 9.8,
        "open_price": 9.9,
        "high": 10.2,
        "low": 9.7,
        "volume": 100000,
        "amount": 2000000.0,
        "volume_ratio": 2.2,
        "change_percent": 3.1,
        "turnover_rate": 4.0,
        "timestamp": "2026-05-18 15:00:00",
        "market": "sh",
    }
    data.update(overrides)
    return StockData(**data)


def sample_signal(**overrides):
    data = {
        "stock_code": "600001",
        "risk_type": "volume",
        "level": 2,
        "deviation_value": 1.5,
        "deviation_unit": "x",
        "description": "volume high",
    }
    data.update(overrides)
    return RiskSignal(**data)


def sample_report(**overrides):
    stock = overrides.pop("stock", sample_stock())
    signal = overrides.pop("signal", sample_signal(stock_code=stock.code))
    data = {
        "title": "Sample Report",
        "summary": "Sample summary",
        "stocks": [stock],
        "signals": [signal] if signal else [],
        "data_source": "unit",
        "timestamp": "2026-05-18 15:10:00",
        "news": [
            NewsItem(
                title="Sample news",
                source="Unit",
                url="https://example.com/news",
                published_at="2026-05-18",
                snippet="Sample snippet",
            )
        ],
    }
    data.update(overrides)
    return ReportData(**data)


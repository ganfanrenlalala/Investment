# -*- coding: utf-8 -*-
"""Fallback A-share historical K-line provider.

This module follows the lightweight idea used by mpquant/Ashare: use public
Sina daily K-line first, then Tencent qfq daily K-line as a backup. It avoids
extra runtime dependencies such as pandas and only returns StockHistory.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import requests

from core import HistoryBar, StockHistory

logger = logging.getLogger(__name__)

SINA_KLINE_URL = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
TENCENT_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.sina.com.cn/",
}


def _market_symbol(code: str) -> Optional[str]:
    clean = code.strip().lower()
    if clean.startswith(("sh", "sz")) and len(clean) == 8:
        return clean
    if len(clean) != 6 or not clean.isdigit():
        return None
    if clean.startswith(("6", "9")):
        return f"sh{clean}"
    if clean.startswith(("0", "2", "3")):
        return f"sz{clean}"
    return None


class AShareHistoryDataSource:
    """A-share historical daily K-line fallback provider."""

    def __init__(self, timeout: int = 10, max_retries: int = 1):
        self._session = requests.Session()
        self._timeout = timeout
        self._max_retries = max_retries

    def name(self) -> str:
        return "AShare History"

    def fetch_history(self, code: str, days: int = 80) -> StockHistory:
        symbol = _market_symbol(code)
        if symbol is None:
            return StockHistory(code=code)

        for fetcher in (self._fetch_sina_history, self._fetch_tencent_history):
            history = fetcher(code, symbol, days)
            if history.bars:
                return history
        return StockHistory(code=code)

    def _fetch_sina_history(self, code: str, symbol: str, days: int) -> StockHistory:
        params = {
            "symbol": symbol,
            "scale": "240",
            "ma": "no",
            "datalen": str(days + 10),
        }
        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.get(
                    SINA_KLINE_URL,
                    params=params,
                    headers=HEADERS,
                    timeout=self._timeout,
                )
                rows = response.json()
                bars = _parse_sina_rows(rows)
                if bars:
                    return StockHistory(code=code, bars=bars[-days:])
            except Exception as exc:
                logger.debug("Sina A-share history failed [%s] attempt %d: %s", code, attempt + 1, exc)
        return StockHistory(code=code)

    def _fetch_tencent_history(self, code: str, symbol: str, days: int) -> StockHistory:
        params = {
            "param": f"{symbol},day,,,{days + 10},qfq",
        }
        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.get(
                    TENCENT_KLINE_URL,
                    params=params,
                    headers={**HEADERS, "Referer": "https://gu.qq.com/"},
                    timeout=self._timeout,
                )
                payload = response.json()
                stock_payload = payload.get("data", {}).get(symbol, {})
                rows = stock_payload.get("qfqday") or stock_payload.get("day") or []
                bars = _parse_tencent_rows(rows)
                if bars:
                    return StockHistory(code=code, bars=bars[-days:])
            except Exception as exc:
                logger.debug("Tencent A-share history failed [%s] attempt %d: %s", code, attempt + 1, exc)
        return StockHistory(code=code)


def _parse_sina_rows(rows: object) -> List[HistoryBar]:
    if not isinstance(rows, list):
        return []

    bars: List[HistoryBar] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            bars.append(HistoryBar(
                date=str(row.get("day", ""))[:10],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(float(row.get("volume") or 0)),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return [bar for bar in bars if bar.date]


def _parse_tencent_rows(rows: object) -> List[HistoryBar]:
    if not isinstance(rows, list):
        return []

    bars: List[HistoryBar] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 6:
            continue
        try:
            bars.append(HistoryBar(
                date=str(row[0])[:10],
                open=float(row[1]),
                close=float(row[2]),
                high=float(row[3]),
                low=float(row[4]),
                volume=int(float(row[5])),
            ))
        except (TypeError, ValueError):
            continue
    return [bar for bar in bars if bar.date]

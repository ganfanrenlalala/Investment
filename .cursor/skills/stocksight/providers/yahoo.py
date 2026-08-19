# -*- coding: utf-8 -*-
"""Yahoo Finance quote provider for US equities.

Uses the public chart JSON endpoint:
https://query1.finance.yahoo.com/v8/finance/chart/{ticker}
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests

from core import DataSource, DataSourceError, FetchResult, HistoryBar, StockData, StockHistory

logger = logging.getLogger(__name__)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def _first_number(values) -> float:
    if not values:
        return 0.0
    for value in values:
        if value is not None:
            return float(value)
    return 0.0


def _last_number(values) -> float:
    if not values:
        return 0.0
    for value in reversed(values):
        if value is not None:
            return float(value)
    return 0.0


def _max_number(values) -> float:
    cleaned = [float(value) for value in values or [] if value is not None]
    return max(cleaned) if cleaned else 0.0


def _min_number(values) -> float:
    cleaned = [float(value) for value in values or [] if value is not None]
    return min(cleaned) if cleaned else 0.0


def _sum_int(values) -> int:
    return int(sum(float(value) for value in values or [] if value is not None))


def _parse_yahoo_chart(payload: dict, code: str) -> StockData:
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise DataSourceError(str(chart["error"]))

    results = chart.get("result") or []
    if not results:
        raise DataSourceError("Yahoo chart result is empty")

    result = results[0]
    meta = result.get("meta") or {}
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]

    close_values = quote.get("close") or []
    open_values = quote.get("open") or []
    high_values = quote.get("high") or []
    low_values = quote.get("low") or []
    volume_values = quote.get("volume") or []

    current_price = float(meta.get("regularMarketPrice") or _last_number(close_values))
    prev_close = float(
        meta.get("previousClose")
        or meta.get("chartPreviousClose")
        or meta.get("regularMarketPreviousClose")
        or 0.0
    )
    open_price = float(meta.get("regularMarketOpen") or _first_number(open_values))
    high = float(meta.get("regularMarketDayHigh") or _max_number(high_values))
    low = float(meta.get("regularMarketDayLow") or _min_number(low_values))
    volume = int(meta.get("regularMarketVolume") or _sum_int(volume_values))

    if current_price <= 0:
        raise DataSourceError("Yahoo chart missing regular market price")

    change_percent = (
        (current_price - prev_close) / prev_close * 100 if prev_close > 0 else 0.0
    )
    timestamp_value = meta.get("regularMarketTime")
    if timestamp_value:
        timestamp = datetime.fromtimestamp(int(timestamp_value)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    symbol = str(meta.get("symbol") or code).upper()
    currency = str(meta.get("currency") or "USD")

    return StockData(
        code=code,
        name=symbol,
        current_price=current_price,
        prev_close=prev_close,
        open_price=open_price,
        high=high,
        low=low,
        volume=volume,
        amount=volume * current_price / 10000,
        volume_ratio=0.0,
        change_percent=change_percent,
        turnover_rate=0.0,
        timestamp=timestamp,
        market="us",
        raw={
            "provider": "yahoo",
            "symbol": symbol,
            "currency": currency,
            "exchange": meta.get("exchangeName", ""),
        },
    )


def _parse_history_chart(payload: dict, symbol: str) -> List[HistoryBar]:
    """Parse Yahoo chart JSON into a list of HistoryBar."""
    import datetime as _dt
    chart = payload.get("chart") or {}
    results = chart.get("result") or []
    if not results:
        return []

    result = results[0]
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]

    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    bars: List[HistoryBar] = []
    for i in range(min(len(timestamps), len(closes))):
        if closes[i] is None:
            continue
        dt = _dt.datetime.fromtimestamp(int(timestamps[i]))
        bars.append(HistoryBar(
            date=dt.strftime("%Y-%m-%d"),
            open=float(opens[i]) if opens[i] is not None else 0.0,
            high=float(highs[i]) if highs[i] is not None else 0.0,
            low=float(lows[i]) if lows[i] is not None else 0.0,
            close=float(closes[i]),
            volume=int(volumes[i]) if volumes[i] is not None else 0,
        ))
    return bars


class YahooFinanceDataSource(DataSource):
    """Yahoo Finance data source for US tickers."""

    def fetch_history(self, symbol: str, days: int = 80) -> StockHistory:
        """Fetch historical daily OHLCV data for a US ticker.

        Args:
            symbol: US ticker symbol (e.g. 'AAPL')
            days: number of trading days to fetch (default 60)

        Returns:
            StockHistory with bars sorted by date ascending
        """
        import time as _time
        normalized_symbol = symbol.strip().upper()
        url = YAHOO_CHART_URL.format(symbol=normalized_symbol)

        params = {
            "range": f"{days + 5}d",
            "interval": "1d",
        }

        payload = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._session.get(
                    url, params=params, timeout=self._timeout,
                    headers={"User-Agent": "StockSight/1.0"},
                )
                if resp.status_code != 200:
                    if attempt == self._max_retries:
                        return StockHistory(code=symbol)
                    continue
                payload = resp.json()
                break
            except (ValueError, requests.RequestException):
                if attempt == self._max_retries:
                    return StockHistory(code=symbol)
                _time.sleep(0.5)

        if payload is None:
            return StockHistory(code=symbol)
        bars = _parse_history_chart(payload, normalized_symbol)
        return StockHistory(code=symbol, bars=bars)

    def __init__(self, timeout: int = 10, max_retries: int = 1):
        self._session = requests.Session()
        self._timeout = timeout
        self._max_retries = max_retries

    def name(self) -> str:
        return "Yahoo Finance"

    def fetch(self, codes: List[str]) -> FetchResult:
        if not codes:
            return {}, []

        result: Dict[str, StockData] = {}
        failed: List[str] = []

        for code in codes:
            symbol = code.strip().upper()
            if not symbol or not symbol.isalpha():
                failed.append(code)
                continue

            last_error: Optional[Exception] = None
            payload = None
            url = YAHOO_CHART_URL.format(symbol=symbol)
            for attempt in range(self._max_retries + 1):
                try:
                    response = self._session.get(
                        url,
                        params={"range": "1d", "interval": "1d"},
                        timeout=self._timeout,
                        headers={"User-Agent": "StockSight/1.0"},
                    )
                    if response.status_code != 200:
                        last_error = DataSourceError(f"HTTP {response.status_code}")
                        continue
                    payload = response.json()
                    break
                except (ValueError, requests.RequestException) as exc:
                    last_error = exc
                    logger.debug(
                        "Yahoo Finance request failed for %s on attempt %d: %s",
                        code,
                        attempt + 1,
                        exc,
                    )

            if payload is None:
                logger.debug("Yahoo Finance unavailable for %s: %s", code, last_error)
                failed.append(code)
                continue

            try:
                result[code] = _parse_yahoo_chart(payload, code)
            except DataSourceError as exc:
                logger.debug("Yahoo Finance parse failed for %s: %s", code, exc)
                failed.append(code)

        return result, failed

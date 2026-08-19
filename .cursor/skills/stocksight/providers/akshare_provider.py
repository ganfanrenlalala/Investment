# -*- coding: utf-8 -*-
"""Optional AkShare quote and history provider.

AkShare is a broad third-party data library with a heavier dependency tree than
StockSight's built-in HTTP providers, so this module imports it lazily. When the
package is not installed, the provider simply reports failure and the normal
failover chain can continue.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from core import DataSource, DataSourceError, FetchResult, HistoryBar, StockData, StockHistory


def _is_a_share_code(code: str) -> bool:
    return code.isdigit() and len(code) == 6 and code[0] in {"0", "3", "6"}


def _market_for_code(code: str) -> str:
    return "sh" if code.startswith("6") else "sz"


def _records(frame) -> List[dict]:
    if frame is None:
        return []
    if hasattr(frame, "to_dict"):
        return list(frame.to_dict("records"))
    return list(frame)


def _num(record: dict, *keys: str) -> float:
    for key in keys:
        value = record.get(key)
        if value in (None, "", "-", "--"):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _int(record: dict, *keys: str) -> int:
    return int(_num(record, *keys))


def _code_value(value) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(6) if text.isdigit() else text


class AkShareDataSource(DataSource):
    """Optional AkShare data source for A-share quotes and daily K-lines."""

    def __init__(self, ak_module=None):
        self._ak = ak_module

    def name(self) -> str:
        return "AkShare"

    def _load_akshare(self):
        if self._ak is not None:
            return self._ak
        try:
            import akshare as ak  # type: ignore
        except ImportError as exc:
            raise DataSourceError(
                "AkShare is not installed. Install it with `pip install akshare`."
            ) from exc
        self._ak = ak
        return ak

    def fetch(self, codes: List[str]) -> FetchResult:
        if not codes:
            return {}, []

        requested = [code.strip() for code in codes]
        a_share_codes = [code for code in requested if _is_a_share_code(code)]
        failed = [code for code in requested if code not in a_share_codes]
        if not a_share_codes:
            return {}, failed

        ak = self._load_akshare()
        try:
            records = _records(ak.stock_zh_a_spot_em())
        except Exception as exc:
            raise DataSourceError(f"AkShare A-share spot fetch failed: {exc}") from exc

        by_code = {_code_value(record.get("代码")): record for record in records}
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result: Dict[str, StockData] = {}
        for code in a_share_codes:
            record = by_code.get(code)
            if not record:
                failed.append(code)
                continue
            stock = self._stock_from_spot_record(code, record, timestamp)
            if stock.current_price <= 0:
                failed.append(code)
                continue
            result[code] = stock

        return result, failed

    def _stock_from_spot_record(self, code: str, record: dict, timestamp: str) -> StockData:
        current_price = _num(record, "最新价")
        prev_close = _num(record, "昨收")
        change_percent = _num(record, "涨跌幅")
        if prev_close <= 0 and current_price > 0:
            prev_close = current_price / (1 + change_percent / 100) if change_percent != -100 else 0.0

        return StockData(
            code=code,
            name=str(record.get("名称") or code),
            current_price=current_price,
            prev_close=prev_close,
            open_price=_num(record, "今开"),
            high=_num(record, "最高"),
            low=_num(record, "最低"),
            volume=_int(record, "成交量"),
            amount=_num(record, "成交额") / 10000,
            volume_ratio=_num(record, "量比"),
            change_percent=change_percent,
            turnover_rate=_num(record, "换手率"),
            timestamp=timestamp,
            market=_market_for_code(code),
            raw={
                "provider": "akshare",
                "source_api": "stock_zh_a_spot_em",
                "total_market_value": _num(record, "总市值"),
                "circulating_market_value": _num(record, "流通市值"),
                "pe": _num(record, "市盈率-动态"),
                "pb": _num(record, "市净率"),
            },
        )

    def fetch_history(self, code: str, days: int = 80) -> StockHistory:
        if not _is_a_share_code(code):
            return StockHistory(code=code)

        try:
            ak = self._load_akshare()
        except DataSourceError:
            return StockHistory(code=code)
        end = datetime.now()
        start = end - timedelta(days=max(days * 2 + 30, 120))
        try:
            frame = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust="qfq",
            )
        except Exception:
            return StockHistory(code=code)

        bars: List[HistoryBar] = []
        for record in _records(frame):
            date_text = str(record.get("日期") or record.get("date") or "")
            if not date_text:
                continue
            bars.append(
                HistoryBar(
                    date=date_text[:10],
                    open=_num(record, "开盘", "open"),
                    high=_num(record, "最高", "high"),
                    low=_num(record, "最低", "low"),
                    close=_num(record, "收盘", "close"),
                    volume=_int(record, "成交量", "volume"),
                )
            )
        return StockHistory(code=code, bars=bars[-days:])


__all__ = ["AkShareDataSource"]

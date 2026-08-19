# -*- coding: utf-8 -*-
"""EastMoney public announcement provider.

Uses EastMoney's public notice-list endpoint. No API key is required; failures
return empty results so the news chain can fall back to other providers.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Optional

import requests

from core import NewsItem
from ..base import NewsProvider


EASTMONEY_NOTICE_URL = "https://np-anotice-stock.eastmoney.com/api/security/ann"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://data.eastmoney.com/notices/",
}


def _extract_code(query: str) -> Optional[str]:
    match = re.search(r"\b([036]\d{5})\b", query or "")
    return match.group(1) if match else None


def _market_code(code: str) -> str:
    return "1" if code.startswith("6") else "0"


def _notice_url(code: str, art_code: str) -> str:
    if not art_code:
        return ""
    return f"https://data.eastmoney.com/notices/detail/{code}/{art_code}.html"


class EastMoneyNoticeProvider(NewsProvider):
    """Best-effort EastMoney announcement provider for A-share stocks."""

    def __init__(self, timeout: int = 10):
        self._timeout = timeout
        self._session = requests.Session()

    def name(self) -> str:
        return "EastMoney Notice"

    def search(self, query: str, max_results: int = 5) -> List[NewsItem]:
        code = _extract_code(query)
        if not code:
            return []

        end = datetime.now()
        start = end - timedelta(days=370)
        params = {
            "sr": "-1",
            "page_size": str(max(1, min(max_results, 10))),
            "page_index": "1",
            "ann_type": "A",
            "client_source": "web",
            "f_node": "0",
            "s_node": "0",
            "begin_time": start.strftime("%Y-%m-%d"),
            "end_time": end.strftime("%Y-%m-%d"),
            "stock_list": f"{code},{_market_code(code)}",
        }

        try:
            resp = self._session.get(
                EASTMONEY_NOTICE_URL,
                params=params,
                headers=HEADERS,
                timeout=self._timeout,
            )
            if resp.status_code != 200:
                return []
            payload = resp.json()
        except Exception:
            return []

        rows = ((payload.get("data") or {}).get("list") or [])
        items: List[NewsItem] = []
        for row in rows:
            title = str(row.get("title") or row.get("title_ch") or "").strip()
            if not title:
                continue
            columns = "、".join(
                str(item.get("column_name") or "")
                for item in row.get("columns") or []
                if item.get("column_name")
            )
            art_code = str(row.get("art_code") or "")
            items.append(
                NewsItem(
                    title=title,
                    source="东方财富公告",
                    url=_notice_url(code, art_code),
                    published_at=str(row.get("notice_date") or row.get("display_time") or "")[:10],
                    snippet=f"[公告] {columns}" if columns else "[公告] 东方财富公开公告。",
                )
            )
            if len(items) >= max_results:
                break
        return items


__all__ = ["EastMoneyNoticeProvider"]

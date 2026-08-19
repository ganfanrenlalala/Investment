# -*- coding: utf-8 -*-
"""CNINFO public announcement search provider.

This provider uses CNINFO's public disclosure search endpoint and requires no
API key. It is best-effort: endpoint or anti-abuse failures return an empty
list so report generation can continue.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Optional

import requests

from core import NewsItem
from ..base import NewsProvider


CNINFO_SEARCH_URL = "https://www.cninfo.com.cn/new/fulltextSearch/full"
CNINFO_STATIC_BASE = "https://static.cninfo.com.cn/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
    "X-Requested-With": "XMLHttpRequest",
}


def _extract_code(query: str) -> Optional[str]:
    match = re.search(r"\b([036]\d{5})\b", query or "")
    return match.group(1) if match else None


def _clean_title(value: str) -> str:
    return re.sub(r"</?em>", "", value or "").strip()


def _format_cninfo_time(value) -> str:
    try:
        timestamp = int(value) / 1000
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")


class CninfoAnnouncementProvider(NewsProvider):
    """Best-effort CNINFO announcement provider for A-share stocks."""

    def __init__(self, timeout: int = 10):
        self._timeout = timeout
        self._session = requests.Session()

    def name(self) -> str:
        return "CNINFO"

    def search(self, query: str, max_results: int = 5) -> List[NewsItem]:
        code = _extract_code(query)
        if not code:
            return []

        end = datetime.now()
        start = end - timedelta(days=370)
        params = {
            "searchkey": code,
            "sdate": start.strftime("%Y-%m-%d"),
            "edate": end.strftime("%Y-%m-%d"),
            "isfulltext": "false",
            "sortName": "pubdate",
            "sortType": "desc",
            "pageNum": "1",
        }

        try:
            resp = self._session.get(
                CNINFO_SEARCH_URL,
                params=params,
                headers=HEADERS,
                timeout=self._timeout,
            )
            if resp.status_code != 200:
                return []
            payload = resp.json()
        except Exception:
            return []

        items: List[NewsItem] = []
        for row in payload.get("announcements") or []:
            if str(row.get("secCode") or "") != code:
                continue
            title = _clean_title(row.get("announcementTitle") or row.get("shortTitle") or "")
            if not title:
                continue
            adjunct_url = str(row.get("adjunctUrl") or "").lstrip("/")
            url = CNINFO_STATIC_BASE + adjunct_url if adjunct_url else ""
            items.append(
                NewsItem(
                    title=title,
                    source="巨潮资讯",
                    url=url,
                    published_at=_format_cninfo_time(row.get("announcementTime")),
                    snippet="[公告] CNINFO 公开披露公告。",
                )
            )
            if len(items) >= max_results:
                break
        return items


__all__ = ["CninfoAnnouncementProvider"]

# -*- coding: utf-8 -*-
"""SerpAPI 新闻搜索实现

使用 SerpAPI (Google News) 搜索股票相关新闻。
API 文档: https://serpapi.com/google-news-api

配置方式：
  1. `.sightconfig.json`:
     ```json
     {"stock_sight": {"serpapi": {"api_key": "xxx"}}}
     ```
  2. 环境变量 `SERPAPI_API_KEY`
"""

import logging
from typing import List

import requests

from core import NewsItem
from ..base import NewsProvider

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


class SerpapiNewsProvider(NewsProvider):
    """SerpAPI (Google News) 新闻搜索"""

    def __init__(self, api_key: str, timeout: int = 10):
        self._api_key = api_key
        self._timeout = timeout
        self._session = requests.Session()

    def name(self) -> str:
        return "SerpAPI"

    def search(self, query: str, max_results: int = 5) -> List[NewsItem]:
        """搜索新闻

        Args:
            query: 搜索关键词
            max_results: 最大返回条数

        Returns:
            新闻条目列表，失败返回空列表
        """
        try:
            params = {
                "engine": "google_news",
                "q": query,
                "api_key": self._api_key,
                "num": min(max_results, 10),
                "gl": "cn",
                "hl": "zh-cn",
            }
            resp = self._session.get(
                SERPAPI_URL,
                params=params,
                headers=HEADERS,
                timeout=self._timeout,
            )
            if resp.status_code != 200:
                logger.warning(
                    "SerpAPI 返回异常状态码: %s %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return []

            data = resp.json()
            news_results = data.get("news_results", [])
            # 有时 SerpAPI 返回 top_stories 结构
            top_stories = data.get("top_stories", [])

            items = []
            for r in (news_results or top_stories):
                if len(items) >= max_results:
                    break
                items.append(NewsItem(
                    title=r.get("title", ""),
                    source=r.get("source", ""),
                    url=r.get("link", "") or r.get("url", ""),
                    published_at=r.get("date", ""),
                    snippet=r.get("snippet", "") or r.get("summary", ""),
                ))

            return items

        except requests.RequestException as e:
            logger.warning("SerpAPI 搜索失败: %s", e)
            return []
        except Exception as e:
            logger.warning("SerpAPI 响应解析失败: %s", e)
            return []
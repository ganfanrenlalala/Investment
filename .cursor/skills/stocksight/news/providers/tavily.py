# -*- coding: utf-8 -*-
"""Tavily 新闻搜索实现

使用 Tavily Search API 搜索股票相关新闻。
API 文档: https://docs.tavily.com/

配置方式：
  1. `.sightconfig.json`:
     ```json
     {"stock_sight": {"tavily": {"api_key": "tvly-xxx"}}}
     ```
  2. 环境变量 `TAVILY_API_KEY`
"""

import logging
from typing import List

import requests

from core import NewsItem
from ..base import NewsProvider

logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"

HEADERS = {
    "Content-Type": "application/json",
}


class TavilyNewsProvider(NewsProvider):
    """Tavily 新闻搜索"""

    def __init__(self, api_key: str, timeout: int = 10):
        self._api_key = api_key
        self._timeout = timeout
        self._session = requests.Session()

    def name(self) -> str:
        return "Tavily"

    def search(self, query: str, max_results: int = 5) -> List[NewsItem]:
        """搜索新闻

        Args:
            query: 搜索关键词
            max_results: 最大返回条数

        Returns:
            新闻条目列表，失败返回空列表
        """
        try:
            payload = {
                "api_key": self._api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": False,
                "include_raw_content": False,
            }
            resp = self._session.post(
                TAVILY_API_URL,
                json=payload,
                headers=HEADERS,
                timeout=self._timeout,
            )
            if resp.status_code != 200:
                logger.warning(
                    "Tavily API 返回异常状态码: %s %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return []

            data = resp.json()
            results = data.get("results", [])
            items = []
            for r in results:
                items.append(NewsItem(
                    title=r.get("title", ""),
                    source=r.get("source", ""),
                    url=r.get("url", ""),
                    published_at=r.get("published_date", ""),
                    snippet=r.get("content", ""),
                ))
            return items

        except requests.RequestException as e:
            logger.warning("Tavily 搜索失败: %s", e)
            return []
        except Exception as e:
            logger.warning("Tavily 响应解析失败: %s", e)
            return []

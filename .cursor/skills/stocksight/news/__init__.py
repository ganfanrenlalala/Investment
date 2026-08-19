# -*- coding: utf-8 -*-
"""News 新闻搜索模块"""

from .base import NewsProvider
from .aggregator import NewsAggregator, create_configured_news_provider, search_configured_news
from .hard_info import classify_category, classify_source, hard_info_query_types

__all__ = [
    "NewsProvider",
    "NewsAggregator",
    "create_configured_news_provider",
    "search_configured_news",
    "classify_category",
    "classify_source",
    "hard_info_query_types",
]

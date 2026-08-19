# -*- coding: utf-8 -*-
"""News and announcement aggregation helpers."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Set, Tuple

from core import NewsItem, StockData
from core.config import get_active_provider, get_api_key
from .base import NewsProvider
from .hard_info import (
    classify_category,
    classify_source,
    default_query_types,
    rank_items,
    relevance_score,
    tag_item,
)


NEWS_QUERY_TYPES = default_query_types()


class CompositeNewsProvider(NewsProvider):
    """Run multiple providers in priority order with cross-provider dedupe."""

    def __init__(self, providers: Sequence[NewsProvider]):
        self.providers = list(providers)

    def name(self) -> str:
        return " + ".join(provider.name() for provider in self.providers)

    def search(self, query: str, max_results: int = 5) -> List[NewsItem]:
        items: List[NewsItem] = []
        seen: Set[str] = set()
        for provider in self.providers:
            for item in provider.search(query, max_results=max_results):
                key = _dedupe_key(item)
                if not key or key in seen:
                    continue
                seen.add(key)
                items.append(item)
                if len(items) >= max_results:
                    return items
        return items


def create_configured_news_provider() -> Optional[NewsProvider]:
    """Create the free-first news provider chain."""
    from .providers import CninfoAnnouncementProvider, EastMoneyNoticeProvider

    providers: List[NewsProvider] = [
        CninfoAnnouncementProvider(),
        EastMoneyNoticeProvider(),
    ]

    provider_name = get_active_provider()
    if not provider_name:
        return CompositeNewsProvider(providers)

    api_key = get_api_key(provider_name)
    if provider_name == "tavily" and api_key:
        from .providers import TavilyNewsProvider

        providers.append(TavilyNewsProvider(api_key))
    elif provider_name == "serpapi" and api_key:
        from .providers import SerpapiNewsProvider

        providers.append(SerpapiNewsProvider(api_key))
    return CompositeNewsProvider(providers)


def _dedupe_key(item: NewsItem) -> str:
    if item.url:
        return item.url.strip().lower()
    return f"{item.source}|{item.title}".strip().lower()


def _tag_snippet(kind: str, item: NewsItem, stock: Optional[StockData] = None) -> NewsItem:
    category = classify_category(item, kind)
    source_label = classify_source(item)
    score = relevance_score(item, stock, category) if stock else 0
    return tag_item(item, category, source_label, score)


class NewsAggregator:
    """Search announcement, earnings, and anomaly news with dedupe."""

    def __init__(self, provider: Optional[NewsProvider] = None):
        self.provider = provider

    def search_for_stocks(
        self,
        stocks: Sequence[StockData],
        max_results: int = 5,
        query_types: Optional[Iterable[str]] = None,
    ) -> List[NewsItem]:
        if self.provider is None or not stocks or max_results <= 0:
            return []

        kinds = list(query_types or NEWS_QUERY_TYPES.keys())
        seen: Set[str] = set()
        stock_items: List[Tuple[StockData, NewsItem]] = []

        per_query_limit = max(1, min(2, max_results))
        collection_budget = max(max_results, max_results * 3)
        for stock in stocks:
            stock_budget = len(stock_items) + collection_budget
            for kind in kinds:
                if len(stock_items) >= stock_budget:
                    break
                template = NEWS_QUERY_TYPES.get(kind)
                if not template:
                    continue
                query = template.format(name=stock.name, code=stock.code)
                for item in self.provider.search(query, max_results=per_query_limit):
                    key = _dedupe_key(item)
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    stock_items.append((stock, _tag_snippet(kind, item, stock)))

        ranked: List[NewsItem] = []
        for stock in stocks:
            ranked.extend(rank_items(
                (item for item_stock, item in stock_items if item_stock.code == stock.code),
                stock,
            ))
        return ranked[:max_results]


def search_configured_news(
    stocks: Sequence[StockData],
    max_results: int = 5,
    query_types: Optional[Iterable[str]] = None,
) -> List[NewsItem]:
    """Search news using configured provider and safe degradation."""
    provider = create_configured_news_provider()
    return NewsAggregator(provider).search_for_stocks(stocks, max_results, query_types)

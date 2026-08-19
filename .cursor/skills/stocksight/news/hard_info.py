# -*- coding: utf-8 -*-
"""Hard-information helpers for A-share news aggregation.

The first version keeps providers lightweight: Tavily/SerpAPI still perform
the search, while this module controls what to ask for, how to label results,
and how to rank announcement-like sources ahead of generic market news.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from core import NewsItem, StockData


HARD_INFO_QUERY_TYPES: Dict[str, str] = {
    "公告": "{name} {code} 公告 交易所 东方财富 巨潮",
    "财报": "{name} {code} 年报 季报 财报 净利润",
    "业绩": "{name} {code} 业绩预告 业绩快报",
    "风险提示": "{name} {code} 风险提示 重大事项 停复牌",
    "持股变动": "{name} {code} 股东 增持 减持 持股变动",
}

MARKET_NEWS_QUERY_TYPES: Dict[str, str] = {
    "异动": "{name} {code} 股票 异动 涨停 跌停",
    "新闻": "{name} {code} 股票 最新消息 财经",
}

SOURCE_CONFIDENCE = {
    "交易所": ("交易所", 5),
    "上交所": ("交易所", 5),
    "深交所": ("交易所", 5),
    "北交所": ("交易所", 5),
    "巨潮": ("巨潮资讯", 5),
    "cninfo": ("巨潮资讯", 5),
    "东方财富": ("东方财富公告", 4),
    "eastmoney": ("东方财富公告", 4),
    "公司官网": ("公司官网", 4),
    "投资者关系": ("投资者关系", 3),
    "互动易": ("互动易", 3),
    "新浪财经": ("财经媒体", 2),
    "证券时报": ("财经媒体", 2),
    "中国证券报": ("财经媒体", 2),
    "上海证券报": ("财经媒体", 2),
}

CATEGORY_KEYWORDS = {
    "风险提示": ("风险提示", "退市", "监管函", "问询函", "处罚", "停牌", "复牌"),
    "业绩预告": ("业绩预告", "业绩快报", "盈利预告", "预亏", "预增", "预减"),
    "财报": ("年度报告", "半年报", "季报", "一季报", "三季报", "财报", "净利润"),
    "重大事项": ("重大事项", "资产重组", "收购", "出售资产", "对外投资", "诉讼"),
    "持股变动": ("增持", "减持", "持股变动", "股东权益变动"),
    "互动问答": ("互动易", "投资者问答", "投资者关系"),
    "公告": ("公告", "披露"),
}

HARD_INFO_CATEGORIES = {
    "公告",
    "财报",
    "业绩预告",
    "风险提示",
    "重大事项",
    "持股变动",
    "互动问答",
}


def hard_info_query_types() -> Dict[str, str]:
    """Return announcement-first query templates."""
    return dict(HARD_INFO_QUERY_TYPES)


def market_news_query_types() -> Dict[str, str]:
    """Return lower-priority generic market-news query templates."""
    return dict(MARKET_NEWS_QUERY_TYPES)


def default_query_types() -> Dict[str, str]:
    """Return the full query plan, with hard information first."""
    query_types = hard_info_query_types()
    query_types.update(market_news_query_types())
    return query_types


def classify_source(item: NewsItem) -> str:
    """Classify source credibility from source name and URL."""
    haystack = f"{item.source} {item.url}".lower()
    for keyword, (label, _) in SOURCE_CONFIDENCE.items():
        if keyword.lower() in haystack:
            return label
    return item.source or "未知来源"


def classify_category(item: NewsItem, query_kind: str = "") -> str:
    """Classify a result as announcement, filing, risk tip, or market news."""
    text = f"{query_kind} {item.title} {item.snippet} {item.source} {item.url}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            return category
    if query_kind in HARD_INFO_CATEGORIES:
        return query_kind
    return "新闻"


def is_hard_info(item: NewsItem) -> bool:
    """Return True when the item was tagged as hard information."""
    category = classify_category(item)
    return category in HARD_INFO_CATEGORIES


def source_score(item: NewsItem) -> int:
    haystack = f"{item.source} {item.url}".lower()
    for keyword, (_, score) in SOURCE_CONFIDENCE.items():
        if keyword.lower() in haystack:
            return score
    return 1


def relevance_score(item: NewsItem, stock: StockData, category: str) -> int:
    """Small transparent ranking model for report snippets."""
    text = f"{item.title} {item.snippet} {item.url}".lower()
    score = source_score(item)
    if category in HARD_INFO_CATEGORIES:
        score += 3
    if stock.code and stock.code.lower() in text:
        score += 2
    if stock.name and stock.name.lower() in text:
        score += 2
    if item.published_at:
        score += 1
    return score


def tag_item(item: NewsItem, category: str, source_label: str, score: int) -> NewsItem:
    """Attach category/source labels in a backward-compatible NewsItem."""
    prefix = f"[{category}]"
    source_prefix = f"{source_label}"
    if item.source and source_label not in item.source:
        item.source = f"{source_prefix} · {item.source}"
    elif not item.source:
        item.source = source_prefix

    confidence = "高" if score >= 8 else "中" if score >= 5 else "低"
    note = f"{prefix} 来源可信度：{confidence}。"
    if item.snippet:
        if not item.snippet.startswith(prefix):
            item.snippet = f"{prefix} {item.snippet}"
    else:
        item.snippet = note
    return item


def rank_items(items: Iterable[NewsItem], stock: StockData) -> List[NewsItem]:
    """Rank hard information ahead of generic market news."""
    return sorted(
        items,
        key=lambda item: (
            is_hard_info(item),
            source_score(item),
            bool(item.published_at),
            relevance_score(item, stock, classify_category(item)),
        ),
        reverse=True,
    )

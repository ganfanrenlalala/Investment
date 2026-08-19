# -*- coding: utf-8 -*-
"""NewsProvider 抽象层

为 StockSight 提供股票相关新闻搜索能力。
搜索引擎向后兼容：用户配置一个 provider 就搜，没配就跳过。
"""

from abc import ABC, abstractmethod
from typing import List

from core import NewsItem


class NewsProvider(ABC):
    """新闻搜索抽象基类"""

    @abstractmethod
    def name(self) -> str:
        """返回 provider 名称，如 'Tavily'"""
        ...

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[NewsItem]:
        """搜索新闻

        Args:
            query: 搜索关键词
            max_results: 最大返回条数（默认 5）

        Returns:
            新闻条目列表，搜索失败返回空列表
        """
        ...

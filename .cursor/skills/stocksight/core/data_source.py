# -*- coding: utf-8 -*-
"""数据源抽象层

定义数据源接口契约和线性 failover 降级链。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

from core.types import StockData

# FetchResult: (成功数据 {code: StockData}, 失败代码列表)
FetchResult = Tuple[Dict[str, StockData], List[str]]


class DataSourceError(Exception):
    """数据源异常基类。网络故障、解析失败等场景抛出。"""


class DataSource(ABC):
    """数据源抽象基类

    所有数据源 provider 必须实现 fetch 和 name 两个方法。
    """

    @abstractmethod
    def fetch(self, codes: List[str]) -> FetchResult:
        """批量获取股票数据

        Args:
            codes: 股票代码列表，格式如 ['600570', '002063']

        Returns:
            (成功数据字典 {code: StockData}, 失败代码列表)

        Raises:
            ValueError: 当传入空列表时
            DataSourceError: 数据源完全不可用时
        """

    @abstractmethod
    def name(self) -> str:
        """数据源标识，用于报告标注，如 '腾讯财经'"""


class DataSourceFactory:
    """线性 failover 链管理器

    按优先级依次尝试数据源，当前一个对部分股票失败时，
    自动将失败代码交给下一个数据源重试。
    """

    def __init__(self, sources: List[DataSource]):
        """初始化

        Args:
            sources: 按优先级排列的数据源列表（高优先级在前）

        Raises:
            ValueError: 数据源列表为空
        """
        if not sources:
            raise ValueError("至少需要一个数据源")
        self.sources = sources

    def fetch(self, codes: List[str]) -> Tuple[FetchResult, str]:
        """按 failover 链获取数据

        依次尝试每个数据源，只向后续数据源传递上游失败的代码。
        第一个返回数据的数据源名称作为最终来源标注。

        Args:
            codes: 股票代码列表

        Returns:
            ((成功数据, 最终失败代码), 所用数据源名称)

        Raises:
            ValueError: 股票代码列表为空
        """
        if not codes:
            raise ValueError("股票代码列表不能为空")

        remaining = list(codes)  # 待获取的代码
        all_data: Dict[str, StockData] = {}
        used_name = "无可用数据"

        for source in self.sources:
            if not remaining:
                break

            try:
                data, failed = source.fetch(remaining)
                if data and not all_data:
                    # 标记第一个实际返回数据的数据源
                    used_name = source.name()
                all_data.update(data)
                remaining = failed
            except DataSourceError:
                # 数据源自身挂了（如网络超时），跳过
                continue

        return (all_data, remaining), used_name

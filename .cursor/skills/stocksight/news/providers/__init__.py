# -*- coding: utf-8 -*-
"""News provider 实现"""

from .cninfo import CninfoAnnouncementProvider
from .eastmoney_notice import EastMoneyNoticeProvider
from .tavily import TavilyNewsProvider
from .serpapi import SerpapiNewsProvider

__all__ = [
    "CninfoAnnouncementProvider",
    "EastMoneyNoticeProvider",
    "TavilyNewsProvider",
    "SerpapiNewsProvider",
]

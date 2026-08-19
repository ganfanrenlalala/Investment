# -*- coding: utf-8 -*-
"""市场识别公共工具

统一股票代码→市场前缀的映射逻辑，供 providers 共用。
"""

from typing import Optional


def detect_market(code: str) -> str:
    """根据股票代码自动识别市场

    Args:
        code: 股票代码，如 '600570', '002063', '00700'

    Returns:
        'sh'（沪市）, 'sz'（深市）, 或 'hk'（港股）

    Notes:
        港股代码通常为 5 位数字（如 00700）
        A股沪市: 6/5/9 开头
        A股深市: 0/3 开头
    """
    normalized = code.strip()
    if normalized.isalpha():
        return "us"
    if len(normalized) == 5 and normalized.isdigit():
        return "hk"
    if normalized.startswith("6") or normalized.startswith("5") or normalized.startswith("9"):
        return "sh"
    return "sz"


def detect_tencent_prefix(code: str) -> str:
    """腾讯财经 API 市场前缀

    Args:
        code: 股票代码

    Returns:
        腾讯 API 前缀: sh, sz, hk
    """
    return detect_market(code)


def detect_sina_prefix(code: str, market_hint: str = "") -> str:
    """新浪财经 API 市场前缀

    Args:
        code: 股票代码
        market_hint: 用户提示的市场（us/hk）

    Returns:
        新浪 API 前缀: sh, sz, hk, gb_
    """
    if market_hint == "us":
        return "gb_"
    if market_hint == "hk":
        return "hk"
    if code.strip().isalpha():
        return "gb_"

    return detect_market(code)


def to_eastmoney_secid(code: str) -> Optional[str]:
    """股票代码 → 东方财富 secid（1.xxx 沪/0.xxx 深）

    Args:
        code: 股票代码，如 '600570', '002266'

    Returns:
        secid 格式字符串，如 '1.600570'，无效返回 None
    """
    code = code.strip()
    if len(code) != 6:
        return None
    if code.startswith("6") or code.startswith("5") or code.startswith("9"):
        return f"1.{code}"
    return f"0.{code}"

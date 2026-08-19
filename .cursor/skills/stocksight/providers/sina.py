# -*- coding: utf-8 -*-
"""新浪财经数据源

支持 A 股（sh/sz）、港股（hk）、美股（gb）。
数据来源: https://hq.sinajs.cn/list={prefix}{code}
响应格式: var hq_str_{prefix}{code}="field1,field2,...";
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests

from core import DataSource, DataSourceError, FetchResult, StockData
from core.market import detect_sina_prefix

logger = logging.getLogger(__name__)

SINA_API_URL = "https://hq.sinajs.cn/list="

# =============================================================================
# 市场前缀映射（用户代码 → API前缀）
# =============================================================================
MARKET_PREFIX = {
    "sh": "sh",
    "sz": "sz",
    "hk": "hk",
    "us": "gb",
}


def _detect_prefix(code: str, market_hint: str = "") -> str:
    return detect_sina_prefix(code, market_hint)


def _parse_sina_response_line(raw: str) -> Optional[List[str]]:
    """解析新浪API响应行

    Args:
        raw: 原始行，如 var hq_str_sh600570="...,...";

    Returns:
        字段列表，解析失败返回 None
    """
    # 提取引号内的内容
    m = re.search(r'"(.+)"', raw)
    if not m:
        return None
    fields = m.group(1).split(",")
    return fields if len(fields) > 2 else None


def _parse_a_fields(
    fields: List[str], code: str, timestamp: str
) -> StockData:
    """解析 A 股字段"""
    name = fields[0]
    open_price = float(fields[1]) if fields[1] else 0.0
    prev_close = float(fields[2]) if fields[2] else 0.0
    current_price = float(fields[3]) if fields[3] else 0.0
    high = float(fields[4]) if fields[4] else 0.0
    low = float(fields[5]) if fields[5] else 0.0
    volume = int(fields[8]) * 100 if fields[8] else 0  # 手→股
    amount = float(fields[9]) if fields[9] else 0.0  # 元

    # 涨跌幅: 需要计算 (current - prev_close) / prev_close * 100
    change_percent = ((current_price - prev_close) / prev_close * 100) if prev_close else 0.0

    market = "sh" if code.startswith("6") else "sz"

    return StockData(
        code=code,
        name=name,
        current_price=current_price,
        prev_close=prev_close,
        open_price=open_price,
        high=high,
        low=low,
        volume=volume,
        amount=amount / 10000,  # 元 → 万元
        volume_ratio=0.0,  # 新浪无量比
        change_percent=change_percent,
        turnover_rate=0.0,  # 新浪无换手率
        timestamp=timestamp,
        market=market,  # ✅ 这里修了！
        raw={"sina_fields": fields},
    )


def _parse_hk_fields(
    fields: List[str], code: str, timestamp: str
) -> StockData:
    """解析港股字段

    新浪港股: name_en, name_cn, open, prev_close, high, low, current,
             change_amount, change_pct, bid, ask, amount, volume, ...
    """
    name = fields[1] if len(fields) > 1 else "未知"  # fields[1]=中文名
    open_price = float(fields[2]) if len(fields) > 2 and fields[2] else 0.0
    prev_close = float(fields[3]) if len(fields) > 3 and fields[3] else 0.0
    high = float(fields[4]) if len(fields) > 4 and fields[4] else 0.0
    low = float(fields[5]) if len(fields) > 5 and fields[5] else 0.0
    current_price = float(fields[6]) if len(fields) > 6 and fields[6] else 0.0
    change_percent = float(fields[8]) if len(fields) > 8 and fields[8] else 0.0
    volume = int(float(fields[11]) if len(fields) > 11 and fields[11] else 0)  # 股
    amount = float(fields[12]) if len(fields) > 12 and fields[12] else 0.0  # 元

    return StockData(
        code=code,
        name=name,
        current_price=current_price,
        prev_close=prev_close,
        open_price=open_price,
        high=high,
        low=low,
        volume=volume,
        amount=amount / 10000,  # 元 → 万元
        volume_ratio=0.0,
        change_percent=change_percent,
        turnover_rate=0.0,
        timestamp=timestamp,
        market="hk",
        raw={"sina_fields": fields},
    )


def _parse_us_fields(
    fields: List[str], code: str, timestamp: str
) -> StockData:
    """解析美股字段"""
    name = fields[0]
    current_price = float(fields[1]) if len(fields) > 1 and fields[1] else 0.0
    change_percent = float(fields[2]) if len(fields) > 2 and fields[2] else 0.0
    open_price = float(fields[5]) if len(fields) > 5 and fields[5] else 0.0
    high = float(fields[6]) if len(fields) > 6 and fields[6] else 0.0
    low = float(fields[7]) if len(fields) > 7 and fields[7] else 0.0
    prev_close = float(fields[8]) if len(fields) > 8 and fields[8] else 0.0
    volume = int(fields[10]) if len(fields) > 10 and fields[10] else 0  # 股
    amount = float(fields[12]) if len(fields) > 12 and fields[12] else 0.0  # USD

    return StockData(
        code=code,
        name=name,
        current_price=current_price,
        prev_close=prev_close,
        open_price=open_price,
        high=high,
        low=low,
        volume=volume,
        amount=amount / 10000,  # 转万元
        volume_ratio=0.0,
        change_percent=change_percent,
        turnover_rate=0.0,
        timestamp=timestamp,
        market="us",
        raw={"sina_fields": fields},
    )


# 解析器路由
_PARSER_MAP = {
    "sh": _parse_a_fields,
    "sz": _parse_a_fields,
    "hk": _parse_hk_fields,
    "gb_": _parse_us_fields,
}


class SinaDataSource(DataSource):
    """新浪财经数据源（支持A股+港股+美股）"""

    def __init__(self, timeout: int = 10, max_retries: int = 2):
        self._session = requests.Session()
        self._timeout = timeout
        self._max_retries = max_retries

    def name(self) -> str:
        return "新浪财经"

    def fetch(
        self,
        codes: List[str],
        market_hints: Optional[Dict[str, str]] = None,
    ) -> FetchResult:
        """获取股票数据

        Args:
            codes: 股票代码列表
            market_hints: {代码: 市场} 可选提示，如 {"aapl": "us"}

        Returns:
            解析后的股票数据映射 {(code): StockData} 和失败列表
        """
        if not codes:
            return {}, []

        # 确定每个代码的市场前缀
        hints = market_hints or {}
        market_codes = []
        code_map: Dict[str, str] = {}

        for code in codes:
            hint = hints.get(code, "")
            prefix = _detect_prefix(code, hint)
            query_code = code.lower() if prefix == "gb_" else code
            key = f"{prefix}{query_code}"
            market_codes.append(key)
            code_map[key] = code

        url = SINA_API_URL + ",".join(market_codes)

        # 带重试的请求
        raw_text: Optional[str] = None
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                resp = self._session.get(
                    url,
                    timeout=self._timeout,
                    headers={"Referer": "https://finance.sina.com.cn"},
                )
                if resp.status_code != 200:
                    last_error = DataSourceError(f"HTTP {resp.status_code}")
                    continue
                resp.encoding = "gbk"
                raw_text = resp.text
                if raw_text.strip().lower().startswith("forbidden"):
                    last_error = DataSourceError("HTTP 403 Forbidden")
                    continue
                break
            except requests.RequestException as e:
                last_error = e
                logger.warning(
                    "新浪API请求失败(第%d次): %s", attempt + 1, e
                )

        if raw_text is None:
            raise DataSourceError(
                f"请求失败（已重试{self._max_retries}次）: {last_error}"
            )

        # 逐行解析
        result: Dict[str, StockData] = {}
        failed: List[str] = []
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line or not line.startswith("var "):
                continue

            # 提取 var hq_str_xxx 中的 xxx
            match = re.match(r"var hq_str_(\w+)=", line)
            if not match:
                continue

            key = match.group(1)  # 如 sh600570, hk00700, gbaapl
            orig_code = code_map.get(key)
            if orig_code is None:
                continue

            fields = _parse_sina_response_line(line)
            if fields is None:
                failed.append(orig_code)
                continue

            # 找到正确的解析器
            # 美股用 gb_ (3字符)，其他市场用前2字符
            parser_prefix = key[:3] if key.startswith("gb_") else key[:2]
            parser = _PARSER_MAP.get(parser_prefix, _parse_a_fields)
            try:
                stock = parser(fields, orig_code, ts)
                result[orig_code] = stock
            except (IndexError, ValueError) as e:
                logger.debug("新浪解析失败 %s: %s", orig_code, e)
                failed.append(orig_code)

        # 标记未在响应中出现的代码
        seen = set(result.keys()) | set(failed)
        for code in codes:
            if code not in seen:
                failed.append(code)

        return result, failed

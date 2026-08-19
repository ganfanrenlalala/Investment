# -*- coding: utf-8 -*-
"""腾讯财经数据源

支持 A 股（sh/sz）和港股（hk）。
数据来源: https://qt.gtimg.cn/q={prefix}{code}
编码: gbk
响应格式: v_{prefix}{code}="1~name~code~price~...~"
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests

from core import DataSource, DataSourceError, FetchResult, StockData
from core.market import detect_market

logger = logging.getLogger(__name__)

# 腾讯财经 API 基础 URL
TENCENT_API_URL = "https://qt.gtimg.cn/q="

# =============================================================================
# A股字段索引（0-based）
# 格式: 1~name~code~price~prev_close~open~volume~...~
# =============================================================================
_FIELD_IDX_A = {
    "name": 1,
    "current_price": 3,
    "prev_close": 4,
    "open_price": 5,
    "volume": 6,
    "change_percent": 32,
    "high": 33,
    "low": 34,
    "amount": 37,
    "volume_ratio": 38,
    "turnover_rate": 39,
    "float_shares": 72,
    "total_shares": 73,
}

# =============================================================================
# 港股字段索引（0-based）
# 港股无量比/换手率字段
# =============================================================================
_FIELD_IDX_HK = {
    "name": 1,
    "current_price": 3,
    "prev_close": 4,
    "open_price": 5,
    "volume": 6,
    "change_percent": 32,
    "high": 33,
    "low": 34,
    "amount": 37,
}

# 最小有效字段数
_MIN_FIELDS_A = 40
_MIN_FIELDS_HK = 35


def _detect_market(code: str) -> str:
    """根据股票代码自动识别市场前缀

    Args:
        code: 股票代码

    Returns:
        'sh'（沪市）, 'sz'（深市）, 或 'hk'（港股）

    Notes:
        港股代码通常为 5 位数字（如 00700）
        A股沪市: 6/5/9 开头
        A股深市: 0/3 开头
    """
    return detect_market(code)


def _parse_a_line(
    line: str, code: str, timestamp: Optional[str] = None
) -> StockData:
    """解析 A 股单行数据"""
    try:
        if '="' not in line:
            raise DataSourceError("缺少字段分隔符 '=\"'")

        data_str = line.split('="')[1].strip('\";')
        fields = data_str.split("~")

        if len(fields) < _MIN_FIELDS_A:
            raise DataSourceError(
                f"A股字段不足: 需要 ≥{_MIN_FIELDS_A}, 实际 {len(fields)}"
            )

        idx = _FIELD_IDX_A
        ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        market = _detect_market(code)

        volume = int(fields[idx["volume"]]) * 100  # 腾讯A股手转股
        raw_turnover = float(fields[idx["turnover_rate"]] or 0)
        turnover_rate, turnover_source = _derive_a_turnover_rate(
            fields, volume, raw_turnover
        )

        return StockData(
            code=code,
            name=fields[idx["name"]],
            current_price=float(fields[idx["current_price"]]),
            prev_close=float(fields[idx["prev_close"]]),
            open_price=float(fields[idx["open_price"]]),
            high=float(fields[idx["high"]]),
            low=float(fields[idx["low"]]),
            volume=volume,
            amount=float(fields[idx["amount"]] or 0),
            volume_ratio=float(fields[idx["volume_ratio"]]),
            change_percent=float(fields[idx["change_percent"]]),
            turnover_rate=turnover_rate,
            timestamp=ts,
            market=market,
            raw={
                "raw_text": line[:500],
                "raw_turnover_rate": raw_turnover,
                "turnover_rate_source": turnover_source,
            },
        )

    except (IndexError, ValueError) as e:
        raise DataSourceError(f"A股字段解析失败: {e}") from e


def _derive_a_turnover_rate(
    fields: List[str], volume: int, raw_turnover: float
) -> tuple[float, str]:
    """Derive a reliable A-share turnover rate.

    Tencent field 39 is not consistently a usable turnover rate. Prefer
    turnover computed from volume / float shares when field 72 is available.
    """
    idx = _FIELD_IDX_A
    float_shares = 0.0
    if len(fields) > idx["float_shares"]:
        float_shares = float(fields[idx["float_shares"]] or 0)

    if volume > 0 and float_shares > 0:
        derived = volume / float_shares * 100
        if 0 < derived <= 100:
            return round(derived, 2), "derived_float_shares"

    if 0 < raw_turnover <= 100:
        return raw_turnover, "provider_field"

    return raw_turnover, "provider_field_untrusted"


def _parse_hk_line(
    line: str, code: str, timestamp: Optional[str] = None
) -> StockData:
    """解析港股单行数据

    港股腾讯API字段位置与A股相同，但成交量单位为 股（A股为 手），
    且无量比/换手率字段。时间戳格式为 yyyy/MM/dd HH:mm:ss。
    """
    try:
        if '="' not in line:
            raise DataSourceError("缺少字段分隔符 '=\"'")

        data_str = line.split('="')[1].strip('\";')
        fields = data_str.split("~")

        if len(fields) < _MIN_FIELDS_HK:
            raise DataSourceError(
                f"港股字段不足: 需要 ≥{_MIN_FIELDS_HK}, 实际 {len(fields)}"
            )

        idx = _FIELD_IDX_HK
        ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return StockData(
            code=code,
            name=fields[idx["name"]],
            current_price=float(fields[idx["current_price"]]),
            prev_close=float(fields[idx["prev_close"]]),
            open_price=float(fields[idx["open_price"]]),
            high=float(fields[idx["high"]]),
            low=float(fields[idx["low"]]),
            volume=int(float(fields[idx["volume"]])),
            amount=float(fields[idx["amount"]] or 0),
            volume_ratio=0.0,
            change_percent=float(fields[idx["change_percent"]]),
            turnover_rate=0.0,
            timestamp=ts,
            market="hk",
            raw={"raw_text": line[:500]},
        )

    except (IndexError, ValueError) as e:
        raise DataSourceError(f"港股字段解析失败: {e}") from e


# =============================================================================
# 根据市场前缀选择解析器
# =============================================================================
_PARSER_MAP = {
    "sh": _parse_a_line,
    "sz": _parse_a_line,
    "hk": _parse_hk_line,
}


class TencentDataSource(DataSource):
    """腾讯财经数据源（支持A股+港股）"""

    def __init__(self, timeout: int = 10, max_retries: int = 2):
        self._session = requests.Session()
        self._timeout = timeout
        self._max_retries = max_retries

    def name(self) -> str:
        return "腾讯财经"

    def fetch(self, codes: List[str]) -> FetchResult:
        if not codes:
            return {}, []

        # 构建请求 URL: 批量查询
        market_codes = []
        code_map: Dict[str, str] = {}  # 市场前缀+code → 原始code
        code_markets: Dict[str, str] = {}  # code → 该请求中用到的前缀
        failed: List[str] = []

        for code in codes:
            market = _detect_market(code)
            if market not in _PARSER_MAP:
                failed.append(code)
                continue
            key = f"{market}{code}"
            market_codes.append(key)
            code_map[key] = code
            code_markets[code] = market

        if not market_codes:
            return {}, failed

        url = TENCENT_API_URL + ",".join(market_codes)

        # 带重试的请求
        raw_text: Optional[str] = None
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                resp = self._session.get(url, timeout=self._timeout)
                resp.encoding = "gbk"
                raw_text = resp.text
                break
            except requests.RequestException as e:
                last_error = e
                logger.warning(
                    "腾讯API请求失败(第%d次): %s", attempt + 1, e
                )

        if raw_text is None:
            raise DataSourceError(
                f"请求失败（已重试{self._max_retries}次）: {last_error}"
            )

        # 逐行解析响应
        result: Dict[str, StockData] = {}
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            eq_pos = line.find("=")
            if eq_pos == -1 or not line.startswith("v_"):
                continue

            key = line[2:eq_pos]  # 去掉 "v_", 得到 "sh600570"
            if key not in code_map:
                continue

            orig_code = code_map[key]
            market = code_markets[orig_code]
            parser = _PARSER_MAP.get(market, _parse_a_line)

            try:
                stock = parser(line, orig_code, ts)
                result[orig_code] = stock
            except DataSourceError as e:
                logger.debug("解析失败 %s: %s", orig_code, e)
                failed.append(orig_code)

        # 标记未在响应中出现的代码
        seen = set(result.keys()) | set(failed)
        for code in codes:
            if code not in seen:
                failed.append(code)

        return result, failed

# -*- coding: utf-8 -*-
"""格式化公共工具

数值格式化、Emoji 映射、表格渲染等通用函数。
对标 VISUAL_SPECS.md Sections 2-5。
"""

from collections import Counter
from html import escape
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from core.types import NewsItem, StockData


# =============================================================================
# 市场与货币符号映射（VISUAL_SPECS Section 2 补充 - 跨市场）
# =============================================================================

MARKET_CURRENCY: Dict[str, str] = {
    "sh": "RMB",
    "sz": "RMB",
    "hk": "HKD",
    "us": "USD",
}

MARKET_TAGS: Dict[str, str] = {
    "sh": "A",
    "sz": "A",
    "hk": "H",
    "us": "U",
}


# =============================================================================
# Emoji 映射表（VISUAL_SPECS Section 2）
# =============================================================================

class EmojiMap:
    """Emoji 符号映射，每个符号绑定唯一语义"""

    # 行情状态
    UP = "📈"
    DOWN = "📉"
    FLAT = "➡️"
    ANOMALY = "🔥"

    # 核心指标
    PRICE = "💰"
    TURNOVER = "🔄"  # 换手率
    VOLUME_RATIO = "⚡"  # 量比
    AMOUNT = "📊"  # 成交额/量
    CHANGE = "📐"  # 涨跌幅

    # 状态与提示
    RISK = "⚠️"
    TIP = "💡"
    DATA_SOURCE = "📡"
    TAG = "🏷️"
    CLOCK = "🕐"

    # 区块标题
    REPORT = "📰"
    LIST = "📋"
    ANALYSIS = "🔍"
    CONCLUSION = "🎯"
    NOTE = "❓"
    NEWS = "🗞️"

    # 风险等级（VISUAL_SPECS Section 5.2）
    RISK_LEVELS = {1: "🔸", 2: "🔶", 3: "🔴"}

    # 操作建议（VISUAL_SPECS Section 5.3）
    OP_BUY = "🟢"
    OP_HOLD = "🟡"
    OP_SELL = "🔴"


def change_emoji(change_percent: float) -> str:
    """根据涨跌幅返回行情 emoji"""
    if change_percent > 0.05:
        return EmojiMap.UP
    elif change_percent < -0.05:
        return EmojiMap.DOWN
    return EmojiMap.FLAT


def risk_level_symbol(level: int) -> str:
    """风险等级数字 → emoji 符号"""
    return EmojiMap.RISK_LEVELS.get(level, "🔸")


def op_symbol(signal: str) -> str:
    """操作建议 → emoji 符号
    
    Args:
        signal: "buy", "hold", "sell"
    """
    mapping = {"buy": EmojiMap.OP_BUY, "hold": EmojiMap.OP_HOLD, "sell": EmojiMap.OP_SELL}
    return mapping.get(signal, EmojiMap.OP_HOLD)


# =============================================================================
# 数值格式化（VISUAL_SPECS Section 4.4）
# =============================================================================

def format_price(value: float, market: str = "") -> str:
    """价格格式化，保留2位小数，可选带货币前缀

    Args:
        value: 价格数值
        market: 市场标记（sh/sz/hk/us），非空时带上货币前缀

    Example:
        format_price(27.93) -> "27.93"
        format_price(27.93, "sh") -> "RMB 27.93"
        format_price(456.4, "hk") -> "HKD 456.40"
    """
    precision = 4 if market == "us" else 2
    formatted = f"{value:.{precision}f}"
    if market and market in MARKET_CURRENCY:
        return f"{MARKET_CURRENCY[market]} {formatted}"
    return formatted


def market_tag(market: str) -> str:
    """市场标记，如 A/H/U"""
    return MARKET_TAGS.get(market, "")


def format_change(value: float) -> str:
    """涨跌幅格式化，带符号+百分比
    
    Example: +3.2%, -2.1%
    """
    if value > 0:
        return f"+{value:.1f}% {EmojiMap.UP}"
    elif value < 0:
        return f"{value:.1f}% {EmojiMap.DOWN}"
    return f"±{value:.1f}% {EmojiMap.FLAT}"


def format_change_plain(value: float) -> str:
    """涨跌幅纯数值（不带 emoji），用于表格内部"""
    if value > 0:
        return f"+{value:.1f}%"
    return f"{value:.1f}%"


def format_volume(volume: int, market: str = "") -> str:
    """成交量格式化，按市场选择单位

    Args:
        volume: 成交量（股）
        market: 市场标记（sh/sz/hk/us）

    Example:
        A股: format_volume(23125400, "sh") -> "231.3万手"
                     (23125400股 / 100 = 231254手 / 10000 = 23.1万手)
                    实际: 23125400/1000000 = 23.1万手
        HK:  format_volume(26449868, "hk") -> "2645.0万股"
                    26449868股 / 10000 = 2645.0万股
        US:  format_volume(54862836, "us") -> "5486.3万股"
    """
    if market in ("hk", "us"):
        return f"{volume / 10000:.1f}万股"
    # A股: 股 → 手(÷100) → 万手(÷10000) = 股 ÷ 1000000
    return f"{volume / 1000000:.1f}万手"


def format_amount(amount: float, market: str = "") -> str:
    """成交额格式化，带货币前缀

    Args:
        amount: 成交额（万元）
        market: 市场标记

    Example:
        format_amount(64652, "sh") -> "RMB 64,652万"
        format_amount(11205362, "hk") -> "HKD 11,205,362万"
    """
    formatted = f"{amount:,.0f}万"
    if market and market in MARKET_CURRENCY:
        return f"{MARKET_CURRENCY[market]} {formatted}"
    return formatted


def format_turnover(value: float) -> str:
    """换手率格式化"""
    if value <= 0 or value > 100:
        return "—"
    return f"{value:.1f}%"


def format_volume_ratio(value: float) -> str:
    """量比格式化"""
    if value <= 0:
        return "—"
    return f"{value:.2f}"


# =============================================================================
# 信号等级格式化
# =============================================================================

def fmt_signal_level(level: int) -> str:
    """风险等级 → 格式化字符串"""
    symbol = risk_level_symbol(level)
    names = {1: "关注", 2: "警告", 3: "危险"}
    name = names.get(level, "未知")
    return f"{symbol} {name}"


def signal_level_label(level: int) -> str:
    """风险等级的文字标签。"""
    names = {1: "关注", 2: "警告", 3: "危险"}
    return names.get(level, "未知")


def render_badge(text: str) -> str:
    """渲染 GitHub Markdown 兼容的短标签"""
    return f"<kbd>{escape(str(text))}</kbd>"


def render_signal_bar(level: int, width: int = 5) -> str:
    """渲染风险/异动强度条。

    风险等级只有 0-3，但视觉条保留 5 格：关注=2格，警告=3格，危险=5格。
    """
    filled_by_level = {0: 0, 1: 2, 2: 3, 3: width}
    filled = filled_by_level.get(level, min(max(level, 0), width))
    return "▰" * filled + "▱" * (width - filled)


def render_count_bar(count: int, max_count: int, width: int = 5) -> str:
    """按数量渲染分布条，适合风险等级/信号构成聚合。"""
    if count <= 0 or max_count <= 0:
        filled = 0
    else:
        filled = max(1, round(count / max_count * width))
    return "▰" * filled + "▱" * (width - filled)


def render_score_bar(score: int, width: int = 5) -> str:
    """Render a 0-100 score as a compact Unicode bar."""
    bounded = max(0, min(int(round(score)), 100))
    filled = 0 if bounded == 0 else max(1, round(bounded / 100 * width))
    return "▰" * filled + "▱" * (width - filled)


def risk_level_counts(signals: Iterable[object]) -> Dict[int, int]:
    """统计关注/警告/危险三个风险等级的信号数量。"""
    counts = Counter(getattr(sig, "level", 0) for sig in signals)
    return {level: counts.get(level, 0) for level in (1, 2, 3)}


def risk_type_counts(signals: Iterable[object]) -> List[Tuple[str, int, int]]:
    """按风险类型统计信号数量和该类型最高风险等级。"""
    grouped: Dict[str, List[int]] = {}
    for sig in signals:
        risk_type = str(getattr(sig, "risk_type", "未知信号") or "未知信号")
        grouped.setdefault(risk_type, []).append(int(getattr(sig, "level", 0) or 0))
    return sorted(
        ((risk_type, len(levels), max(levels)) for risk_type, levels in grouped.items()),
        key=lambda item: (-item[1], -item[2], item[0]),
    )


def render_risk_distribution(signals: Sequence[object]) -> str:
    """渲染 Markdown 风险等级分布条。"""
    if not signals:
        return f"{EmojiMap.OP_BUY} 暂无显著异动信号，风险分布保持平稳。"

    counts = risk_level_counts(signals)
    max_count = max(counts.values(), default=0)
    headers = [render_badge(label) for label in ("关注", "警告", "危险")]
    rows = [[
        f"{counts[1]} {render_count_bar(counts[1], max_count)}",
        f"{counts[2]} {render_count_bar(counts[2], max_count)}",
        f"{counts[3]} {render_count_bar(counts[3], max_count)}",
    ]]
    return render_table(headers, rows, col_align=["center", "center", "center"])


def render_signal_composition(signals: Sequence[object]) -> str:
    """渲染 Markdown 信号构成表。"""
    composition = risk_type_counts(signals)
    if not composition:
        return f"{EmojiMap.OP_BUY} 暂无显著异动信号。"

    max_count = max((count for _, count, _ in composition), default=0)
    rows = [
        [
            render_badge(risk_type),
            str(count),
            fmt_signal_level(level),
            render_count_bar(count, max_count),
        ]
        for risk_type, count, level in composition
    ]
    return render_table(
        ["信号类型", "数量", "最高等级", "分布"],
        rows,
        col_align=["left", "right", "left", "left"],
    )


def anomaly_breakdown_rows(signals: Sequence[object]) -> List[Tuple[str, str, int, str]]:
    """Return anomaly-strength contribution rows for Markdown/HTML.

    The values are intentionally transparent and heuristic. They explain why a
    report feels unusual without claiming that every unusual move is dangerous.
    """
    rows = [
        ("价格波动", "未触发", 0, "涨跌幅未出现显著偏离"),
        ("成交活跃", "未触发", 0, "量比/成交活跃度未出现显著放大"),
        ("筹码交换", "未触发", 0, "换手率不极端"),
        ("技术共振", "未触发", 0, "MACD/RSI/BOLL/KDJ 暂无显著共振"),
        ("事件驱动", "未检索/未触发", 0, "暂无公告或硬信息放大"),
    ]

    def _set(index: int, performance: str, score: int, note: str):
        old = rows[index]
        if score > old[2]:
            rows[index] = (old[0], performance, score, note)

    for signal in signals:
        risk_type = str(getattr(signal, "risk_type", "") or "")
        description = str(getattr(signal, "description", "") or "")
        level = int(getattr(signal, "level", 0) or 0)
        score = {0: 0, 1: 40, 2: 65, 3: 90}.get(level, min(level * 25, 100))
        summary = description or risk_type or "已触发"

        if any(keyword in risk_type for keyword in ("收益", "涨跌", "价格")):
            _set(0, fmt_signal_level(level), score, summary)
        elif any(keyword in risk_type for keyword in ("量比", "成交")):
            _set(1, fmt_signal_level(level), score, summary)
        elif "换手" in risk_type:
            _set(2, fmt_signal_level(level), score, summary)
        elif any(keyword in risk_type for keyword in ("MACD", "RSI", "BOLL", "KDJ")):
            _set(3, fmt_signal_level(level), score, summary)
        elif any(keyword in risk_type for keyword in ("公告", "风险提示", "监管", "业绩", "退市", "减持")):
            _set(4, fmt_signal_level(level), score, summary)

    return rows


def render_anomaly_breakdown(signals: Sequence[object]) -> str:
    """Render Markdown anomaly-strength breakdown."""
    rows = anomaly_breakdown_rows(signals)
    table_rows = [
        [dimension, performance, f"{score} {render_score_bar(score)}", note]
        for dimension, performance, score, note in rows
    ]
    return render_table(
        ["维度", "当前表现", "异动贡献", "说明"],
        table_rows,
        col_align=["left", "left", "left", "left"],
    )


def metric_quality_notes(stocks: Sequence[object]) -> List[str]:
    """识别不可用或明显异常的指标，供 Markdown/HTML 报告共同展示。"""
    notes: List[str] = []
    volume_ratio_codes = [
        str(getattr(stock, "code", ""))
        for stock in stocks
        if getattr(stock, "volume_ratio", 0) <= 0
    ]
    turnover_codes = [
        str(getattr(stock, "code", ""))
        for stock in stocks
        if getattr(stock, "turnover_rate", 0) <= 0 or getattr(stock, "turnover_rate", 0) > 100
    ]

    if volume_ratio_codes:
        notes.append(f"量比不可用：{', '.join(volume_ratio_codes)} 已显示为 —。")
    if turnover_codes:
        notes.append(f"换手率不可用或超出常规范围：{', '.join(turnover_codes)} 已显示为 —，不纳入风险判断。")
    return notes


def _turnover_source_text(stock: StockData) -> Tuple[str, str]:
    raw = stock.raw or {}
    source = str(raw.get("turnover_rate_source", "") or "")
    value = getattr(stock, "turnover_rate", 0)
    if value <= 0 or value > 100 or source == "provider_field_untrusted":
        return "不可用", "未采用"
    if source == "derived_float_shares":
        return "推导值", "成交量 / 流通股本"
    if source == "provider_field":
        return "可确认", "数据源字段"
    return "可确认", "数据源字段"


def data_credibility_rows(stock: StockData, technical: object = None) -> List[Tuple[str, str, str, str]]:
    """Return concise field credibility rows: label, status, source, note."""
    volume_ratio_status = "可确认" if stock.volume_ratio > 0 else "不可用"
    volume_ratio_source = "数据源字段" if stock.volume_ratio > 0 else "未采用"
    turnover_status, turnover_source = _turnover_source_text(stock)

    technical_ready = bool(
        technical
        and (
            getattr(getattr(technical, "macd", None), "dates", None)
            or getattr(getattr(technical, "rsi", None), "values", None)
        )
    )
    technical_status = "历史计算" if technical_ready else "不可用"
    technical_source = "历史行情计算" if technical_ready else "未加载历史行情"

    rows = [
        ("实时行情", "可确认" if stock.current_price > 0 else "不可用", "数据源字段", "现价/涨跌幅"),
        ("成交活跃度", "可确认" if stock.volume >= 0 and stock.amount >= 0 else "不可用", "数据源字段", "成交量/成交额"),
        ("量比", volume_ratio_status, volume_ratio_source, "不可用时不触发量比风险"),
        ("换手率", turnover_status, turnover_source, "不可用或异常时不纳入风险判断"),
        ("MACD/RSI/BOLL/KDJ", technical_status, technical_source, "仅作技术辅助判断"),
    ]
    return rows


def credibility_level(stock: StockData, technical: object = None) -> str:
    """Summarize whether the report has enough confirmed inputs."""
    statuses = [status for _, status, _, _ in data_credibility_rows(stock, technical)]
    unavailable = statuses.count("不可用")
    derived = statuses.count("推导值")
    if unavailable >= 3:
        return "偏低"
    if unavailable >= 1 or derived >= 1:
        return "中等"
    return "较高"


def render_data_credibility_section(stock: StockData, technical: object = None) -> str:
    """Render Markdown data credibility table."""
    rows = data_credibility_rows(stock, technical)
    return "\n".join([
        f"## {EmojiMap.TIP} 数据可信度",
        "",
        render_table(
            ["字段", "状态", "来源"],
            [[label, render_badge(status), source] for label, status, source, _ in rows],
            col_align=["left", "center", "left"],
        ),
        "",
        f"> 可信度：{render_badge(credibility_level(stock, technical))}。不可用或推导字段会被降权处理，避免直接放大风险结论。",
    ])


def quote_timestamp(data: object) -> str:
    """Return the quote timestamp shown in reproducibility metadata."""
    stocks = list(getattr(data, "stocks", []) or [])
    timestamps = [str(getattr(stock, "timestamp", "") or "") for stock in stocks]
    timestamps = [value for value in timestamps if value]
    if timestamps:
        return max(timestamps)
    return str(getattr(data, "timestamp", "") or "—")


def technical_cutoff_date(data: object) -> str:
    """Return the latest historical indicator date, or — when unavailable."""
    technical = getattr(data, "technical", None)
    if not technical:
        return "—"
    dates: List[str] = []
    for indicator_name in ("macd", "rsi", "boll", "kdj"):
        indicator = getattr(technical, indicator_name, None)
        dates.extend(str(value) for value in (getattr(indicator, "dates", []) or []) if value)
    return max(dates) if dates else "—"


def source_chain_summary(data: object) -> str:
    """Return compact quote/history source notes for reproducible reports."""
    notes = [str(note) for note in (getattr(data, "source_notes", []) or []) if str(note)]
    if notes:
        return "；".join(notes)
    source = str(getattr(data, "data_source", "") or "")
    return f"实时行情：{source}" if source else "—"


def snapshot_status(data: object) -> str:
    """Return whether this report was rendered from a snapshot."""
    source = str(getattr(data, "snapshot_source", "") or "")
    return f"是（{source}）" if source else "否"


def render_report_context_section(data: object) -> str:
    """Render Markdown report reproducibility metadata."""
    rows = [[
        quote_timestamp(data),
        technical_cutoff_date(data),
        source_chain_summary(data),
        snapshot_status(data),
    ]]
    return "\n".join([
        f"## {EmojiMap.NOTE} 报告口径",
        "",
        render_table(
            ["行情时间", "历史指标截止日期", "数据来源链", "使用 Snapshot"],
            rows,
            col_align=["center", "center", "left", "center"],
        ),
    ])


def final_judgment(stock: StockData, signals: Sequence[object], technical: object = None) -> Tuple[str, str, str, str]:
    """Return status label, tone class, main risk, next confirmation.

    Status is one of: 偏强 / 过热 / 转弱 / 观察, based on signal levels + trend summary.
    """
    max_level = max((int(getattr(sig, "level", 0) or 0) for sig in signals), default=0)
    top_signal = max(signals, key=lambda sig: int(getattr(sig, "level", 0) or 0), default=None)

    # Extract trend summary if available
    trend = getattr(technical, "trend", None) if technical else None
    macd_align = getattr(trend, "macd_alignment", "") or ""
    has_divergence = bool(getattr(trend, "divergence", "") or "")
    divergence_type = getattr(trend, "divergence", "") or ""
    rsi_trend = getattr(trend, "rsi_trend", "") or ""
    rsi_latest = getattr(getattr(technical, "rsi", None), "latest", None) if technical else None

    # Determine status label from signal levels + trend data
    if max_level >= 3:
        status_label = "转弱"
        tone = "danger"
        stance = "转弱 — 风险升高"
    elif has_divergence and divergence_type == "bearish":
        status_label = "过热"
        tone = "warning"
        stance = "过热 — 背离警告"
    elif rsi_latest is not None and rsi_latest >= 70:
        status_label = "过热"
        tone = "warning"
        stance = "过热 — RSI超买"
    elif rsi_trend in ("overbought_pullback",):
        status_label = "观察"
        tone = "watch"
        stance = "观察 — RSI回落中"
    elif max_level >= 2:
        status_label = "转弱"
        tone = "warning"
        stance = "转弱 — 需关注回撤"
    elif macd_align == "bullish" and max_level <= 1:
        status_label = "偏强"
        tone = "healthy"
        stance = "偏强 — 动能偏多"
    elif max_level >= 1:
        status_label = "观察"
        tone = "watch"
        stance = "观察 — 轻度异动"
    else:
        status_label = "观察"
        tone = "healthy"
        stance = "观察 — 结构平稳"

    # Main risk description
    if top_signal is None:
        main_risk = "暂无显著异动信号"
    else:
        risk_type = str(getattr(top_signal, "risk_type", "未知信号"))
        description = str(getattr(top_signal, "description", "") or "")
        main_risk = f"{risk_type}：{description}" if description else risk_type

    # Next confirmation
    if has_divergence and divergence_type == "bearish":
        confirmation = "观察价格是否跌破近期支撑，确认 MACD 是否同步转弱。若 DIF 下穿 DEA 形成死叉，进一步确认顶背离。"
    elif rsi_latest is not None and rsi_latest >= 70:
        confirmation = "确认 RSI 是否回落到中性区间（<60），并观察价格是否脱离追高区。"
    elif macd_align == "bullish" and max_level <= 1:
        confirmation = "确认上涨量能是否持续。若 MACD 柱收敛且量比回落，需关注短期调整可能。"
    elif top_signal is not None:
        risk_type = str(getattr(top_signal, "risk_type", ""))
        if "RSI" in risk_type:
            confirmation = "确认 RSI 是否回落到中性区间，并观察价格是否脱离追高区。"
        elif "MACD" in risk_type:
            confirmation = "确认 DIF/DEA 是否延续走弱，避免单日交叉造成误判。"
        elif "量比" in risk_type:
            confirmation = "确认放量是否持续，并结合价格方向判断是资金承接还是冲高回落。"
        elif "换手" in risk_type:
            confirmation = "确认换手是否伴随有效价格突破，避免高换手后的短线回撤。"
        else:
            confirmation = "确认后续成交额、振幅和收盘位置是否继续支持该信号。"
    else:
        confirmation = "继续观察成交量、价格区间和 MACD/RSI/BOLL/KDJ 是否同步转强或转弱。"

    confidence = credibility_level(stock, technical)
    return stance, tone, main_risk, f"{confirmation} 当前数据可信度：{confidence}。"


def render_metric_strip(metrics: Sequence[Tuple[str, str]]) -> str:
    """渲染顶部指标摘要条，最多 5 个指标。"""
    if not metrics:
        return ""
    if len(metrics) > 5:
        raise ValueError("指标摘要条最多支持5个指标")
    headers = [render_badge(label) for label, _ in metrics]
    values = [value for _, value in metrics]
    return render_table(headers, [values], col_align=["center"] * len(metrics))


# =============================================================================
# 表格渲染（VISUAL_SPECS Section 4）
# =============================================================================

def render_table(
    headers: List[str],
    rows: List[List[str]],
    col_align: Optional[List[str]] = None,
) -> str:
    """渲染 Markdown 表格
    
    Args:
        headers: 表头列表，如 ['股票', '现价', '涨跌幅']
        rows: 数据行，每行是字符串列表
        col_align: 列对齐方式，'left' / 'right' / 'center'
                  默认全部左对齐
        
    Returns:
        格式化的 Markdown 表格字符串
        
    Raises:
        ValueError: 列数不一致或超过5列
    """
    n_cols = len(headers)

    if n_cols > 5:
        raise ValueError(f"表格列数不能超过5（当前{n_cols}列）")

    # 检查行数据列数
    for i, row in enumerate(rows):
        if len(row) != n_cols:
            raise ValueError(
                f"第{i+1}行列数({len(row)})与表头({n_cols})不一致"
            )

    if col_align is None:
        col_align = ["left"] * n_cols

    # 构建分隔符行
    align_map = {"left": ":---", "right": "---:", "center": ":---:"}
    separators = [align_map.get(a, ":---") for a in col_align]

    # 渲染
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(separators) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


# =============================================================================
# Markdown 报告公共渲染函数
# =============================================================================

def render_highest_risk_badge(signals: Sequence[object]) -> str:
    """整份报告最高风险标签。"""
    max_level = max((getattr(sig, "level", 0) for sig in signals), default=0)
    if max_level == 0:
        return f"{EmojiMap.OP_BUY} {render_badge('平稳')}"
    return f"{fmt_signal_level(max_level)} {render_signal_bar(max_level)}"


def render_data_quality_section(stocks: Sequence[StockData]) -> str:
    """渲染数据完整性提示区块。"""
    notes = metric_quality_notes(stocks)
    if not notes:
        return ""
    lines = [f"## {EmojiMap.TIP} 数据完整性", ""]
    lines.extend(f"- {note}" for note in notes)
    return "\n".join(lines)


def render_news_details_standard(news: Sequence[NewsItem]) -> str:
    """渲染标准模式可折叠新闻区块。"""
    if not news:
        return ""
    hard_items, market_items = split_news_items(news)
    sections = []
    if hard_items:
        sections.append(("公司公告与硬信息", hard_items[:5]))
    if market_items:
        sections.append(("市场资讯与舆情", market_items[:5]))

    chunks = ["<details>", f"<summary>{EmojiMap.NEWS} 公司信息与资讯</summary>", ""]
    return "\n".join([
        *chunks,
        *[
            "\n".join([
                f"### {title}",
                "",
                render_table(
                    ["来源", "标题", "时间"],
                    [[n.source or "—", n.title or "—", n.published_at or "—"] for n in items],
                ),
                "",
            ])
            for title, items in sections
        ],
        "</details>",
    ])


def render_news_details_detailed(news: Sequence[NewsItem]) -> str:
    """渲染详细模式可折叠新闻区块。"""
    if not news:
        return ""
    hard_items, market_items = split_news_items(news)
    lines = [
        "<details>",
        f"<summary>{EmojiMap.NEWS} 公司信息与资讯</summary>",
        "",
    ]
    for section_title, items in (("公司公告与硬信息", hard_items), ("市场资讯与舆情", market_items)):
        if not items:
            continue
        lines.append(f"### {section_title}")
        lines.append("")
        for item in items[:5]:
            title = item.title or "—"
            source = item.source or "—"
            time = f"（{item.published_at}）" if item.published_at else ""
            lines.append(f"[{source}] {title}{time}")
            if item.snippet:
                lines.append(f"  {EmojiMap.NOTE} {item.snippet}")
            lines.append("")
        lines.append("")
    lines.append("</details>")
    return "\n".join(lines)


def _news_category(item: NewsItem) -> str:
    text = f"{item.snippet} {item.title} {item.source}".lower()
    for category in ("风险提示", "业绩预告", "财报", "重大事项", "持股变动", "互动问答", "公告"):
        if f"[{category}]".lower() in text or category.lower() in text:
            return category
    return "新闻"


def split_news_items(news: Sequence[NewsItem]):
    hard_categories = {"公告", "财报", "业绩预告", "风险提示", "重大事项", "持股变动", "互动问答"}
    hard_items = [item for item in news if _news_category(item) in hard_categories]
    market_items = [item for item in news if item not in hard_items]
    return hard_items, market_items

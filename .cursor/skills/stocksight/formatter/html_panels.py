# -*- coding: utf-8 -*-
"""Table, data quality, news, and metric HTML sections."""

from typing import Dict, List, Sequence, Tuple

from core import ReportData, RiskSignal, StockData
from .base import (
    change_emoji,
    credibility_level,
    data_credibility_rows,
    fmt_signal_level,
    format_change_plain,
    format_price,
    format_turnover,
    format_volume_ratio,
    market_tag,
    metric_quality_notes,
    render_signal_bar,
    split_news_items,
)
from .html_utils import _html

# =============================================================================

def _stock_table_html(stocks: Sequence[StockData], signals: Sequence[RiskSignal]) -> str:
    signal_by_code: Dict[str, List[RiskSignal]] = {}
    for sig in signals:
        signal_by_code.setdefault(sig.stock_code, []).append(sig)

    rows = []
    for stock in stocks:
        stock_signals = signal_by_code.get(stock.code, [])
        max_level = max((sig.level for sig in stock_signals), default=0)
        risk_text = "—"
        if stock_signals:
            risk_text = (
                ", ".join(_html(sig.risk_type) for sig in stock_signals)
                + f" {render_signal_bar(max_level)}"
            )
        tag = f" [{market_tag(stock.market)}]" if market_tag(stock.market) else ""
        rows.append(
            "<tr>"
            f"<td>{_html(stock.code)} {_html(stock.name)}{_html(tag)}</td>"
            f"<td>{_html(format_price(stock.current_price, stock.market))}</td>"
            f"<td>{_html(format_change_plain(stock.change_percent))} {change_emoji(stock.change_percent)}</td>"
            f"<td>{_html(format_volume_ratio(stock.volume_ratio))}</td>"
            f"<td>{risk_text}</td>"
            "</tr>"
        )

    return (
        '<section class="panel">'
        "<h2>标的列表</h2>"
        "<table>"
        "<thead><tr><th>股票</th><th>现价</th><th>涨跌幅</th><th>量比</th><th>异动信号</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</section>"
    )


# =============================================================================
# 风险提示
# =============================================================================

def _risk_notes_html(signals: Sequence[RiskSignal]) -> str:
    if not signals:
        return (
            '<section class="panel">'
            "<h2>风险提示</h2>"
            '<div class="empty-state">当前未检测到显著风险信号。</div>'
            "</section>"
        )

    cards = []
    for sig in signals:
        detail = sig.description
        if not sig.risk_type.endswith("技术信号"):
            detail = f"{detail}（偏离度 {sig.deviation_value:.1f}{sig.deviation_unit}）。"
        cards.append(
            '<article class="risk-card">'
            f"<h3>{_html(fmt_signal_level(sig.level))}</h3>"
            f"<p><kbd>{_html(sig.risk_type)}</kbd> {render_signal_bar(sig.level)}</p>"
            f"<p>{_html(detail)}</p>"
            "</article>"
        )
    return '<section class="panel"><h2>风险提示</h2><div class="risk-grid">' + "".join(cards) + "</div></section>"


# =============================================================================
# 价格区间卡片
# =============================================================================

def _price_range_html(stock: StockData) -> str:
    low = stock.low
    high = stock.high
    current = stock.current_price
    prev_close = stock.prev_close
    open_price = stock.open_price

    if high <= 0 or low <= 0 or high == low:
        return ""

    def _pct(val: float) -> float:
        return max(0.0, min(100.0, (val - low) / (high - low) * 100))

    current_pct = _pct(current)
    prev_pct = _pct(prev_close) if prev_close > 0 else -1
    open_pct = _pct(open_price) if open_price > 0 else -1

    prev_marker = ""
    if prev_pct >= 0:
        prev_marker = f'<span class="range-marker prev" style="left:{prev_pct:.1f}%"><span class="marker-dot"></span><span class="marker-label">昨收 {format_price(prev_close, stock.market)}</span></span>'

    open_marker = ""
    if open_pct >= 0:
        open_marker = f'<span class="range-marker open" style="left:{open_pct:.1f}%"><span class="marker-dot"></span><span class="marker-label">开盘 {format_price(open_price, stock.market)}</span></span>'

    current_marker = f'<span class="range-marker current" style="left:{current_pct:.1f}%"><span class="marker-dot"></span><span class="marker-label">现价 {format_price(current, stock.market)}</span></span>'

    amplitude = (high - low) / prev_close * 100 if prev_close > 0 else 0

    return (
        '<section class="panel" id="price-range">'
        "<h2>价格区间</h2>"
        '<div class="price-range-card">'
        f'<div class="range-labels"><span>{_html(format_price(low, stock.market))}</span><span>{_html(format_price(high, stock.market))}</span></div>'
        '<div class="range-track">'
        + prev_marker
        + open_marker
        + current_marker
        + "</div>"
        f'<div class="range-meta"><span>振幅 {amplitude:.1f}%</span><span>区间 {format_price(high - low, stock.market)}</span></div>'
        "</div>"
        "</section>"
    )


# =============================================================================
# 量价关系模块
# =============================================================================

def _volume_price_html(stock: StockData, signals: Sequence[RiskSignal]) -> str:
    change = stock.change_percent
    vr = stock.volume_ratio
    tr = stock.turnover_rate
    max_level = max((s.level for s in signals), default=0)

    if change > 2 and vr > 1.5:
        vp_status = "价升量增"
        vp_class = "healthy"
        vp_desc = "看多信号，资金积极介入"
    elif change < -2 and vr > 1.5:
        vp_status = "价跌量增"
        vp_class = "caution"
        vp_desc = "抛压较大，需关注支撑位"
    elif change > 2 and vr < 0.8:
        vp_status = "价升量缩"
        vp_class = "caution"
        vp_desc = "上涨动力不足，谨防假突破"
    elif change < -2 and vr < 0.8:
        vp_status = "价跌量缩"
        vp_class = "neutral"
        vp_desc = "缩量下跌，观望情绪浓厚"
    else:
        vp_status = "量价平稳"
        vp_class = "neutral"
        vp_desc = "量价配合正常，按既定策略执行"

    if max_level >= 3:
        fund_status = "高度异常"
        fund_class = "danger"
        fund_desc = "多项指标异常，需重点监控"
    elif max_level >= 2:
        fund_status = "明显异动"
        fund_class = "caution"
        fund_desc = "量比/换手率异常，需确认持续性"
    elif max_level >= 1:
        fund_status = "轻度偏离"
        fund_class = "watch"
        fund_desc = "轻度偏离，常规关注"
    else:
        fund_status = "正常"
        fund_class = "healthy"
        fund_desc = "各项指标正常"

    vr_width = min(vr / 4.0 * 100, 100) if vr > 0 else 0
    tr_width = min(tr / 25.0 * 100, 100) if tr > 0 else 0

    vr_bar_color = "#c2412d" if vr > 3 else "#d36b23" if vr > 2 else "#d79b2b" if vr > 1.5 else "#16794c"
    tr_bar_color = "#c2412d" if tr > 15 else "#d36b23" if tr > 10 else "#d79b2b" if tr > 5 else "#16794c"

    return (
        '<section class="panel" id="vol-price">'
        "<h2>量价关系</h2>"
        '<div class="vp-grid">'
        '<div class="vp-card">'
        '<div class="vp-header">'
        f'<span class="vp-badge {vp_class}">{_html(vp_status)}</span>'
        "<h3>量价配合</h3>"
        "</div>"
        f"<p>{_html(vp_desc)}</p>"
        '<div class="vp-bars">'
        f'<div class="vp-bar-row"><span>量比</span><div class="vp-bar-track"><i style="width:{vr_width:.0f}%; background:{vr_bar_color};"></i></div><strong>{format_volume_ratio(vr)}</strong></div>'
        f'<div class="vp-bar-row"><span>换手率</span><div class="vp-bar-track"><i style="width:{tr_width:.0f}%; background:{tr_bar_color};"></i></div><strong>{format_turnover(tr)}</strong></div>'
        "</div>"
        "</div>"
        '<div class="vp-card">'
        '<div class="vp-header">'
        f'<span class="vp-badge {fund_class}">{_html(fund_status)}</span>'
        "<h3>资金活跃度</h3>"
        "</div>"
        f"<p>{_html(fund_desc)}</p>"
        '<div class="vp-dimension-grid">'
        f'<div class="vp-dim"><span class="dim-label">涨跌幅</span><strong class="dim-value">{format_change_plain(change)}</strong></div>'
        f'<div class="vp-dim"><span class="dim-label">量比</span><strong class="dim-value">{format_volume_ratio(vr)}</strong></div>'
        f'<div class="vp-dim"><span class="dim-label">换手率</span><strong class="dim-value">{format_turnover(tr)}</strong></div>'
        f'<div class="vp-dim"><span class="dim-label">最高风险</span><strong class="dim-value">{fmt_signal_level(max_level) if max_level else "平稳"}</strong></div>'
        "</div>"
        "</div>"
        "</div>"
        "</section>"
    )


# =============================================================================
# 资讯时间线
# =============================================================================

def _news_html(data: ReportData) -> str:
    if not data.news:
        return ""

    def _render_items(items):
        rendered = []
        for item in items[:5]:
            title = _html(item.title or "—")
            source = _html(item.source or "—")
            time = _html(item.published_at) if item.published_at else ""
            snippet = f"<p>{_html(item.snippet)}</p>" if item.snippet else ""
            if item.url:
                title_html = f'<a href="{_html(item.url)}">{title}</a>'
            else:
                title_html = title

            rendered.append(
                '<article class="timeline-item">'
                '<div class="timeline-dot"></div>'
                '<div class="timeline-content">'
                f"<h3>{title_html}</h3>"
                f'<div class="timeline-meta"><span>{source}</span>{f" · <span>{time}</span>" if time else ""}</div>'
                f"{snippet}"
                "</div>"
                "</article>"
            )
        return "".join(rendered)

    hard_items, market_items = split_news_items(data.news)
    sections = []
    if hard_items:
        sections.append("<h3>公司公告与硬信息</h3>" + _render_items(hard_items))
    if market_items:
        sections.append("<h3>市场资讯与舆情</h3>" + _render_items(market_items))

    return (
        '<section class="panel" id="news">'
        "<h2>公司信息与资讯</h2>"
        '<div class="timeline">'
        + "".join(sections)
        + "</div>"
        "</section>"
    )


# =============================================================================
# 数据完整性面板
# =============================================================================

_METRIC_LABELS = {
    "current_price": "现价",
    "prev_close": "昨收价",
    "open_price": "开盘价",
    "high": "最高价",
    "low": "最低价",
    "volume": "成交量",
    "amount": "成交额",
    "volume_ratio": "量比",
    "turnover_rate": "换手率",
    "change_percent": "涨跌幅",
}


def _assess_metric_status(stock: StockData) -> List[Tuple[str, str, str]]:
    results: List[Tuple[str, str, str]] = []

    def _add(attr: str, is_unavailable):
        label = _METRIC_LABELS.get(attr, attr)
        val = getattr(stock, attr, None)
        if val is None:
            results.append((label, "缺失", "missing"))
        elif is_unavailable(val):
            results.append((label, "不可用", "unavailable"))
        else:
            results.append((label, "正常", "ok"))

    _add("current_price", lambda v: v <= 0)
    _add("prev_close", lambda v: v < 0)
    _add("open_price", lambda v: v < 0)
    _add("high", lambda v: v < 0)
    _add("low", lambda v: v < 0)
    _add("volume", lambda v: v < 0)
    _add("amount", lambda v: v < 0)
    _add("volume_ratio", lambda v: v < 0)
    _add("turnover_rate", lambda v: v <= 0 or v > 100)
    _add("change_percent", lambda v: False)

    return results


def _quality_html(stocks: Sequence[StockData], technical=None) -> str:
    all_statuses: List[Tuple[str, str, str]] = []
    notes = metric_quality_notes(stocks)

    for stock in stocks:
        all_statuses.extend(_assess_metric_status(stock))

    ok_count = sum(1 for _, status, _ in all_statuses if status == "正常")
    total = len(all_statuses)
    pct = ok_count / total * 100 if total > 0 else 100

    if pct >= 100 and not notes:
        integrity_class = "full"
    elif pct >= 80:
        integrity_class = "partial"
    else:
        integrity_class = "degraded"

    ring_gradient = ""
    if total > 0:
        ok_end = pct
        ring_gradient = f"background: conic-gradient(#16794c 0% {ok_end:.1f}%, #edf1f7 {ok_end:.1f}% 100%);"

    items = []
    for label, status, css_class in all_statuses:
        icon = "✓" if status == "正常" else "✗" if status == "缺失" else "—"
        items.append(
            f'<div class="qi-item {css_class}"><span class="qi-icon">{icon}</span><span class="qi-label">{_html(label)}</span><span class="qi-status">{_html(status)}</span></div>'
        )

    note_items = ""
    if notes:
        note_items = '<div class="qi-notes">' + "".join(f"<p>{_html(n)}</p>" for n in notes) + "</div>"

    credibility = ""
    if stocks:
        stock = stocks[0]
        trust_items = []
        for label, status, source, note in data_credibility_rows(stock, technical):
            css_class = {
                "可确认": "ok",
                "历史计算": "computed",
                "推导值": "derived",
                "不可用": "unavailable",
            }.get(status, "unavailable")
            trust_items.append(
                f'<div class="trust-item {css_class}">'
                f'<span>{_html(label)}</span>'
                f'<strong>{_html(status)}</strong>'
                f'<em>{_html(source)}</em>'
                f'<p>{_html(note)}</p>'
                '</div>'
            )
        credibility = (
            '<div class="trust-block">'
            '<div class="trust-head">'
            '<h3>数据可信度</h3>'
            f'<strong>{_html(credibility_level(stock, technical))}</strong>'
            '</div>'
            '<div class="trust-grid">'
            + "".join(trust_items)
            + '</div>'
            '</div>'
        )

    return (
        '<section class="panel quality-panel" id="quality">'
        "<h2>数据完整性</h2>"
        '<div class="qi-grid">'
        f'<div class="qi-ring"><div class="qi-ring-inner" style="{ring_gradient}"><span>{ok_count}/{total}</span></div><p class="muted">指标可用率</p></div>'
        '<div class="qi-items">'
        + "".join(items)
        + "</div>"
        + note_items
        + credibility
        + "</div>"
        "</section>"
    )


# =============================================================================
# CSS

# -*- coding: utf-8 -*-
"""HTML report rendering.

The HTML output is a self-contained premium report page. It intentionally uses
plain CSS only: no JavaScript, external images, or template dependencies.
"""

from core import ReportData, technical_risk_signals
from .base import (
    EmojiMap,
    change_emoji,
    fmt_signal_level,
    format_amount,
    format_change_plain,
    format_price,
    format_turnover,
    format_volume,
    format_volume_ratio,
    market_tag,
    quote_timestamp,
    snapshot_status,
    source_chain_summary,
    technical_cutoff_date,
)
from .html_sections import (
    HEADER_GRADIENTS,
    VERSION,
    _decision_card_html,
    _anomaly_breakdown_html,
    _final_judgment_html,
    _html,
    _metric_card,
    _metric_card_heat,
    _nav_html,
    _news_html,
    _price_range_html,
    _quality_html,
    _radar_html,
    _risk_distribution_html,
    _risk_gauge_html,
    _risk_notes_html,
    _signal_composition_html,
    _stock_table_html,
    _target_stock_and_signals,
    _technical_indicators_html,
    _volume_price_html,
)
from .html_utils import calculate_dual_risk_score
from .html_style import _style

def render_html_report(data: ReportData, mode: str = "detailed", macd_result=None) -> str:
    if not data.stocks:
        title = _html(data.title or "StockSight Report")
        return (
            "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            f"<title>{title}</title></head><body>无可用数据生成报告</body></html>"
        )

    selected_mode = mode if mode in {"standard", "detailed"} else "detailed"
    if selected_mode == "detailed":
        stock, visible_signals = _target_stock_and_signals(data)
        visible_stocks = [stock]
        title = f"{stock.name} ({stock.code}) 深度分析报告"
    else:
        visible_stocks = data.stocks
        visible_signals = data.signals
        title = data.title

    if selected_mode == "detailed":
        technical = data.technical
        if technical is None and macd_result is not None:
            from core import TechnicalAnalysis
            technical = TechnicalAnalysis(macd=macd_result)
        technical_signals = technical_risk_signals(technical, visible_stocks[0].code) if technical else []
        existing = {(signal.risk_type, signal.description) for signal in visible_signals}
        visible_signals = visible_signals + [
            signal
            for signal in technical_signals
            if (signal.risk_type, signal.description) not in existing
        ]
    else:
        technical = None

    top_level = max((sig.level for sig in visible_signals), default=0)
    dual_score = calculate_dual_risk_score(visible_signals)
    tone = "danger" if top_level >= 3 else ""
    first_stock = visible_stocks[0]
    subtitle = data.summary or (
        f"{first_stock.name} 今日收 {format_price(first_stock.current_price, first_stock.market)}，"
        f"涨跌幅 {format_change_plain(first_stock.change_percent)}。"
    )

    header_gradient = HEADER_GRADIENTS.get(top_level, HEADER_GRADIENTS[0])

    metric_cards = [
        _metric_card("覆盖标的", str(len(visible_stocks))),
        _metric_card("异动信号", str(len(visible_signals)), tone),
        _metric_card("最高风险", fmt_signal_level(top_level) if top_level else "平稳", tone),
        _metric_card("异动强度", f"{dual_score.anomaly_score} · {_html(dual_score.anomaly_label)}", tone),
        _metric_card("下行风险", f"{dual_score.risk_score} · {_html(dual_score.risk_label)}", tone),
        _metric_card("数据源", _html(data.data_source)),
        _metric_card("来源链", _html(source_chain_summary(data))),
        _metric_card("行情时间", _html(quote_timestamp(data))),
        _metric_card("指标截止", _html(technical_cutoff_date(data))),
        _metric_card("Snapshot", _html(snapshot_status(data))),
    ]

    price_panel = ""
    if selected_mode == "detailed":
        price_panel = (
            '<section class="panel" id="core">'
            "<h2>核心指标</h2>"
            '<div class="metric-grid">'
            + _metric_card("当前价", _html(format_price(first_stock.current_price, first_stock.market)))
            + _metric_card_heat("涨跌幅", f"{_html(format_change_plain(first_stock.change_percent))} {change_emoji(first_stock.change_percent)}", first_stock.change_percent)
            + _metric_card("量比", _html(format_volume_ratio(first_stock.volume_ratio)))
            + _metric_card("换手率", _html(format_turnover(first_stock.turnover_rate)))
            + _metric_card("成交额", _html(format_amount(first_stock.amount, first_stock.market)))
            + "</div>"
            f"<p class=\"muted\">成交量：{_html(format_volume(first_stock.volume, first_stock.market))}"
            f" · 市场标签：{_html(market_tag(first_stock.market) or '—')}</p>"
            "</section>"
        )

    price_range_section = _price_range_html(first_stock)
    volume_price_section = _volume_price_html(first_stock, visible_signals)
    judgment_panel = (
        _final_judgment_html(first_stock, visible_signals, technical)
        if selected_mode == "detailed"
        else ""
    )

    detailed_only = ""
    if selected_mode == "detailed":
        detailed_only = (
            _risk_gauge_html(top_level, visible_signals)
            + _radar_html(visible_signals, first_stock)
            + _decision_card_html(
                first_stock,
                visible_signals,
                technical,
                data.news,
                profile=data.strategy_profile,
                performance=data.strategy_performance,
                trade_plan=data.trade_plan,
                trade_lifecycle=data.trade_lifecycle,
            )
        )

    body = (
        "<!doctype html>"
        '<html lang="zh-CN">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_html(title)}</title>"
        f"<style>{_style()}</style>"
        "</head>"
        "<body>"
        "<main>"
        + _nav_html()
        + f'<header style="background: {header_gradient};">'
        f"<h1>{EmojiMap.ANALYSIS} {_html(title)}</h1>"
        f'<p class="summary">{EmojiMap.REPORT} {_html(subtitle)}</p>'
        '<div class="metric-grid">'
        + "".join(metric_cards)
        + "</div>"
        "</header>"
        + price_panel
        + judgment_panel
        + price_range_section
        + volume_price_section
        + detailed_only
        + (_technical_indicators_html(technical) if selected_mode == "detailed" else "")
        + _anomaly_breakdown_html(visible_signals)
        + _risk_distribution_html(visible_signals)
        + _signal_composition_html(visible_signals)
        + _quality_html(visible_stocks, technical)
        + _stock_table_html(visible_stocks, visible_signals)
        + _risk_notes_html(visible_signals)
        + _news_html(data)
        + f'<footer>'
        f'<div class="footer-row">'
        f'<span>{EmojiMap.DATA_SOURCE} 数据来源：{_html(data.data_source)} | {EmojiMap.CLOCK} {_html(data.timestamp)}</span>'
        f'<span class="footer-version">StockSight v{VERSION}</span>'
        f'</div>'
        f'<div class="muted">技术指标参考，不构成投资建议。</div>'
        f'</footer>'
        "</main>"
        "</body>"
        "</html>"
    )
    return body

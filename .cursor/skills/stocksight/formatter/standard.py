# -*- coding: utf-8 -*-
"""标准模式报告渲染

对标 VISUAL_SPECS.md Section 6.2（标准模式）和 Section 8（完整示例）。

报告结构（固定顺序）:
  1. H1: 📰 标题
  2. 引用摘要
  3. H2: 📋 异动股票列表（表格，5列）
  4. H2: ⚠️ 风险提示（表格，4列）
  5. H2: 🎯 操作建议（段落）
  6. 数据来源标注
"""

from typing import List

from core import RiskSignal, StockData, ReportData
from .base import (
    EmojiMap,
    change_emoji,
    fmt_signal_level,
    format_change_plain,
    format_price,
    format_volume_ratio,
    market_tag,
    metric_quality_notes,
    render_badge,
    render_data_quality_section,
    render_highest_risk_badge,
    render_metric_strip,
    render_report_context_section,
    render_news_details_standard,
    render_anomaly_breakdown,
    render_risk_distribution,
    render_signal_bar,
    render_signal_composition,
    risk_level_symbol,
    render_table,
)


def _stock_label(stock: StockData) -> str:
    """股票显示名，包含市场标签。"""
    tag_value = market_tag(stock.market)
    tag = f" [{tag_value}]" if tag_value else ""
    return f"{stock.code} {stock.name}{tag}"


def _stock_level(stock: StockData, signals: List[RiskSignal]) -> int:
    """取单只股票最高风险等级。"""
    return max((sig.level for sig in signals if sig.stock_code == stock.code), default=0)


def _highest_risk(signals: List[RiskSignal]) -> str:
    return render_highest_risk_badge(signals)


def _anomaly_flag(stock: StockData, signals: List[RiskSignal]) -> str:
    """判断股票是否在异动信号中，返回原因标识"""
    risk_types = []
    for signal in signals:
        if signal.stock_code == stock.code:
            risk_types.append(signal.risk_type)
    if risk_types:
        level = _stock_level(stock, signals)
        return f"{render_badge(' + '.join(risk_types))} {render_signal_bar(level)} {EmojiMap.ANOMALY}"
    return "—"


def _build_stock_table(stocks: List[StockData], signals: List[RiskSignal]) -> str:
    """渲染异动股票列表（5列）"""
    headers = ["股票", "现价", "涨跌幅", "量比", "异动信号"]
    rows = []
    for s in stocks:
        change_str = format_change_plain(s.change_percent)
        emoji = change_emoji(s.change_percent)
        rows.append([
            _stock_label(s),
            format_price(s.current_price, s.market),
            f"{change_str} {emoji}",
            format_volume_ratio(s.volume_ratio),
            _anomaly_flag(s, signals),
        ])
    return render_table(headers, rows, col_align=["left", "right", "right", "right", "left"])


def _render_data_quality(stocks: List[StockData]) -> str:
    return render_data_quality_section(stocks)


def _build_risk_table(signals: List[RiskSignal]) -> str:
    """渲染风险提示表格（4列）"""
    if not signals:
        return ""
    headers = ["股票", "风险类型", "偏离说明", "等级"]
    rows = []
    for sig in signals:
        level_symbol = risk_level_symbol(sig.level)
        unit = sig.deviation_unit
        dev_str = f"{sig.deviation_value:.1f}{unit}" if unit else f"{sig.deviation_value:.1f}"
        rows.append([
            sig.stock_code,
            render_badge(sig.risk_type),
            f"{sig.description}（偏离度 {dev_str}）",
            f"{level_symbol} {render_signal_bar(sig.level)}",
        ])
    return render_table(headers, rows)


def _build_suggestions(stocks: List[StockData], signals: List[RiskSignal]) -> str:
    """生成操作建议段落"""
    lines = []
    for stock in stocks:
        change = stock.change_percent
        level = 0
        for sig in signals:
            if sig.stock_code == stock.code:
                level = max(level, sig.level)

        code_name = _stock_label(stock)
        if level >= 3:
            symbol = EmojiMap.OP_SELL
            advice = "风险过高，建议关注后续走势后决策"
        elif level >= 2:
            symbol = EmojiMap.OP_HOLD
            advice = "异动特征明显，建议确认方向后再操作"
        elif change > 3:
            symbol = EmojiMap.OP_HOLD
            advice = "涨幅较大，注意回调风险"
        else:
            symbol = EmojiMap.OP_BUY
            advice = "量价正常，按既定策略执行"

        lines.append(f"{symbol} {code_name}：{advice}")

    return "\n".join(lines)


def _render_market_pulse(data: ReportData) -> str:
    """渲染标准报告顶部市场脉冲。"""
    signal_codes = {sig.stock_code for sig in data.signals}
    metrics = [
        ("覆盖标的", f"{len(data.stocks)} 只"),
        ("异动标的", f"{len(signal_codes)} 只"),
        ("最高风险", _highest_risk(data.signals)),
        ("数据源", data.data_source),
    ]
    return render_metric_strip(metrics)


def _render_news_details(data: ReportData) -> str:
    return render_news_details_standard(data.news)


def render_standard_report(data: ReportData) -> str:
    """渲染标准模式报告
    
    Args:
        data: 报告数据包
        
    Returns:
        ️ 格式化后的 Markdown 报告文本
    """
    parts = []

    # 1. H1: 标题
    parts.append(f"# {EmojiMap.REPORT} {data.title}")
    parts.append("")

    # 2. 引用摘要
    parts.append(f"> {EmojiMap.REPORT} 一句话总结：{data.summary}")
    parts.append("")

    # 3. 报告口径
    parts.append(render_report_context_section(data))
    parts.append("")

    # 4. 市场脉冲
    parts.append(f"## {EmojiMap.AMOUNT} 市场脉冲")
    parts.append("")
    parts.append(_render_market_pulse(data))
    parts.append("")

    # 5. 风险可视化
    parts.append(f"## {EmojiMap.AMOUNT} 风险可视化")
    parts.append("")
    parts.append(render_risk_distribution(data.signals))
    parts.append("")
    parts.append("### 异动强度拆解")
    parts.append("")
    parts.append(render_anomaly_breakdown(data.signals))
    parts.append("")
    parts.append("### 信号构成")
    parts.append("")
    parts.append(render_signal_composition(data.signals))
    parts.append("")

    # 6. 数据完整性
    data_quality = _render_data_quality(data.stocks)
    if data_quality:
        parts.append(data_quality)
        parts.append("")

    # 7. 异动股票列表
    parts.append(f"## {EmojiMap.LIST} 异动股票列表")
    parts.append("")

    # 先找有信号的股票，再补无信号的
    signal_codes = {s.stock_code for s in data.signals}
    anomaly_stocks = [s for s in data.stocks if s.code in signal_codes]
    normal_stocks = [s for s in data.stocks if s.code not in signal_codes]
    ordered_stocks = anomaly_stocks + normal_stocks

    # 渲染表格（传递 signals 给 _anomaly_flag）
    headers = ["股票", "现价", "涨跌幅", "量比", "异动信号"]
    rows = []
    for s in ordered_stocks:
        change_str = format_change_plain(s.change_percent)
        emoji = change_emoji(s.change_percent)
        rows.append([
            _stock_label(s),
            format_price(s.current_price, s.market),
            f"{change_str} {emoji}",
            format_volume_ratio(s.volume_ratio),
            _anomaly_flag(s, data.signals),
        ])
    parts.append(render_table(headers, rows, col_align=["left", "right", "right", "right", "left"]))
    parts.append("")

    # 7. 风险提示
    if data.signals:
        parts.append(f"## {EmojiMap.RISK} 风险提示")
        parts.append("")
        risk_table = _build_risk_table(data.signals)
        if risk_table:
            parts.append(risk_table)
            parts.append("")
    else:
        parts.append(f"## {EmojiMap.RISK} 风险提示")
        parts.append("")
        parts.append("✅ 未发现显著异动，当前市场状态平稳。")
        parts.append("")

    # 8. 操作建议
    if data.signals:
        parts.append(f"## {EmojiMap.CONCLUSION} 操作建议")
        parts.append("")
        parts.append(_build_suggestions(data.stocks, data.signals))
        parts.append("")

    # 9. 相关资讯（可选）
    if data.news:
        parts.append(_render_news_details(data))
        parts.append("")

    # 10. 数据来源标注
    parts.append(f"{EmojiMap.DATA_SOURCE} 数据来源：{data.data_source} | {EmojiMap.CLOCK} {data.timestamp}")

    return "\n".join(parts)

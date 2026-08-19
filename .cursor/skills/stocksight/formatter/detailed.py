# -*- coding: utf-8 -*-
"""详细模式报告渲染

对标 VISUAL_SPECS.md Section 6.3（详细模式）和 EXAMPLES.md Example 2。

报告结构（固定顺序，单只股票）：
  1. H1: 🔍 深度分析标题
  2. 引用摘要
  3. H2: 💰 价格概览（2列表格）
  4. H2: 📊 量价指标（段落列表）
  5. H2: 🔍 异动分析（H3 子维度）
  6. H2: ⚠️ 风险提示
  7. H2: 🎯 操作建议（含止损/目标参考）
  8. H3: 关注维度汇总表
  9. 数据来源标注
"""

from typing import List, Optional, Sequence

from core import (
    RiskSignal,
    StockData,
    ReportData,
    evaluate_strategy_action,
    evaluate_strategy_separation,
    technical_risk_signals,
)
from .base import (
    EmojiMap,
    change_emoji,
    fmt_signal_level,
    format_price,
    format_change_plain,
    format_volume,
    format_amount,
    format_volume_ratio,
    format_turnover,
    market_tag,
    metric_quality_notes,
    render_badge,
    render_data_quality_section,
    render_data_credibility_section,
    final_judgment,
    render_highest_risk_badge,
    render_metric_strip,
    render_report_context_section,
    render_news_details_detailed,
    render_anomaly_breakdown,
    render_risk_distribution,
    render_signal_bar,
    render_signal_composition,
    risk_level_symbol,
    render_table,
)


def _calc_amplitude(stock: StockData) -> float:
    """计算振幅（%）"""
    if stock.prev_close == 0:
        return 0.0
    return (stock.high - stock.low) / stock.prev_close * 100


def _calc_excess_return(stock: StockData) -> Optional[float]:
    """计算超额收益（无板块数据时返回 None）"""
    return None


def _format_signals_text(signals: List[RiskSignal], stock: StockData) -> str:
    """格式化异动分析段落"""
    parts = []
    for sig in signals:
        symbol = risk_level_symbol(sig.level)
        parts.append(f"### {sig.risk_type}（{symbol}）")
        parts.append(_signal_detail_text(sig))
        parts.append("")
    return "\n".join(parts)


def _signal_detail_text(sig: RiskSignal) -> str:
    if sig.risk_type.endswith("技术信号"):
        return sig.description
    return f"{sig.description}（偏离度 {sig.deviation_value:.1f}{sig.deviation_unit}）。"


def _risk_warnings(signals: List[RiskSignal]) -> str:
    """格式化风险提示"""
    lines = []
    for i, sig in enumerate(signals):
        symbol = risk_level_symbol(sig.level)
        lines.append(f"{symbol} {render_badge(sig.risk_type)} {render_signal_bar(sig.level)}")
        lines.append(_signal_detail_text(sig))
        lines.append("")
    return "\n".join(lines)


def _strategy_separation_markdown(stock: StockData, signals: Sequence[RiskSignal], data: ReportData) -> str:
    """Render separated mainline direction and swing timing scorecards."""
    separation = evaluate_strategy_separation(stock, signals, data.technical, data.news)
    lines = [
        "### 主线方向 / Swing 买点分离",
        "",
        f"- 组合结论：{separation.summary}",
        f"- 下一步：{separation.next_step}",
        "",
        "| 层级 | 作用 | 评分 | 状态 | 当前动作 |",
        "|:---|:---|:---:|:---:|:---|",
    ]
    for card in (separation.mainline, separation.swing):
        lines.append(
            f"| {card.label} | {card.role} | {card.score_text} | {card.status} | {card.decision.action} |"
        )
    lines.append("")
    for card in (separation.mainline, separation.swing):
        lines.append(f"**{card.label}依据：**")
        if card.hits:
            for hit in card.hits:
                lines.append(f"- {hit}")
        else:
            lines.append("- 暂无可量化依据，需补充板块、技术或新闻信息。")
        lines.append(f"- 确认条件：{card.decision.confirmation}")
        lines.append(f"- 失效条件：{card.decision.invalidation}")
        lines.append("")
    return "\n".join(lines)


def _highest_risk(signals: List[RiskSignal]) -> str:
    return render_highest_risk_badge(signals)


def _render_core_panel(stock: StockData, signals: List[RiskSignal]) -> str:
    """渲染详细报告核心看板。"""
    metrics = [
        ("当前价", format_price(stock.current_price, stock.market)),
        ("涨跌幅", f"{format_change_plain(stock.change_percent)} {change_emoji(stock.change_percent)}"),
        ("量比", format_volume_ratio(stock.volume_ratio)),
        ("换手率", format_turnover(stock.turnover_rate)),
        ("最高风险", _highest_risk(signals)),
    ]
    return render_metric_strip(metrics)


def _render_news_details(data: ReportData) -> str:
    return render_news_details_detailed(data.news)


def _render_data_quality(stocks: List[StockData]) -> str:
    return render_data_quality_section(stocks)


def _combined_signals(data: ReportData, stock: StockData, signals: List[RiskSignal]) -> List[RiskSignal]:
    technical_signals = technical_risk_signals(data.technical, stock.code) if data.technical else []
    existing = {(signal.risk_type, signal.description) for signal in signals}
    unique_technical = [
        signal
        for signal in technical_signals
        if (signal.risk_type, signal.description) not in existing
    ]
    return signals + unique_technical


def _render_technical_section(data: ReportData) -> str:
    technical = data.technical
    if technical is None:
        return "## 📈 技术指标辅助\n\n历史数据不足，暂无法计算 MACD / RSI / BOLL / KDJ。"

    macd_status = "数据不足"
    if technical.macd and technical.macd.dates:
        latest_dif = next((value for value in reversed(technical.macd.dif) if value != 0), 0.0)
        latest_dea = next((value for value in reversed(technical.macd.dea) if value != 0), 0.0)
        latest_hist = next((value for value in reversed(technical.macd.macd) if value != 0), 0.0)
        bias = "偏多" if latest_dif > latest_dea else "偏空"
        macd_status = f"{bias}（DIF {latest_dif:.4f} / DEA {latest_dea:.4f} / 柱 {latest_hist:.4f}）"

    rsi_value = technical.rsi.latest if technical.rsi else None
    if rsi_value is None:
        rsi_status = "数据不足"
    elif rsi_value >= 70:
        rsi_status = f"{rsi_value:.2f}（超买区）"
    elif rsi_value <= 30:
        rsi_status = f"{rsi_value:.2f}（超卖区）"
    else:
        rsi_status = f"{rsi_value:.2f}（中性区）"

    boll_status = "数据不足"
    if technical.boll and technical.boll.latest:
        upper, middle, lower = technical.boll.latest
        price = data.stocks[0].current_price if data.stocks else 0.0
        if price > upper:
            zone = "突破上轨"
        elif price < lower:
            zone = "跌破下轨"
        elif price >= upper - (upper - lower) * 0.08:
            zone = "贴近上轨"
        elif price <= lower + (upper - lower) * 0.08:
            zone = "贴近下轨"
        else:
            zone = "轨道内"
        boll_status = f"{zone}（上 {upper:.2f} / 中 {middle:.2f} / 下 {lower:.2f}）"

    kdj_status = "数据不足"
    if technical.kdj and technical.kdj.latest:
        k, d, j = technical.kdj.latest
        if k >= 80 and d >= 75:
            zone = "超买区"
        elif k <= 20 and d <= 25:
            zone = "超卖区"
        elif k > d:
            zone = "偏多"
        else:
            zone = "偏弱"
        kdj_status = f"{zone}（K {k:.2f} / D {d:.2f} / J {j:.2f}）"

    signal_text = "暂无明显技术指标信号"
    if technical.signals:
        signal_text = "；".join(signal.description for signal in technical.signals[-3:])

    # Build trend summary table
    trend_rows = []
    if technical.trend:
        t = technical.trend
        if t.macd_alignment_desc:
            trend_rows.append(["MACD 排列", t.macd_alignment_desc])
        if t.macd_histogram_trend:
            hist_labels = {"expanding": "扩张 📈", "contracting": "收敛 📉", "flat": "持平"}
            trend_rows.append(["MACD 柱", hist_labels.get(t.macd_histogram_trend, t.macd_histogram_trend)])
        if t.rsi_trend_desc:
            trend_rows.append(["RSI 趋势", t.rsi_trend_desc])
        if t.divergence_desc:
            icon = "🔴" if t.divergence == "bearish" else "🟢"
            trend_rows.append(["背离检测", f"{icon} {t.divergence_desc}"])

    parts = ["## 📈 技术指标辅助\n"]
    parts.append(render_table(
        ["指标", "状态"],
        [
            ["MACD", macd_status],
            [f"RSI{technical.rsi.period if technical.rsi else 14}", rsi_status],
            [f"BOLL{technical.boll.period if technical.boll else 20}", boll_status],
            [f"KDJ{technical.kdj.period if technical.kdj else 9}", kdj_status],
            ["近期信号", signal_text],
        ],
    ))
    if trend_rows:
        parts.append("\n### 趋势摘要\n")
        parts.append(render_table(
            ["维度", "判断"],
            trend_rows,
        ))
    return "\n".join(parts)


def _dimension_table(stock: StockData, signals: List[RiskSignal]) -> str:
    """渲染关注维度汇总表（3列）"""
    # 量价关系
    if stock.change_percent > 2 and stock.volume_ratio > 1.5:
        vol_price = f"{EmojiMap.OP_BUY} 健康"
        vol_price_note = "价升量增，看多信号"
    elif stock.change_percent < -2 and stock.volume_ratio > 1.5:
        vol_price = f"{EmojiMap.OP_SELL} 谨慎"
        vol_price_note = "价跌量增，需关注"
    else:
        vol_price = f"{EmojiMap.OP_HOLD} 平稳"
        vol_price_note = "量价配合正常"

    # 资金活跃度
    max_level = max((s.level for s in signals), default=0)
    if max_level >= 3:
        active = f"{risk_level_symbol(3)} 危险"
        active_note = "多项指标异常，需重点监控"
    elif max_level >= 2:
        active = f"{risk_level_symbol(2)} 关注"
        active_note = f"量比/换手率异常，需确认持续性 {render_signal_bar(2)}"
    elif max_level >= 1:
        active = f"{risk_level_symbol(1)} 留意"
        active_note = "轻度偏离，常规关注"
    else:
        active = f"{EmojiMap.OP_BUY} 正常"
        active_note = "各项指标正常"

    headers = ["维度", "状态", "说明"]
    rows = [
        ["量价关系", vol_price, vol_price_note],
        ["资金活跃度", active, active_note],
    ]
    return render_table(headers, rows)


def render_detailed_report(data: ReportData) -> str:
    """渲染详细模式报告（单只股票深度分析）
    
    取 signals 中等级最高的股票进行分析；无信号时取列表第一只。
    
    Args:
        data: 报告数据包
        
    Returns:
        格式化后的 Markdown 报告文本
    """
    # 选择分析目标
    target_stock: Optional[StockData] = None
    target_signals: List[RiskSignal] = []

    if data.signals:
        # 按等级降序取第一只
        top_signal = max(data.signals, key=lambda s: s.level)
        target_stock = next(
            (s for s in data.stocks if s.code == top_signal.stock_code), None
        )
        target_signals = [s for s in data.signals if s.stock_code == top_signal.stock_code]
    elif data.stocks:
        target_stock = data.stocks[0]

    if target_stock is None:
        return f"{EmojiMap.REPORT} 无可用数据生成深度报告"

    stock = target_stock
    signals = _combined_signals(data, stock, target_signals)
    stock_label = f"{stock.name} ({stock.code})"
    amplitude = _calc_amplitude(stock)

    parts = []

    # 1. H1: 标题
    parts.append(f"# {EmojiMap.ANALYSIS} {stock_label} 深度分析报告")
    parts.append("")

    # 2. 摘要行（一句，不重复）
    emoji = change_emoji(stock.change_percent)
    summary_text = (
        f"> {EmojiMap.REPORT} 一句话总结："
        f"{f'`[{market_tag(stock.market)}]` ' if market_tag(stock.market) else ''}"
        f"{stock.name}今日收{format_price(stock.current_price, stock.market)}，"
        f"涨跌幅{format_change_plain(stock.change_percent)} {emoji}"
    )
    if signals:
        top = signals[0]
        if top.risk_type.endswith("技术信号"):
            summary_text += f"，{top.risk_type}"
        else:
            summary_text += (
                f"，{top.risk_type}（偏离度 "
                f"{top.deviation_value:.1f}{top.deviation_unit}）"
            )
    parts.append(summary_text)
    parts.append("")

    # 3. 报告口径
    parts.append(render_report_context_section(data))
    parts.append("")

    # 4. 最终判断
    stance, _, main_risk, confirmation = final_judgment(stock, signals, data.technical)
    parts.append(f"## {EmojiMap.CONCLUSION} 最终判断")
    parts.append("")
    parts.append(
        render_table(
            ["结论", "主要风险", "下一步确认"],
            [[render_badge(stance), main_risk, confirmation]],
            col_align=["center", "left", "left"],
        )
    )
    parts.append("")

    # 5. 核心看板
    parts.append(f"## {EmojiMap.AMOUNT} 核心看板")
    parts.append("")
    parts.append(_render_core_panel(stock, signals))
    parts.append("")

    # 6. 风险可视化
    parts.append(f"## {EmojiMap.AMOUNT} 风险可视化")
    parts.append("")
    parts.append(render_risk_distribution(signals))
    parts.append("")
    parts.append("### 异动强度拆解")
    parts.append("")
    parts.append(render_anomaly_breakdown(signals))
    parts.append("")
    parts.append("### 信号构成")
    parts.append("")
    parts.append(render_signal_composition(signals))
    parts.append("")

    # 7. 数据完整性
    data_quality = _render_data_quality([stock])
    if data_quality:
        parts.append(data_quality)
        parts.append("")

    # 8. 数据可信度
    parts.append(render_data_credibility_section(stock, data.technical))
    parts.append("")

    # 9. 价格概览（2列）
    parts.append(f"## {EmojiMap.PRICE} 价格概览")
    parts.append("")
    parts.append(
        render_table(
            ["指标", "数值"],
            [
                ["当前价", format_price(stock.current_price, stock.market)],
                ["开盘价", format_price(stock.open_price, stock.market)],
                ["最高价", format_price(stock.high, stock.market)],
                ["最低价", format_price(stock.low, stock.market)],
                ["昨收价", format_price(stock.prev_close, stock.market)],
                ["振幅", f"{amplitude:.1f}%"],
            ],
            col_align=["left", "right"],
        )
    )
    parts.append("")

    # 10. 量价指标（段落列表）
    parts.append(f"## {EmojiMap.AMOUNT} 量价指标")
    parts.append("")
    emoji_c = change_emoji(stock.change_percent)
    parts.append(f"- {EmojiMap.CHANGE} 涨跌幅：{format_change_plain(stock.change_percent)} {emoji_c}")
    parts.append(f"- {EmojiMap.PRICE} 当前价：{format_price(stock.current_price, stock.market)}")
    parts.append(f"- {EmojiMap.AMOUNT} 成交量：{format_volume(stock.volume, stock.market)}")
    parts.append(f"- {EmojiMap.AMOUNT} 成交额：{format_amount(stock.amount, stock.market)}")
    parts.append(f"- {EmojiMap.VOLUME_RATIO} 量比：{format_volume_ratio(stock.volume_ratio)}")
    parts.append(f"- {EmojiMap.TURNOVER} 换手率：{format_turnover(stock.turnover_rate)}")
    parts.append("")

    # 11. 技术指标辅助
    parts.append(_render_technical_section(data))
    parts.append("")

    # 12. 异动分析
    if signals:
        parts.append(f"## {EmojiMap.ANALYSIS} 异动分析")
        parts.append("")
        for sig in signals:
            symbol = risk_level_symbol(sig.level)
            parts.append(f"### {symbol} {sig.risk_type}")
            parts.append(f"{render_badge(fmt_signal_level(sig.level))} {render_signal_bar(sig.level)}")
            parts.append("")
            parts.append(_signal_detail_text(sig))
            parts.append("")
            # 补充可能的分析
            if "量比" in sig.risk_type:
                parts.append("可能原因：")
                parts.append("- 近期有重大消息或财报预期")
                parts.append("- 主力资金异动")
                parts.append("- 板块内部轮动")
                parts.append("")

    # 13. 风险提示
    if signals:
        parts.append(f"## {EmojiMap.RISK} 风险提示")
        parts.append("")
        parts.append(_risk_warnings(signals))
    else:
        parts.append(f"## {EmojiMap.RISK} 风险提示")
        parts.append("")
        parts.append("当前未检测到显著风险信号。")
        parts.append("")

    # 14. 操作建议
    parts.append(f"## {EmojiMap.CONCLUSION} 操作建议")
    parts.append("")
    decision = evaluate_strategy_action(stock, signals, data.technical, data.news, profile=data.strategy_profile)
    mk = stock.market
    icon = EmojiMap.OP_SELL if decision.tone == "danger" else EmojiMap.OP_HOLD if decision.tone in ("warning", "watch") else EmojiMap.OP_BUY
    if decision.profile_label:
        parts.append(f"- 策略视角：{decision.profile_label}")
        parts.append("- 结论类型：策略适配度判断，不构成买卖建议")
        parts.append("")
    parts.append(f"{icon} **{decision.action}**")
    parts.append("")
    parts.append(decision.summary)
    parts.append("")
    parts.append(f"- 当前价：{format_price(stock.current_price, mk)}")
    plan = data.trade_plan
    if plan:
        parts.append(f"- 计划状态：{plan.status_label}")
        parts.append(f"- 入场方式：{plan.entry_style}")
        if plan.trigger_price is not None:
            parts.append(f"- 触发价：{format_price(plan.trigger_price, mk)}")
        if plan.entry_low is not None and plan.entry_high is not None:
            parts.append(
                f"- 计划入场区：{format_price(plan.entry_low, mk)} – "
                f"{format_price(plan.entry_high, mk)}"
            )
        if plan.stop_loss is not None:
            stop_suffix = (
                f"（距触发价 {plan.stop_distance_percent:.2f}%）"
                if plan.stop_distance_percent is not None
                else ""
            )
            parts.append(f"- 结构止损：{format_price(plan.stop_loss, mk)}{stop_suffix}")
        if plan.target_1 is not None:
            parts.append(
                f"- 第一目标：{format_price(plan.target_1, mk)}"
                + (
                    f"（{plan.reward_risk_1:.2f}R）"
                    if plan.reward_risk_1 is not None
                    else ""
                )
            )
        if plan.target_2 is not None:
            parts.append(
                f"- 第二目标：{format_price(plan.target_2, mk)}"
                + (
                    f"（{plan.reward_risk_2:.2f}R）"
                    if plan.reward_risk_2 is not None
                    else ""
                )
            )
        if plan.atr is not None:
            parts.append(
                f"- ATR：{format_price(plan.atr, mk)}"
                + (
                    f"（现价的 {plan.atr_percent:.2f}%）"
                    if plan.atr_percent is not None
                    else ""
                )
            )
        if plan.suggested_position_percent is not None:
            parts.append(
                f"- 建议仓位：{plan.suggested_position_percent:.2f}%"
                f"（单笔风险预算 {plan.risk_per_trade_percent:.2f}%，"
                f"单票上限 {plan.max_position_percent:.2f}%）"
            )
        if plan.account_size is not None:
            parts.append(f"- 账户规模：{plan.account_size:,.2f}")
            parts.append(f"- 风险预算金额：{(plan.risk_budget_amount or 0):,.2f}")
            parts.append(f"- 计划持仓金额：{(plan.position_value or 0):,.2f}")
            parts.append(f"- 计划数量：{plan.shares or 0} 股")
        if plan.basis:
            parts.append(f"- 计划依据：{'；'.join(plan.basis)}")
        parts.append(f"- 执行备注：{plan.note}")
    else:
        parts.append("- 波动率交易计划：不可用（当前报告未保存足够的历史 K 线信息）")
    lifecycle = data.trade_lifecycle
    if lifecycle:
        parts.extend(
            [
                "",
                "### 交易生命周期",
                "",
                f"- 当前状态：**{lifecycle.state_label}**",
                f"- 生命周期 ID：`{lifecycle.lifecycle_id}`",
                f"- 创建时间：{lifecycle.created_at}",
            ]
        )
        if lifecycle.triggered_at:
            parts.append(
                f"- 触发记录：{lifecycle.triggered_at}"
                + (
                    f" @ {format_price(lifecycle.triggered_price, mk)}"
                    if lifecycle.triggered_price is not None
                    else ""
                )
            )
        if lifecycle.entry_price is not None:
            parts.append(
                f"- 实际持仓：{lifecycle.entry_at} @ "
                f"{format_price(lifecycle.entry_price, mk)}"
                + (
                    f"，{lifecycle.shares} 股"
                    if lifecycle.shares is not None
                    else ""
                )
            )
        if lifecycle.exit_price is not None:
            parts.append(
                f"- 退出记录：{lifecycle.exit_at} @ "
                f"{format_price(lifecycle.exit_price, mk)}"
            )
            parts.append(f"- 退出原因：{lifecycle.exit_reason}")
        if lifecycle.pnl_percent is not None:
            result = f"{lifecycle.pnl_percent:+.2f}%"
            if lifecycle.pnl_amount is not None:
                result += f"，{lifecycle.pnl_amount:+,.2f}"
            if lifecycle.r_multiple is not None:
                result += f"，{lifecycle.r_multiple:+.2f}R"
            parts.append(f"- 交易结果：{result}")
        if lifecycle.holding_days is not None:
            parts.append(f"- 持有天数：{lifecycle.holding_days} 天")
        if lifecycle.review_note:
            grade = f"（{lifecycle.review_grade}）" if lifecycle.review_grade else ""
            parts.append(f"- 复盘{grade}：{lifecycle.review_note}")
        if lifecycle.events:
            parts.append("- 最近迁移：")
            for event in lifecycle.events[-5:]:
                transition = (
                    f"{event.from_state or 'new'} → {event.to_state}"
                )
                price_text = (
                    f" @ {format_price(event.price, mk)}"
                    if event.price is not None
                    else ""
                )
                parts.append(
                    f"  - {event.timestamp} · {transition}{price_text} · {event.reason}"
                )
    if decision.basis:
        parts.append(f"- 触发依据：{'；'.join(decision.basis)}")
    parts.append(f"- 确认条件：{decision.confirmation}")
    parts.append(f"- 失效条件：{decision.invalidation}")
    if decision.time_stop:
        parts.append(f"- 时间止损：{decision.time_stop}")
    if decision.position_note:
        parts.append(f"- 仓位提示：{decision.position_note}")
    parts.append(f"- 风险备注：{decision.risk_note}")
    if data.strategy_performance:
        performance = data.strategy_performance
        score_text = (
            f"{performance.score:.0f}/{performance.score_max:.0f}"
            if performance.score is not None and performance.score_max is not None
            else "—"
        )
        parts.extend(
            [
                "",
                "### 历史样本外表现",
                "",
                f"- 匹配动作：{performance.action}（Swing 评分 {score_text}）",
                f"- {performance.horizon_days} 日净收益为正概率：{performance.probability_positive * 100:.1f}%",
                f"- 匹配层级：{performance.match_basis or '—'}；样本：{performance.sample_size} 次；可靠性：{performance.reliability}",
                f"- 平均净收益：{performance.mean_return:+.2f}%；中位净收益：{performance.median_return:+.2f}%",
                f"- 校准说明：{performance.note}",
            ]
        )
    parts.append("")
    if data.strategy_profile == "mainline":
        parts.append(_strategy_separation_markdown(stock, signals, data))
        parts.append("")
    parts.append("> 以上参考数值基于技术指标计算，不构成投资建议。")
    parts.append("")

    # 15. 关注维度汇总表
    parts.append(f"### 关注维度")
    parts.append("")
    parts.append(_dimension_table(stock, signals))
    parts.append("")

    # 16. 相关资讯（可选，详细模式用段落格式）
    if data.news:
        parts.append(_render_news_details(data))
        parts.append("")

    # 17. 数据来源
    parts.append(f"{EmojiMap.DATA_SOURCE} 数据来源：{data.data_source} | {EmojiMap.CLOCK} {data.timestamp}")

    return "\n".join(parts)

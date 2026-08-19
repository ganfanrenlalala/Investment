# -*- coding: utf-8 -*-
"""Chart-like HTML sections for StockSight reports."""

from typing import Dict, List, Sequence, Tuple
import math

from core import RiskSignal, StockData, evaluate_strategy_action, evaluate_strategy_separation
from .base import (
    fmt_signal_level,
    final_judgment,
    format_change_plain,
    format_price,
    format_turnover,
    format_volume_ratio,
    anomaly_breakdown_rows,
    render_count_bar,
    render_score_bar,
    render_signal_bar,
    risk_level_counts,
    risk_type_counts,
    signal_level_label,
)
from .html_utils import (
    LEVEL_COLORS,
    TYPE_COLORS,
    calculate_dual_risk_score,
    _html,
    _level_pie_gradient,
    _pie_gradient,
)

# =============================================================================

def _risk_gauge_html(top_level: int, signals: Sequence[RiskSignal]) -> str:
    dual = calculate_dual_risk_score(signals)
    score = dual.risk_score
    status_text, status_color, range_text = dual.risk_label, dual.risk_color, dual.risk_range

    cx, cy = 260, 252
    arc_r = 174
    bg_r = 190
    sw = 18

    angle_deg = (score / 100) * 180 - 180
    rad = math.radians(angle_deg)

    tip_r = arc_r - 8
    tip_x = cx + tip_r * math.cos(rad)
    tip_y = cy + tip_r * math.sin(rad)

    segments = [
        (0, 25, "#11a36a", "低风险", "0-25"),
        (25, 50, "#7ac943", "较低风险", "25-50"),
        (50, 75, "#f1c40f", "中等偏高", "50-75"),
        (75, 90, "#ff7a1a", "高风险", "75-90"),
        (90, 100, "#ef3b2d", "极高风险", "90-100"),
    ]

    arcs = []
    legend = []
    for start_pct, end_pct, color, label, range_label in segments:
        start_angle = (start_pct / 100) * 180 - 180
        end_angle = (end_pct / 100) * 180 - 180
        x1 = cx + arc_r * math.cos(math.radians(start_angle))
        y1 = cy + arc_r * math.sin(math.radians(start_angle))
        x2 = cx + arc_r * math.cos(math.radians(end_angle))
        y2 = cy + arc_r * math.sin(math.radians(end_angle))
        large_arc = 1 if (end_angle - start_angle) > 180 else 0
        arcs.append(f'<path d="M {x1:.2f} {y1:.2f} A {arc_r} {arc_r} 0 {large_arc} 1 {x2:.2f} {y2:.2f}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="butt"/>')
        legend.append(f'<div class="gauge-legend-item"><span style="background:{color};"></span><strong>{_html(label)}</strong><em>{_html(range_label)}</em></div>')

    tick_marks = []
    for pct in [0, 25, 50, 75, 100]:
        a = (pct / 100) * 180 - 180
        r_a = math.radians(a)
        tx = cx + (bg_r + 6) * math.cos(r_a)
        ty = cy + (bg_r + 6) * math.sin(r_a)
        tick_marks.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" dominant-baseline="middle" class="gauge-tick">{pct}</text>')

    bg_sx = cx - bg_r
    bg_sy = cy
    bg_ex = cx + bg_r
    bg_ey = cy
    needle_start_r = 36
    needle_start_x = cx + needle_start_r * math.cos(rad)
    needle_start_y = cy + needle_start_r * math.sin(rad)

    return (
        '<section class="panel" id="risk-gauge">'
        "<h2>风险仪表盘</h2>"
        '<div class="risk-dashboard-shell">'
        '<div class="gauge-stage">'
        + f'<svg viewBox="0 0 520 360" class="new-gauge-svg" role="img" aria-label="综合风险得分 {score}">'
        + f'<path d="M {bg_sx} {bg_sy} A {bg_r} {bg_r} 0 0 1 {bg_ex} {bg_ey}" fill="none" stroke="#edf1f7" stroke-width="2"/>'
        + "".join(arcs)
        + "".join(tick_marks)
        + f'<line x1="{needle_start_x:.1f}" y1="{needle_start_y:.1f}" x2="{tip_x:.1f}" y2="{tip_y:.1f}" stroke="{status_color}" stroke-width="6" stroke-linecap="round"/>'
        + f'<circle cx="{cx}" cy="{cy}" r="8" fill="#172033" stroke="white" stroke-width="3"/>'
        + '</svg>'
        '</div>'
        + '<aside class="gauge-score-card">'
        + '<span>下行风险得分</span>'
        + f'<strong style="color:{status_color};">{score}</strong>'
        + f'<b style="color:{status_color};">{_html(status_text)}</b>'
        + f'<em>风险区间：{_html(range_text)}</em>'
        + f'<p>异动强度：{dual.anomaly_score} / 100 · {_html(dual.anomaly_label)}。上涨异动不会自动等同高风险。</p>'
        + '</aside>'
        + '<div class="gauge-legend-pro">'
        + "".join(legend)
        + '</div>'
        + "</div>"
        + "</section>"
    )


# =============================================================================
# 操作建议决策卡
# =============================================================================

def _decision_card_html(
    stock: StockData,
    signals: Sequence[RiskSignal],
    technical=None,
    news=None,
    profile: str = "neutral",
    performance=None,
    trade_plan=None,
    trade_lifecycle=None,
) -> str:
    price = stock.current_price
    mk = stock.market
    decision = evaluate_strategy_action(stock, signals, technical, news, profile=profile)
    action_class = {
        "danger": "danger",
        "warning": "caution",
        "watch": "watch",
        "healthy": "healthy",
    }.get(decision.tone, "watch")
    basis = "".join(f"<li>{_html(item)}</li>" for item in decision.basis)
    profile_note = ""
    if decision.profile_label:
        profile_note = (
            '<p class="muted">'
            f'<strong>策略视角：</strong>{_html(decision.profile_label)}<br>'
            "结论类型：策略适配度判断，不构成买卖建议。"
            "</p>"
        )
    extra_rows = ""
    if decision.time_stop:
        extra_rows += f'<div><dt>时间止损</dt><dd>{_html(decision.time_stop)}</dd></div>'
    if decision.position_note:
        extra_rows += f'<div><dt>仓位提示</dt><dd>{_html(decision.position_note)}</dd></div>'
    performance_html = ""
    if performance:
        score_text = (
            f"{performance.score:.0f}/{performance.score_max:.0f}"
            if performance.score is not None and performance.score_max is not None
            else "—"
        )
        performance_html = (
            '<div class="strategy-performance">'
            '<h3>历史样本外表现</h3>'
            '<div class="strategy-performance-grid">'
            f'<div><span>{performance.horizon_days}日上涨概率</span><strong>{performance.probability_positive * 100:.1f}%</strong></div>'
            f'<div><span>匹配样本</span><strong>{performance.sample_size}</strong></div>'
            f'<div><span>可靠性</span><strong>{_html(performance.reliability)}</strong></div>'
            f'<div><span>匹配层级</span><strong>{_html(performance.match_basis or "—")}</strong></div>'
            f'<div><span>Swing评分</span><strong>{_html(score_text)}</strong></div>'
            f'<div><span>平均净收益</span><strong>{performance.mean_return:+.2f}%</strong></div>'
            f'<div><span>中位净收益</span><strong>{performance.median_return:+.2f}%</strong></div>'
            '</div>'
            f'<p class="muted">{_html(performance.note)}</p>'
            '</div>'
        )
    plan_html = ""
    if trade_plan:
        plan_rows = []
        if trade_plan.trigger_price is not None:
            plan_rows.append(
                f'<div><dt>触发价</dt><dd>{_html(format_price(trade_plan.trigger_price, mk))}</dd></div>'
            )
        if trade_plan.entry_low is not None and trade_plan.entry_high is not None:
            plan_rows.append(
                '<div><dt>计划入场区</dt><dd>'
                f'{_html(format_price(trade_plan.entry_low, mk))} – '
                f'{_html(format_price(trade_plan.entry_high, mk))}</dd></div>'
            )
        if trade_plan.stop_loss is not None:
            stop_note = (
                f" · {trade_plan.stop_distance_percent:.2f}%"
                if trade_plan.stop_distance_percent is not None
                else ""
            )
            plan_rows.append(
                f'<div><dt>结构止损</dt><dd>{_html(format_price(trade_plan.stop_loss, mk))}{_html(stop_note)}</dd></div>'
            )
        if trade_plan.target_1 is not None:
            rr = f" · {trade_plan.reward_risk_1:.2f}R" if trade_plan.reward_risk_1 is not None else ""
            plan_rows.append(
                f'<div><dt>第一目标</dt><dd>{_html(format_price(trade_plan.target_1, mk))}{_html(rr)}</dd></div>'
            )
        if trade_plan.target_2 is not None:
            rr = f" · {trade_plan.reward_risk_2:.2f}R" if trade_plan.reward_risk_2 is not None else ""
            plan_rows.append(
                f'<div><dt>第二目标</dt><dd>{_html(format_price(trade_plan.target_2, mk))}{_html(rr)}</dd></div>'
            )
        if trade_plan.atr is not None:
            atr_note = (
                f" · {trade_plan.atr_percent:.2f}%"
                if trade_plan.atr_percent is not None
                else ""
            )
            plan_rows.append(
                f'<div><dt>ATR</dt><dd>{_html(format_price(trade_plan.atr, mk))}{_html(atr_note)}</dd></div>'
            )
        if trade_plan.suggested_position_percent is not None:
            plan_rows.append(
                f'<div><dt>建议仓位</dt><dd>{trade_plan.suggested_position_percent:.2f}%</dd></div>'
            )
        if trade_plan.account_size is not None:
            plan_rows.append(
                f'<div><dt>风险预算</dt><dd>{(trade_plan.risk_budget_amount or 0):,.2f}</dd></div>'
            )
            plan_rows.append(
                f'<div><dt>计划数量</dt><dd>{trade_plan.shares or 0} 股</dd></div>'
            )
        plan_html = (
            '<div class="trade-plan-details">'
            '<h3>价格与波动率交易计划</h3>'
            f'<p><strong>{_html(trade_plan.status_label)}</strong> · {_html(trade_plan.entry_style)}</p>'
            '<dl>'
            + "".join(plan_rows)
            + '</dl>'
            f'<p class="muted">{_html(trade_plan.note)}</p>'
            '</div>'
        )
    lifecycle_html = _trade_lifecycle_html(trade_lifecycle, mk)
    stop_price_html = (
        _html(format_price(trade_plan.stop_loss, mk))
        if trade_plan and trade_plan.stop_loss is not None
        else "—"
    )
    stop_note_html = (
        f"{trade_plan.stop_distance_percent:.2f}%"
        if trade_plan and trade_plan.stop_distance_percent is not None
        else "ATR / 结构"
    )
    target_price_html = (
        _html(format_price(trade_plan.target_1, mk))
        if trade_plan and trade_plan.target_1 is not None
        else "—"
    )
    target_note_html = (
        f"{trade_plan.reward_risk_1:.2f}R"
        if trade_plan and trade_plan.reward_risk_1 is not None
        else "风险收益比"
    )
    separation_html = (
        _strategy_separation_html(stock, signals, technical, news)
        if profile == "mainline"
        else ""
    )

    return (
        '<section class="panel" id="decision">'
        "<h2>操作建议</h2>"
        '<div class="decision-card">'
        '<div class="dc-col dc-loss">'
        '<div class="dc-arrow dc-arrow-down">&#9660;</div>'
        '<span class="dc-label">结构止损</span>'
        f'<strong class="dc-price">{stop_price_html}</strong>'
        f'<span class="dc-note">{_html(stop_note_html)}</span>'
        "</div>"
        '<div class="dc-divider"></div>'
        '<div class="dc-col dc-current">'
        f'<span class="dc-action-badge {action_class}">{_html(decision.action)}</span>'
        '<span class="dc-label">当前价</span>'
        f'<strong class="dc-price dc-price-main">{_html(format_price(price, mk))}</strong>'
        "</div>"
        '<div class="dc-divider"></div>'
        '<div class="dc-col dc-target">'
        '<div class="dc-arrow dc-arrow-up">&#9650;</div>'
        '<span class="dc-label">第一目标</span>'
        f'<strong class="dc-price">{target_price_html}</strong>'
        f'<span class="dc-note">{_html(target_note_html)}</span>'
        "</div>"
        "</div>"
        '<div class="dc-strategy-details">'
        + profile_note
        + f'<p>{_html(decision.summary)}</p>'
        + (f'<ul>{basis}</ul>' if basis else '')
        + '<dl>'
        + f'<div><dt>确认条件</dt><dd>{_html(decision.confirmation)}</dd></div>'
        + f'<div><dt>失效条件</dt><dd>{_html(decision.invalidation)}</dd></div>'
        + extra_rows
        + f'<div><dt>风险备注</dt><dd>{_html(decision.risk_note)}</dd></div>'
        + '</dl>'
        + plan_html
        + lifecycle_html
        + performance_html
        + separation_html
        + '</div>'
        + '<p class="muted dc-disclaimer">以上参考数值基于技术指标计算，不构成投资建议。</p>'
        + "</section>"
    )


def _trade_lifecycle_html(lifecycle, market: str) -> str:
    if not lifecycle:
        return ""
    states = [
        ("candidate", "候选"),
        ("triggered", "触发"),
        ("holding", "持仓"),
        ("exited", "退出"),
        ("reviewed", "复盘"),
    ]
    current_index = next(
        (index for index, item in enumerate(states) if item[0] == lifecycle.state),
        0,
    )
    steps = []
    for index, (state, label) in enumerate(states):
        status = "done" if index < current_index else "active" if index == current_index else ""
        steps.append(
            f'<div class="lifecycle-step {status}">'
            f'<span>{index + 1}</span><strong>{_html(label)}</strong>'
            '</div>'
        )
    rows = [
        f'<div><dt>当前状态</dt><dd>{_html(lifecycle.state_label)}</dd></div>',
        f'<div><dt>创建时间</dt><dd>{_html(lifecycle.created_at)}</dd></div>',
    ]
    if lifecycle.triggered_price is not None:
        rows.append(
            '<div><dt>触发记录</dt><dd>'
            f'{_html(lifecycle.triggered_at)} @ '
            f'{_html(format_price(lifecycle.triggered_price, market))}'
            '</dd></div>'
        )
    if lifecycle.entry_price is not None:
        shares = (
            f" · {lifecycle.shares} 股"
            if lifecycle.shares is not None
            else ""
        )
        rows.append(
            '<div><dt>实际持仓</dt><dd>'
            f'{_html(lifecycle.entry_at)} @ '
            f'{_html(format_price(lifecycle.entry_price, market))}'
            f'{_html(shares)}</dd></div>'
        )
    if lifecycle.exit_price is not None:
        rows.append(
            '<div><dt>退出记录</dt><dd>'
            f'{_html(lifecycle.exit_at)} @ '
            f'{_html(format_price(lifecycle.exit_price, market))}'
            '</dd></div>'
        )
        rows.append(
            f'<div><dt>退出原因</dt><dd>{_html(lifecycle.exit_reason)}</dd></div>'
        )
    if lifecycle.pnl_percent is not None:
        result = f"{lifecycle.pnl_percent:+.2f}%"
        if lifecycle.pnl_amount is not None:
            result += f" · {lifecycle.pnl_amount:+,.2f}"
        if lifecycle.r_multiple is not None:
            result += f" · {lifecycle.r_multiple:+.2f}R"
        rows.append(
            f'<div><dt>交易结果</dt><dd>{_html(result)}</dd></div>'
        )
    if lifecycle.holding_days is not None:
        rows.append(
            f'<div><dt>持有天数</dt><dd>{lifecycle.holding_days} 天</dd></div>'
        )
    if lifecycle.review_note:
        grade = f"{lifecycle.review_grade} · " if lifecycle.review_grade else ""
        rows.append(
            f'<div><dt>复盘</dt><dd>{_html(grade + lifecycle.review_note)}</dd></div>'
        )
    events = "".join(
        '<li>'
        f'<span>{_html(event.timestamp)}</span>'
        f'<strong>{_html((event.from_state or "new") + " → " + event.to_state)}</strong>'
        f'<em>{_html(event.reason)}</em>'
        '</li>'
        for event in lifecycle.events[-5:]
    )
    return (
        '<div class="trade-lifecycle-details">'
        '<h3>交易生命周期</h3>'
        f'<div class="lifecycle-steps">{"".join(steps)}</div>'
        f'<dl>{"".join(rows)}</dl>'
        f'<ul class="lifecycle-events">{events}</ul>'
        '</div>'
    )


def _strategy_separation_html(stock: StockData, signals: Sequence[RiskSignal], technical=None, news=None) -> str:
    separation = evaluate_strategy_separation(stock, signals, technical, news)

    def card_html(card) -> str:
        hits = "".join(f"<li>{_html(item)}</li>" for item in card.hits[:4])
        if not hits:
            hits = "<li>暂无可量化依据，需补充板块、技术或新闻信息。</li>"
        return (
            '<div class="strategy-split-card">'
            f'<h4>{_html(card.label)}</h4>'
            f'<p class="muted">{_html(card.role)}</p>'
            '<div class="strategy-split-meta">'
            f'<span>评分 <strong>{_html(card.score_text)}</strong></span>'
            f'<span>状态 <strong>{_html(card.status)}</strong></span>'
            f'<span>动作 <strong>{_html(card.decision.action)}</strong></span>'
            '</div>'
            f'<ul>{hits}</ul>'
            '</div>'
        )

    return (
        '<div class="strategy-split">'
        '<h3>主线方向 / Swing 买点分离</h3>'
        f'<p><strong>组合结论：</strong>{_html(separation.summary)}</p>'
        f'<p><strong>下一步：</strong>{_html(separation.next_step)}</p>'
        '<div class="strategy-split-grid">'
        + card_html(separation.mainline)
        + card_html(separation.swing)
        + '</div>'
        '</div>'
    )


# =============================================================================
# 最终判断
# =============================================================================

def _final_judgment_html(stock: StockData, signals: Sequence[RiskSignal], technical=None) -> str:
    stance, tone, main_risk, confirmation = final_judgment(stock, signals, technical)

    # Map tone to visual theme
    theme_colors = {
        "danger": ("#fef2f2", "#c2412d", "#fecaca"),
        "warning": ("#fff7ed", "#d97706", "#fed7aa"),
        "watch": ("#f0f9ff", "#2563eb", "#bae6fd"),
        "healthy": ("#f0fdf4", "#16794c", "#bbf7d0"),
    }
    bg, accent, _ = theme_colors.get(tone, theme_colors["watch"])

    # Build signal summary
    risk_types = list(dict.fromkeys(
        str(getattr(s, "risk_type", "")) for s in signals if str(getattr(s, "risk_type", ""))
    ))[:3]
    if not main_risk and risk_types:
        main_risk = "、".join(risk_types)

    # Build trend indicators line. Keep this area concise, but never hard-cut
    # indicator text because half tokens like "D" or "M" look like data loss.
    trend_items = []
    if technical and getattr(technical, "trend", None):
        t = technical.trend
        if t.macd_alignment:
            trend_items.append(f"MACD {t.macd_alignment_desc}")
        if t.rsi_trend:
            trend_items.append(t.rsi_trend_desc)
        if t.divergence:
            icon = "⚠" if t.divergence == "bearish" else "✦"
            label = "顶背离" if t.divergence == "bearish" else "底背离"
            if "MACD DIF" in t.divergence_desc:
                trend_items.append(f"{icon} {label}：MACD DIF 未同步确认")
            else:
                trend_items.append(f"{icon} {label}")
    trend_line = " · ".join(trend_items) if trend_items else ""

    return (
        f'<section class="judgment-hero" id="judgment" style="background:{bg}; border-left:4px solid {accent};">'
        '<div class="judgment-hero-inner">'
        # Status badge
        f'<div class="judgment-status-badge {tone}">'
        f'<strong>{_html(stance)}</strong>'
        '</div>'
        # Risk & trend summary
        '<div class="judgment-hero-body">'
        f'<p class="judgment-risk-line">{_html(main_risk)}</p>'
        + (f'<p class="judgment-trend-line">{_html(trend_line)}</p>' if trend_line else '')
        + '</div>'
        # Next action
        '<div class="judgment-hero-action">'
        '<span>下一步确认</span>'
        f'<p>{_html(confirmation)}</p>'
        '</div>'
        '</div>'
        '</section>'
    )


# =============================================================================
# 信号雷达图
# =============================================================================

def _radar_html(signals: Sequence[RiskSignal], stock: StockData) -> str:
    type_levels: Dict[str, int] = {}
    for sig in signals:
        type_levels[sig.risk_type] = max(type_levels.get(sig.risk_type, 0), sig.level)

    dim_config = [
        ("量比信号", "volume_ratio", stock.volume_ratio, "vr"),
        ("换手信号", "turnover", stock.turnover_rate, "tr"),
        ("涨跌幅信号", "change", stock.change_percent, "ch"),
        ("成交额信号", "amount", stock.amount / 10000000 if stock.amount else 0, "am"),
        ("振幅信号", "amplitude", (stock.high - stock.low) / (stock.prev_close or 1) * 100 if (stock.high and stock.low and stock.prev_close) else 0, "ampl"),
        ("波动信号", "volatility", abs(stock.change_percent), "vol"),
    ]

    cx, cy, r_max = 230, 230, 138

    def hex_points(radius: float) -> str:
        pts = []
        for i in range(6):
            angle = -90 + i * 60
            rad = math.radians(angle)
            x = cx + radius * math.cos(rad)
            y = cy + radius * math.sin(rad)
            pts.append(f"{x:.2f},{y:.2f}")
        return " ".join(pts)

    grid = []
    for r, label in [(0.25, "25"), (0.5, "50"), (0.75, "75"), (1.0, "100")]:
        grid.append(f'<polygon points="{hex_points(r_max * r)}" fill="none" stroke="#e5eaf2" stroke-width="1"/>')
        grid.append(f'<text x="{cx}" y="{cy - r_max * r - 5:.1f}" text-anchor="middle" class="radar-scale">{label}</text>')

    axes = []
    labels = []
    for i in range(6):
        angle = -90 + i * 60
        rad = math.radians(angle)
        x = cx + r_max * math.cos(rad)
        y = cy + r_max * math.sin(rad)
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.2f}" y2="{y:.2f}" stroke="#cbd5e1" stroke-width="1"/>')

        label_offset = 54
        label_x = cx + (r_max + label_offset) * math.cos(rad)
        label_y = cy + (r_max + label_offset) * math.sin(rad)

        anchor = "middle"
        if i == 1 or i == 4 or i == 5:
            if i == 1:
                anchor = "start"
                label_x += 4
            elif i == 4:
                anchor = "end"
                label_x -= 4
            elif i == 5:
                anchor = "end"
                label_x -= 4

        labels.append(f'<text x="{label_x:.2f}" y="{label_y:.2f}" text-anchor="{anchor}" dominant-baseline="middle" class="radar-axis-label">{_html(dim_config[i][0])}</text>')

    values = []
    for i, (name, key, val, short) in enumerate(dim_config):
        level = 0
        if key == "volume_ratio":
            if val > 3: level = 3
            elif val > 2: level = 2
            elif val > 1.5: level = 1
        elif key == "turnover":
            if val > 15: level = 3
            elif val > 10: level = 2
            elif val > 5: level = 1
        elif key == "change":
            if abs(val) > 9.8: level = 3
            elif abs(val) > 7: level = 2
            elif abs(val) > 5: level = 1
        elif key in ["amplitude", "volatility"]:
            if val > 8: level = 3
            elif val > 5: level = 2
            elif val > 3: level = 1
        elif key == "amount":
            pass
        values.append(level)

    data_points = []
    baseline_points = []
    for i, (name, key, val, short) in enumerate(dim_config):
        angle = -90 + i * 60
        rad = math.radians(angle)
        r = r_max * (0.35 if values[i] == 1 else 0.62 if values[i] == 2 else 0.88 if values[i] == 3 else 0.18)
        x = cx + r * math.cos(rad)
        y = cy + r * math.sin(rad)
        data_points.append(f"{x:.2f},{y:.2f}")
        br = r_max * 0.55
        bx = cx + br * math.cos(rad)
        by = cy + br * math.sin(rad)
        baseline_points.append(f"{bx:.2f},{by:.2f}")

    signal_rows = []
    for i, (name, key, val, short) in enumerate(dim_config):
        level = values[i]
        if level >= 3:
            signal = "偏多" if key in {"volume_ratio", "turnover", "amount"} else "偏空" if stock.change_percent < 0 else "偏多"
            pill = "bull" if signal == "偏多" else "bear"
        elif level >= 2:
            signal = "偏高"
            pill = "watch"
        elif level >= 1:
            signal = "关注"
            pill = "watch"
        else:
            signal = "中性"
            pill = "neutral"
        signal_rows.append(
            '<div class="signal-row">'
            f'<span class="signal-icon signal-{i}">{i + 1}</span>'
            f'<strong>{_html(name)}</strong>'
            f'<em>{_html(_radar_signal_description(key, val, level))}</em>'
            f'<b class="{pill}">{_html(signal)}</b>'
            '</div>'
        )

    return (
        '<section class="panel" id="radar">'
        "<h2>信号雷达</h2>"
        '<div class="radar-dashboard">'
        '<div class="radar-stage">'
        '<svg viewBox="0 0 460 460" class="new-radar-svg" role="img" aria-label="六维信号雷达">'
        + "".join(grid)
        + "".join(axes)
        + f'<polygon points="{" ".join(baseline_points)}" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 4"/>'
        + f'<polygon points="{" ".join(data_points)}" fill="rgba(36, 84, 214, 0.14)" stroke="#2563eb" stroke-width="2.5"/>'
        + "".join(_radar_dots(data_points))
        + "".join(labels)
        + '</svg>'
        '</div>'
        '<div class="signal-list">'
        + "".join(signal_rows)
        + '</div>'
        '</div>'
        "</section>"
    )


def _radar_dots(points: Sequence[str]) -> List[str]:
    dots = []
    for point in points:
        x, y = point.split(",")
        dots.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#2563eb" stroke="white" stroke-width="2"/>')
    return dots


def _radar_signal_description(key: str, value: float, level: int) -> str:
    if key == "volume_ratio":
        return f"量比 {value:.2f}，{'高于活跃阈值' if level else '活跃度中性'}"
    if key == "turnover":
        return f"换手率 {value:.1f}%，{'交易分歧较高' if level else '交易分歧正常'}"
    if key == "change":
        return f"涨跌幅 {value:+.1f}%，{'价格波动显著' if level else '价格波动中性'}"
    if key == "amount":
        return f"成交额强度 {value:.1f}，资金信号参考"
    if key == "amplitude":
        return f"振幅 {value:.1f}%，{'日内波动偏大' if level else '日内波动正常'}"
    return f"波动强度 {value:.1f}，{'需关注' if level else '中性'}"


# =============================================================================
# 侧边导航
# =============================================================================

_NAV_ITEMS = [
    ("#core", "📊", "核心"),
    ("#judgment", "🧭", "判断"),
    ("#price-range", "📈", "价格"),
    ("#vol-price", "🔄", "量价"),
    ("#risk-gauge", "🎯", "仪表"),
    ("#anomaly-breakdown", "📊", "异动"),
    ("#technical", "📈", "技术"),
    ("#risk-dist", "⚠️", "风险"),
    ("#radar", "📡", "雷达"),
    ("#quality", "✅", "数据"),
    ("#decision", "🎯", "建议"),
]


def _nav_html() -> str:
    items = []
    for href, icon, label in _NAV_ITEMS:
        items.append(
            f'<a class="nav-item" href="{href}" title="{_html(label)}">{icon}</a>'
        )
    return '<nav class="side-nav">' + "".join(items) + "</nav>"


# =============================================================================
# 风险可视化
# =============================================================================

def _risk_distribution_html(signals: Sequence[RiskSignal]) -> str:
    counts = risk_level_counts(signals)
    total = sum(counts.values())
    max_count = max(counts.values(), default=0)

    if total == 0:
        return (
            '<section class="panel" id="risk-dist">'
            "<h2>风险可视化</h2>"
            '<div class="empty-state">暂无显著异动，风险分布保持平稳。</div>'
            "</section>"
        )

    dominant_level = max(counts, key=lambda level: counts[level]) if total else 0
    max_level = max((sig.level for sig in signals), default=0)
    dual = calculate_dual_risk_score(signals)
    concentration = max_count / total * 100 if total else 0
    danger_ratio = counts[3] / total * 100 if total else 0
    risk_summary = _risk_distribution_summary(max_level, danger_ratio, concentration, total)

    rows = []
    for level in (1, 2, 3):
        count = counts[level]
        width = 0 if max_count == 0 else count / max_count * 100
        rows.append(
            '<div class="bar-row">'
            f'<span>{_html(signal_level_label(level))}</span>'
            '<div class="bar-track">'
            f'<i style="width:{width:.1f}%; background:{LEVEL_COLORS[level]};"></i>'
            "</div>"
            f"<strong>{count}</strong>"
            f"<em>{render_count_bar(count, max_count)}</em>"
            "</div>"
        )

    pie_style = _level_pie_gradient(counts)
    insight_cards = [
        ("异动强度", f"{dual.anomaly_score}", dual.anomaly_label),
        ("下行风险", f"{dual.risk_score}", dual.risk_label),
        ("最高等级", fmt_signal_level(max_level), _risk_level_hint(max_level)),
        ("风险集中度", f"{concentration:.0f}%", f"主要集中在{signal_level_label(dominant_level)}级信号"),
        ("触发信号", f"{total} 个", "来自当前检测到的技术异动维度"),
    ]
    return (
        '<section class="panel" id="risk-dist">'
        "<h2>风险可视化</h2>"
        f'<p class="section-brief">{_html(risk_summary)}</p>'
        '<div class="risk-insight-grid">'
        + "".join(
            '<article class="risk-insight-card">'
            f'<span>{_html(label)}</span>'
            f'<strong>{_html(value)}</strong>'
            f'<em>{_html(hint)}</em>'
            '</article>'
            for label, value, hint in insight_cards
        )
        + '</div>'
        '<div class="chart-grid enriched">'
        '<div class="chart-card">'
        "<h3>风险等级占比</h3>"
        f'<div class="pie" style="{pie_style}"><span>{total}</span></div>'
        '<p class="muted">按 RiskSignal 等级聚合</p>'
        "</div>"
        '<div class="chart-card wide">'
        "<h3>风险分布柱</h3>"
        + "".join(rows)
        + "</div>"
        "</div>"
        '<div class="risk-explain-list">'
        + "".join(_risk_distribution_explanations(signals))
        + "</div>"
        "</section>"
    )


def _anomaly_breakdown_html(signals: Sequence[RiskSignal]) -> str:
    rows = anomaly_breakdown_rows(signals)
    cards = []
    for dimension, performance, score, note in rows:
        width = max(0, min(score, 100))
        tone = "high" if score >= 75 else "medium" if score >= 45 else "low"
        cards.append(
            f'<article class="anomaly-card {tone}">'
            '<div class="anomaly-card-head">'
            f'<span>{_html(dimension)}</span>'
            f'<strong>{score}</strong>'
            '</div>'
            f'<div class="anomaly-bar"><i style="width:{width}%;"></i></div>'
            f'<div class="anomaly-meta"><b>{_html(performance)}</b><em>{render_score_bar(score)}</em></div>'
            f'<p>{_html(note)}</p>'
            '</article>'
        )

    return (
        '<section class="panel" id="anomaly-breakdown">'
        "<h2>异动强度拆解</h2>"
        '<p class="section-brief">这张表只解释“今天哪里不寻常”，不直接等同于下行风险。上涨异动、放量、技术信号和公告事件会分别计入。</p>'
        '<div class="anomaly-breakdown-grid">'
        + "".join(cards)
        + "</div>"
        "</section>"
    )


def _signal_composition_html(signals: Sequence[RiskSignal]) -> str:
    composition = risk_type_counts(signals)
    if not composition:
        return (
            '<section class="panel">'
            "<h2>信号构成</h2>"
            '<div class="empty-state">暂无显著异动信号。</div>'
            "</section>"
        )

    max_count = max(count for _, count, _ in composition)
    segments = [(risk_type, count) for risk_type, count, _ in composition]
    pie_style = _pie_gradient(segments)

    rows = []
    cards = []
    for index, (risk_type, count, level) in enumerate(composition):
        width = count / max_count * 100
        color = TYPE_COLORS[index % len(TYPE_COLORS)]
        related = [sig for sig in signals if sig.risk_type == risk_type]
        top_sig = max(related, key=lambda sig: sig.level)
        detail = _signal_detail_sentence(top_sig)
        rows.append(
            '<div class="bar-row">'
            f'<span><b style="background:{color};"></b>{_html(risk_type)}</span>'
            '<div class="bar-track">'
            f'<i style="width:{width:.1f}%; background:{color};"></i>'
            "</div>"
            f"<strong>{count}</strong>"
            f"<em>{_html(fmt_signal_level(level))} {render_signal_bar(level)}</em>"
            "</div>"
        )
        cards.append(
            '<article class="signal-detail-card">'
            f'<div class="signal-detail-head"><span style="background:{color};"></span><strong>{_html(risk_type)}</strong><kbd>{_html(fmt_signal_level(level))}</kbd></div>'
            f'<p>{_html(detail)}</p>'
            '<dl>'
            f'<div><dt>影响维度</dt><dd>{_html(_risk_type_dimension(risk_type))}</dd></div>'
            f'<div><dt>观察重点</dt><dd>{_html(_risk_type_watchpoint(risk_type))}</dd></div>'
            f'<div><dt>触发次数</dt><dd>{count} 个</dd></div>'
            '</dl>'
            '</article>'
        )

    return (
        '<section class="panel">'
        "<h2>信号构成</h2>"
        f'<p class="section-brief">{_html(_signal_composition_summary(composition))}</p>'
        '<div class="chart-grid enriched">'
        '<div class="chart-card">'
        "<h3>类型占比</h3>"
        f'<div class="pie" style="{pie_style}"><span>{sum(count for _, count, _ in composition)}</span></div>'
        '<p class="muted">按风险类型聚合</p>'
        "</div>"
        '<div class="chart-card wide">'
        "<h3>构成柱图</h3>"
        + "".join(rows)
        + "</div>"
        "</div>"
        '<div class="signal-detail-grid">'
        + "".join(cards)
        + "</div>"
        "</section>"
    )


def _risk_distribution_summary(max_level: int, danger_ratio: float, concentration: float, total: int) -> str:
    if max_level >= 3:
        return f"当前共有 {total} 个异动信号，最高达到危险级；危险信号占比 {danger_ratio:.0f}%，需要优先确认价格和资金承接。"
    if max_level == 2:
        return f"当前共有 {total} 个异动信号，最高为警告级；风险集中度 {concentration:.0f}%，适合继续观察持续性。"
    return f"当前共有 {total} 个异动信号，最高为关注级；风险仍处于早期观察阶段。"


def _risk_level_hint(level: int) -> str:
    if level >= 3:
        return "短线波动或流动性风险较高"
    if level == 2:
        return "存在明显异动，需要确认持续性"
    if level == 1:
        return "轻度偏离，适合常规跟踪"
    return "未检测到显著风险"


def _risk_distribution_explanations(signals: Sequence[RiskSignal]) -> List[str]:
    if not signals:
        return []
    lines = []
    for sig in sorted(signals, key=lambda item: (-item.level, item.risk_type))[:4]:
        detail = _signal_detail_sentence(sig)
        lines.append(
            '<div class="risk-explain-item">'
            f'<strong>{_html(sig.risk_type)}</strong>'
            f'<span>{_html(fmt_signal_level(sig.level))}</span>'
            f'<p>{_html(detail)}</p>'
            '</div>'
        )
    return lines


def _signal_detail_sentence(signal: RiskSignal) -> str:
    if signal.risk_type.endswith("技术信号"):
        return signal.description
    return f"{signal.description}（偏离度 {signal.deviation_value:.1f}{signal.deviation_unit}）。"


def _signal_composition_summary(composition: Sequence[Tuple[str, int, int]]) -> str:
    top_type, top_count, top_level = composition[0]
    return f"信号主要来自“{top_type}”，共 {top_count} 个，最高等级为 {signal_level_label(top_level)}；下方列出每类信号的影响维度和观察重点。"


def _risk_type_dimension(risk_type: str) -> str:
    if "量比" in risk_type:
        return "成交活跃度"
    if "换手" in risk_type:
        return "筹码交换与资金分歧"
    if "收益" in risk_type or "涨跌" in risk_type:
        return "价格偏离与短线波动"
    return "综合技术异动"


def _risk_type_watchpoint(risk_type: str) -> str:
    if "量比" in risk_type:
        return "观察放量是否持续，以及价格是否同步确认方向"
    if "换手" in risk_type:
        return "观察高换手后价格是否走弱，避免分歧扩大"
    if "收益" in risk_type or "涨跌" in risk_type:
        return "观察次日开盘承接、跌停/涨停打开情况和成交变化"
    return "结合公告、财报和板块走势继续验证"


# =============================================================================
# 标的列表



# =============================================================================
# 技术指标图
# =============================================================================

def _technical_indicators_html(technical) -> str:
    if technical is None:
        return (
            '<section class="panel" id="technical">'
            "<h2>技术指标</h2>"
            '<div class="empty-state">历史数据不足，暂无法计算 MACD / RSI / BOLL / KDJ。</div>'
            "</section>"
        )

    return (
        '<section class="panel" id="technical">'
        "<h2>技术指标</h2>"
        '<div class="technical-grid">'
        + _macd_chart_inner_html(technical.macd)
        + _rsi_panel_html(technical.rsi)
        + _boll_panel_html(technical.boll)
        + _kdj_panel_html(technical.kdj)
        + "</div>"
        + _technical_trend_summary_html(technical)
        + _technical_signal_summary_html(technical)
        + "</section>"
    )


def _macd_chart_html(macd_result) -> str:
    """Backward-compatible MACD-only panel."""
    return (
        '<section class="panel" id="macd">'
        "<h2>MACD 指标</h2>"
        + _macd_chart_inner_html(macd_result)
        + _macd_signal_summary_html(macd_result)
        + "</section>"
    )


def _macd_chart_inner_html(macd_result) -> str:
    """Render an SVG MACD chart with histogram, DIF, DEA, and crossover markers."""
    if not macd_result or not macd_result.dates:
        return (
            '<div class="empty-state">历史数据不足，无法计算MACD指标。</div>'
        )

    dif = macd_result.dif
    dea = macd_result.dea
    hist = macd_result.macd
    dates = macd_result.dates

    # Take last ~45 bars for display
    display_len = min(45, len(dates))
    dif = dif[-display_len:]
    dea = dea[-display_len:]
    hist = hist[-display_len:]
    dates = dates[-display_len:]

    # Find data range
    all_vals = [v for v in dif + dea + hist if v != 0.0]
    if not all_vals:
        return (
            '<div class="empty-state">MACD数据不足，继续观察。</div>'
        )

    max_val = max(all_vals)
    min_val = min(all_vals)
    val_range = max(abs(max_val), abs(min_val)) * 1.15
    if val_range == 0:
        val_range = 1.0

    # Chart dimensions
    chart_w = 720
    chart_h = 300
    pad_left = 50
    pad_right = 20
    pad_top = 10
    pad_bottom = 30
    plot_w = chart_w - pad_left - pad_right
    plot_h = chart_h - pad_top - pad_bottom
    zero_y = pad_top + plot_h / 2

    def _val_to_y(v: float) -> float:
        return zero_y - (v / val_range) * (plot_h / 2)

    def _idx_to_x(i: int) -> float:
        return pad_left + i * (plot_w / max(display_len - 1, 1))

    # Histogram bars
    bars = []
    for i, h_val in enumerate(hist):
        if h_val == 0.0:
            continue
        x = _idx_to_x(i)
        bar_w = max(2, plot_w / display_len * 0.6)
        if h_val > 0:
            y = _val_to_y(h_val)
            h = zero_y - y
            color = "#ef3b2d"  # red for positive (bullish momentum)
        else:
            y = zero_y
            h = _val_to_y(h_val) - zero_y
            color = "#11a36a"  # green for negative (bearish momentum)
        if h < 0.5:
            h = 0.5
        bars.append(
            f'<rect x="{x - bar_w/2:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
            f'height="{h:.1f}" fill="{color}" opacity="0.7"/>'
        )

    # DIF line
    dif_points = []
    for i, v in enumerate(dif):
        if v == 0.0:
            continue
        dif_points.append(f"{_idx_to_x(i):.1f},{_val_to_y(v):.1f}")
    dif_path = " ".join(dif_points) if dif_points else ""

    # DEA line
    dea_points = []
    for i, v in enumerate(dea):
        if v == 0.0:
            continue
        dea_points.append(f"{_idx_to_x(i):.1f},{_val_to_y(v):.1f}")
    dea_path = " ".join(dea_points) if dea_points else ""

    # Zero line
    zero_line = (
        f'<line x1="{pad_left}" y1="{zero_y:.1f}" '
        f'x2="{pad_left + plot_w}" y2="{zero_y:.1f}" '
        f'stroke="#94a3b8" stroke-width="1" stroke-dasharray="4 4"/>'
    )

    # Date labels (every ~10 bars)
    date_labels = []
    step = max(1, display_len // 5)
    for i in range(0, display_len, step):
        if i >= len(dates):
            break
        d = dates[i]
        short_date = d[5:] if len(d) >= 10 else d  # MM-DD
        date_labels.append(
            f'<text x="{_idx_to_x(i):.1f}" y="{chart_h - 8}" '
            f'text-anchor="middle" class="macd-date-label">{short_date}</text>'
        )

    # Legend
    legend_y = pad_top + 8

    return (
        '<div class="macd-chart-container">'
        f'<svg viewBox="0 0 {chart_w} {chart_h}" class="macd-svg" role="img" aria-label="MACD indicator chart">'
        # Grid lines
        + zero_line
        + f'<line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{chart_h - pad_bottom}" stroke="#e5eaf2" stroke-width="1"/>'
        + f'<line x1="{pad_left}" y1="{chart_h - pad_bottom:.1f}" x2="{pad_left + plot_w}" y2="{chart_h - pad_bottom:.1f}" stroke="#e5eaf2" stroke-width="1"/>'
        # Bars
        + "".join(bars)
        # Lines
        + (
            f'<polyline points="{dif_path}" fill="none" stroke="#2563eb" stroke-width="1.8" stroke-linejoin="round"/>'
            if dif_points else ""
        )
        + (
            f'<polyline points="{dea_path}" fill="none" stroke="#f59e0b" stroke-width="1.8" stroke-linejoin="round"/>'
            if dea_points else ""
        )
        # Date labels
        + "".join(date_labels)
        # Legend
        + f'<rect x="{pad_left}" y="{legend_y}" width="10" height="10" fill="#2563eb" rx="1"/>'
        + f'<text x="{pad_left + 14}" y="{legend_y + 9}" class="macd-legend">DIF</text>'
        + f'<rect x="{pad_left + 45}" y="{legend_y}" width="10" height="10" fill="#f59e0b" rx="1"/>'
        + f'<text x="{pad_left + 59}" y="{legend_y + 9}" class="macd-legend">DEA</text>'
        + f'<rect x="{pad_left + 95}" y="{legend_y}" width="10" height="10" fill="#ef3b2d" rx="1"/>'
        + f'<text x="{pad_left + 109}" y="{legend_y + 9}" class="macd-legend">多头柱</text>'
        + f'<rect x="{pad_left + 155}" y="{legend_y}" width="10" height="10" fill="#11a36a" rx="1"/>'
        + f'<text x="{pad_left + 169}" y="{legend_y + 9}" class="macd-legend">空头柱</text>'
        + "</svg>"
        "</div>"
    )


def _macd_signal_summary_html(macd_result) -> str:
    """Generate MACD signal summary text."""
    from core.analysis import detect_macd_signals
    signals = detect_macd_signals(macd_result)
    if not signals:
        return '<p class="muted">近期未检测到MACD金叉/死叉信号。</p>'

    recent = [s for s in signals if s.date == signals[-1].date]
    if not recent:
        return '<p class="muted">近期未检测到MACD金叉/死叉信号。</p>'

    sig = recent[0]
    icon = "🔴" if sig.signal_type == "death_cross" else "🟢"
    return (
        '<div class="macd-signal-card">'
        f'<strong>{icon} {_html(sig.description)}</strong>'
        f'<em>触发日期：{sig.date}</em>'
        '</div>'
    )


def _rsi_panel_html(rsi_result) -> str:
    latest = rsi_result.latest if rsi_result else None
    if latest is None:
        return (
            '<div class="rsi-panel">'
            "<h3>RSI</h3>"
            '<div class="empty-state">RSI 数据不足。</div>'
            "</div>"
        )

    pos = max(0, min(100, latest))
    if latest >= 70:
        zone = "超买区"
        tone = "bearish"
    elif latest <= 30:
        zone = "超卖区"
        tone = "watch"
    else:
        zone = "中性区"
        tone = "neutral"

    return (
        f'<div class="rsi-panel {tone}">'
        f"<h3>RSI{rsi_result.period}</h3>"
        f'<strong>{latest:.2f}</strong>'
        f"<p>{_html(zone)}</p>"
        '<div class="rsi-track">'
        '<span class="rsi-zone low"></span><span class="rsi-zone mid"></span><span class="rsi-zone high"></span>'
        f'<i style="left:{pos:.2f}%"></i>'
        "</div>"
        '<div class="rsi-labels"><span>0</span><span>30</span><span>70</span><span>100</span></div>'
        "</div>"
    )


def _boll_panel_html(boll_result) -> str:
    latest = boll_result.latest if boll_result else None
    if latest is None:
        return (
            '<div class="rsi-panel">'
            "<h3>BOLL</h3>"
            '<div class="empty-state">BOLL 数据不足。</div>'
            "</div>"
        )

    upper, middle, lower = latest
    width = upper - lower
    if width <= 0:
        pos = 50.0
    else:
        pos = max(0, min(100, (middle - lower) / width * 100))

    return (
        '<div class="rsi-panel neutral">'
        f"<h3>BOLL{boll_result.period}</h3>"
        f"<strong>{middle:.2f}</strong>"
        f"<p>中轨 · 上 {upper:.2f} / 下 {lower:.2f}</p>"
        '<div class="rsi-track">'
        '<span class="rsi-zone low"></span><span class="rsi-zone mid"></span><span class="rsi-zone high"></span>'
        f'<i style="left:{pos:.2f}%"></i>'
        "</div>"
        '<div class="rsi-labels"><span>下轨</span><span>中轨</span><span>上轨</span></div>'
        "</div>"
    )


def _kdj_panel_html(kdj_result) -> str:
    latest = kdj_result.latest if kdj_result else None
    if latest is None:
        return (
            '<div class="rsi-panel">'
            "<h3>KDJ</h3>"
            '<div class="empty-state">KDJ 数据不足。</div>'
            "</div>"
        )

    k, d, j = latest
    if k >= 80 and d >= 75:
        tone = "bearish"
        zone = "超买区"
    elif k <= 20 and d <= 25:
        tone = "watch"
        zone = "超卖区"
    elif k > d:
        tone = "neutral"
        zone = "偏多"
    else:
        tone = "watch"
        zone = "偏弱"
    pos = max(0, min(100, k))

    return (
        f'<div class="rsi-panel {tone}">'
        f"<h3>KDJ{kdj_result.period}</h3>"
        f"<strong>{k:.2f}</strong>"
        f"<p>{_html(zone)} · D {d:.2f} / J {j:.2f}</p>"
        '<div class="rsi-track">'
        '<span class="rsi-zone low"></span><span class="rsi-zone mid"></span><span class="rsi-zone high"></span>'
        f'<i style="left:{pos:.2f}%"></i>'
        "</div>"
        '<div class="rsi-labels"><span>0</span><span>20</span><span>80</span><span>100</span></div>'
        "</div>"
    )



def _technical_trend_summary_html(technical) -> str:
    """Render trend summary cards for MACD alignment, RSI trend, and divergence."""
    if not technical or not technical.trend:
        return ""

    t = technical.trend
    cards = []

    # MACD alignment card
    if t.macd_alignment:
        al_tone_map = {
            "bullish": "bullish",
            "bearish": "bearish",
            "turning": "watch",
            "neutral": "neutral",
        }
        al_icon_map = {
            "bullish": "⇈",
            "bearish": "⇊",
            "turning": "⇄",
            "neutral": "→",
        }
        tone = al_tone_map.get(t.macd_alignment, "neutral")
        icon = al_icon_map.get(t.macd_alignment, "→")
        bar_status = {
            "expanding": "扩张",
            "contracting": "收敛",
            "flat": "持平",
        }.get(t.macd_histogram_trend, "")
        cards.append(
            f'<div class="trend-card {tone}">'
            f'<span class="trend-icon">{icon}</span>'
            f'<div class="trend-body">'
            f'<span class="trend-label">MACD 排列</span>'
            f'<strong>{_html(t.macd_alignment_desc)}</strong>'
            f'<em>柱状图趋势：{bar_status}</em>'
            f'</div>'
            f'</div>'
        )

    # RSI trend card
    if t.rsi_trend:
        rsi_tone_map = {
            "overbought_pullback": "bearish",
            "oversold_bounce": "bullish",
            "uptrend": "bullish",
            "downtrend": "bearish",
            "heated": "watch",
            "cooling": "watch",
            "neutral": "neutral",
        }
        rsi_icon_map = {
            "overbought_pullback": "↘",
            "oversold_bounce": "↗",
            "uptrend": "↑",
            "downtrend": "↓",
            "heated": "△",
            "cooling": "▽",
            "neutral": "→",
        }
        tone = rsi_tone_map.get(t.rsi_trend, "neutral")
        icon = rsi_icon_map.get(t.rsi_trend, "→")
        cards.append(
            f'<div class="trend-card {tone}">'
            f'<span class="trend-icon">{icon}</span>'
            f'<div class="trend-body">'
            f'<span class="trend-label">RSI 趋势</span>'
            f'<strong>{_html(t.rsi_trend_desc)}</strong>'
            f'</div>'
            f'</div>'
        )

    # Divergence card
    if t.divergence:
        tone = "bearish" if t.divergence == "bearish" else "bullish"
        icon = "⚠" if t.divergence == "bearish" else "✦"
        cards.append(
            f'<div class="trend-card {tone}">'
            f'<span class="trend-icon">{icon}</span>'
            f'<div class="trend-body">'
            f'<span class="trend-label">背离检测</span>'
            f'<strong>{_html(t.divergence_desc)}</strong>'
            f'</div>'
            f'</div>'
        )

    if not cards:
        return ""

    return (
        '<div class="trend-summary">'
        + "".join(cards)
        + "</div>"
    )



def _technical_signal_summary_html(technical) -> str:
    if not technical.signals:
        notes = "；".join(technical.notes) if technical.notes else "近期未检测到 MACD / RSI / BOLL / KDJ 技术信号。"
        return f'<p class="muted">{_html(notes)}</p>'

    cards = []
    for signal in technical.signals[-4:]:
        level = signal.level
        tone = "bullish" if signal.direction == "bullish" else "bearish"
        level_text = signal_level_label(level) if level else "辅助"
        cards.append(
            f'<div class="technical-signal {tone}">'
            f'<span>{_html(signal.indicator)} · {_html(level_text)}</span>'
            f'<strong>{_html(signal.description)}</strong>'
            f'<em>{_html(signal.date)}</em>'
            "</div>"
        )
    return '<div class="technical-signals">' + "".join(cards) + "</div>"

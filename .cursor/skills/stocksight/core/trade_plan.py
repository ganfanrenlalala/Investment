# -*- coding: utf-8 -*-
"""Price- and volatility-based execution plans."""

from __future__ import annotations

from dataclasses import replace
import math
from statistics import mean
from typing import Optional, Sequence

from .strategy import StrategyDecision
from .types import HistoryBar, StockData, StockHistory, TradePlan


NO_NEW_POSITION_ACTIONS = {
    "风险规避",
    "触发退出",
    "不适合参与",
    "排雷未通过",
    "重点排查",
    "高位降温",
    "触发减仓",
}
BREAKOUT_ACTIONS = {"波段候选", "突破确认", "可小仓试错", "进入候选池"}
PULLBACK_ACTIONS = {"回踩观察", "低位修复"}


def compute_atr(history: StockHistory, period: int = 14) -> Optional[float]:
    """Return the latest simple ATR from point-in-time OHLC bars."""
    bars = _valid_bars(history)
    if period <= 0 or len(bars) < period + 1:
        return None
    true_ranges = []
    for index in range(1, len(bars)):
        bar = bars[index]
        previous_close = bars[index - 1].close
        true_ranges.append(
            max(
                bar.high - bar.low,
                abs(bar.high - previous_close),
                abs(bar.low - previous_close),
            )
        )
    return mean(true_ranges[-period:])


def build_trade_plan(
    stock: StockData,
    history: Optional[StockHistory],
    decision: StrategyDecision,
    *,
    account_size: Optional[float] = None,
    risk_per_trade_percent: float = 0.5,
    max_position_percent: float = 20.0,
    atr_period: int = 14,
    max_stop_percent: float = 8.0,
) -> TradePlan:
    """Build an explainable long-side plan from market structure and ATR."""
    if risk_per_trade_percent <= 0:
        raise ValueError("risk_per_trade_percent must be positive")
    if max_position_percent <= 0 or max_position_percent > 100:
        raise ValueError("max_position_percent must be between 0 and 100")
    if account_size is not None and account_size <= 0:
        raise ValueError("account_size must be positive")

    bars = _merge_current_bar(stock, history)
    atr = compute_atr(StockHistory(code=stock.code, bars=bars), period=atr_period)
    if atr is None or atr <= 0 or stock.current_price <= 0:
        return _unavailable_plan(
            decision,
            risk_per_trade_percent,
            max_position_percent,
            account_size,
            "历史 K 线不足，无法计算 ATR 和结构止损。",
        )

    current = stock.current_price
    tick = _price_tick(current)
    atr_percent = atr / current * 100
    recent = bars[-20:]
    prior = bars[-21:-1] if len(bars) >= 21 else bars[:-1]
    prior = prior or bars[:-1] or bars
    structure_window = bars[-6:-1] if len(bars) >= 6 else bars[:-1]
    structure_window = structure_window or bars
    structure_support = min(item.low for item in structure_window)
    recent_resistance = max(item.high for item in prior[-20:])
    sma20 = mean(item.close for item in recent)

    if (
        decision.profile == "risk_avoid"
        or decision.action in NO_NEW_POSITION_ACTIONS
        or decision.tone == "danger"
    ):
        protective_stop = _round_price(
            min(current - 1.5 * atr, structure_support - 0.2 * atr),
            current,
        )
        return TradePlan(
            profile=decision.profile,
            action=decision.action,
            status="avoid",
            status_label="不新开仓",
            entry_style="风险控制",
            stop_loss=protective_stop if protective_stop > 0 else None,
            atr=round(atr, 4),
            atr_percent=round(atr_percent, 2),
            structure_support=_round_price(structure_support, current),
            recent_resistance=_round_price(recent_resistance, current),
            risk_per_trade_percent=risk_per_trade_percent,
            max_position_percent=max_position_percent,
            suggested_position_percent=0.0,
            account_size=account_size,
            risk_budget_amount=(
                round(account_size * risk_per_trade_percent / 100, 2)
                if account_size is not None
                else None
            ),
            position_value=0.0 if account_size is not None else None,
            shares=0 if account_size is not None else None,
            lot_size=_lot_size(stock),
            basis=[
                f"ATR({atr_period}) {atr:.2f}，约占现价 {atr_percent:.2f}%",
                f"近期结构支撑 {_round_price(structure_support, current):.2f}",
                "当前策略状态不支持新开仓",
            ],
            invalidation=decision.invalidation,
            note="止损价仅供已有仓位做保护参考；事件风险或跳空可能使止损无法按计划成交。",
        )

    entry_style, trigger, entry_low, entry_high = _entry_plan(
        decision.action,
        current,
        atr,
        recent_resistance,
        sma20,
        tick,
    )
    stop_loss = min(trigger - 1.5 * atr, structure_support - 0.2 * atr)
    stop_loss = _round_price(stop_loss, current)
    trigger = _round_price(trigger, current)
    entry_low = _round_price(entry_low, current)
    entry_high = _round_price(entry_high, current)
    if stop_loss <= 0 or stop_loss >= trigger:
        return _unavailable_plan(
            decision,
            risk_per_trade_percent,
            max_position_percent,
            account_size,
            "价格结构无法形成有效止损距离。",
            atr=atr,
            atr_percent=atr_percent,
        )

    risk_per_share = trigger - stop_loss
    stop_distance_percent = risk_per_share / trigger * 100
    if stop_distance_percent > max_stop_percent:
        return TradePlan(
            profile=decision.profile,
            action=decision.action,
            status="wait",
            status_label="等待结构收紧",
            entry_style=entry_style,
            trigger_price=trigger,
            entry_low=entry_low,
            entry_high=entry_high,
            stop_loss=stop_loss,
            atr=round(atr, 4),
            atr_percent=round(atr_percent, 2),
            structure_support=_round_price(structure_support, current),
            recent_resistance=_round_price(recent_resistance, current),
            stop_distance_percent=round(stop_distance_percent, 2),
            risk_per_trade_percent=risk_per_trade_percent,
            max_position_percent=max_position_percent,
            suggested_position_percent=0.0,
            account_size=account_size,
            risk_budget_amount=(
                round(account_size * risk_per_trade_percent / 100, 2)
                if account_size is not None
                else None
            ),
            position_value=0.0 if account_size is not None else None,
            shares=0 if account_size is not None else None,
            lot_size=_lot_size(stock),
            basis=[
                f"ATR({atr_period}) {atr:.2f}，约占现价 {atr_percent:.2f}%",
                f"结构止损距离 {stop_distance_percent:.2f}% 超过上限 {max_stop_percent:.2f}%",
            ],
            invalidation=decision.invalidation,
            note="当前结构要求承担的单股波动过大，等待回踩、横盘或支撑抬高后再计算。",
        )

    target_1 = _round_price(trigger + max(1.5 * risk_per_share, 1.5 * atr), current)
    target_2 = _round_price(trigger + max(2.5 * risk_per_share, 3.0 * atr), current)
    rr1 = (target_1 - trigger) / risk_per_share
    rr2 = (target_2 - trigger) / risk_per_share
    suggested_position_percent = min(
        max_position_percent,
        risk_per_trade_percent / stop_distance_percent * 100,
    )
    lot_size = _lot_size(stock)
    risk_budget_amount = None
    position_value = None
    shares = None
    if account_size is not None:
        risk_budget_amount = account_size * risk_per_trade_percent / 100
        risk_limited_shares = math.floor(risk_budget_amount / risk_per_share)
        position_limited_shares = math.floor(
            account_size * max_position_percent / 100 / trigger
        )
        raw_shares = min(risk_limited_shares, position_limited_shares)
        shares = raw_shares // lot_size * lot_size
        position_value = shares * trigger
        suggested_position_percent = (
            position_value / account_size * 100 if account_size > 0 else 0.0
        )

    status = "ready"
    status_label = "条件触发后执行"
    note = "未到触发价不执行；触发后若直接跳空超过入场区上沿，放弃追价并重新计算。"
    if current > entry_high:
        status = "wait"
        status_label = "等待回踩，避免追价"
        suggested_position_percent = 0.0
        position_value = 0.0 if account_size is not None else None
        shares = 0 if account_size is not None else None
        note = "当前价已高于计划入场区，原风险收益比失真，等待新结构形成。"

    return TradePlan(
        profile=decision.profile,
        action=decision.action,
        status=status,
        status_label=status_label,
        entry_style=entry_style,
        trigger_price=trigger,
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        atr=round(atr, 4),
        atr_percent=round(atr_percent, 2),
        structure_support=_round_price(structure_support, current),
        recent_resistance=_round_price(recent_resistance, current),
        stop_distance_percent=round(stop_distance_percent, 2),
        reward_risk_1=round(rr1, 2),
        reward_risk_2=round(rr2, 2),
        risk_per_trade_percent=risk_per_trade_percent,
        max_position_percent=max_position_percent,
        suggested_position_percent=round(suggested_position_percent, 2),
        account_size=account_size,
        risk_budget_amount=round(risk_budget_amount, 2) if risk_budget_amount is not None else None,
        position_value=round(position_value, 2) if position_value is not None else None,
        shares=shares,
        lot_size=lot_size,
        basis=[
            f"ATR({atr_period}) {atr:.2f}，约占现价 {atr_percent:.2f}%",
            f"近期结构支撑 {_round_price(structure_support, current):.2f}",
            f"近 20 日阻力 {_round_price(recent_resistance, current):.2f}",
            f"单笔账户风险预算 {risk_per_trade_percent:.2f}%",
        ],
        invalidation=decision.invalidation,
        note=note,
    )


def resize_trade_plan(
    plan: TradePlan,
    *,
    account_size: Optional[float],
    risk_per_trade_percent: Optional[float] = None,
    max_position_percent: Optional[float] = None,
) -> TradePlan:
    """Recalculate position sizing from an existing price plan."""
    risk_percent = (
        plan.risk_per_trade_percent
        if risk_per_trade_percent is None
        else risk_per_trade_percent
    )
    max_position = (
        plan.max_position_percent
        if max_position_percent is None
        else max_position_percent
    )
    if account_size is None:
        return replace(
            plan,
            account_size=None,
            risk_budget_amount=None,
            position_value=None,
            shares=None,
            risk_per_trade_percent=risk_percent,
            max_position_percent=max_position,
        )
    if account_size <= 0 or risk_percent <= 0 or max_position <= 0:
        raise ValueError("account and risk sizing values must be positive")
    if plan.status != "ready" or not plan.trigger_price or not plan.stop_loss:
        return replace(
            plan,
            account_size=account_size,
            risk_budget_amount=round(account_size * risk_percent / 100, 2),
            position_value=0.0,
            shares=0,
            suggested_position_percent=0.0,
            risk_per_trade_percent=risk_percent,
            max_position_percent=max_position,
        )
    risk_per_share = plan.trigger_price - plan.stop_loss
    risk_budget = account_size * risk_percent / 100
    by_risk = math.floor(risk_budget / risk_per_share)
    by_position = math.floor(account_size * max_position / 100 / plan.trigger_price)
    shares = min(by_risk, by_position) // plan.lot_size * plan.lot_size
    position_value = shares * plan.trigger_price
    return replace(
        plan,
        account_size=account_size,
        risk_budget_amount=round(risk_budget, 2),
        position_value=round(position_value, 2),
        shares=shares,
        suggested_position_percent=round(position_value / account_size * 100, 2),
        risk_per_trade_percent=risk_percent,
        max_position_percent=max_position,
    )


def _entry_plan(action, current, atr, resistance, sma20, tick):
    if action in BREAKOUT_ACTIONS:
        trigger = max(current, resistance + tick)
        return "突破触发", trigger, trigger, trigger + 0.25 * atr
    if action in PULLBACK_ACTIONS:
        trigger = max(current + 0.35 * atr, resistance + tick)
        return "回踩后转强", trigger, trigger, trigger + 0.25 * atr
    pullback_low = max(sma20, current - 0.75 * atr)
    pullback_high = max(pullback_low, current - 0.20 * atr)
    return "趋势回踩", pullback_high, pullback_low, pullback_high


def _merge_current_bar(stock: StockData, history: Optional[StockHistory]):
    bars = list(_valid_bars(history))
    current_date = stock.timestamp[:10] if stock.timestamp else ""
    current_bar = HistoryBar(
        date=current_date or (bars[-1].date if bars else ""),
        open=stock.open_price or stock.current_price,
        high=stock.high or stock.current_price,
        low=stock.low or stock.current_price,
        close=stock.current_price,
        volume=stock.volume,
        amount=stock.amount,
        turnover_rate=stock.turnover_rate,
        change_percent=stock.change_percent,
    )
    if bars and current_bar.date and bars[-1].date == current_bar.date:
        bars[-1] = current_bar
    else:
        bars.append(current_bar)
    return bars


def _valid_bars(history: Optional[StockHistory]) -> Sequence[HistoryBar]:
    if history is None:
        return []
    return [
        bar
        for bar in history.bars
        if bar.close > 0 and bar.high > 0 and bar.low > 0
    ]


def _price_tick(price: float) -> float:
    return 0.01 if price < 1000 else 0.1


def _round_price(value: float, reference: float) -> float:
    decimals = 2 if reference < 1000 else 1
    return round(value, decimals)


def _lot_size(stock: StockData) -> int:
    return 100 if stock.market in ("sh", "sz") else 1


def _unavailable_plan(
    decision,
    risk_percent,
    max_position,
    account_size,
    note,
    *,
    atr=None,
    atr_percent=None,
):
    return TradePlan(
        profile=decision.profile,
        action=decision.action,
        status="unavailable",
        status_label="计划不可用",
        entry_style="数据不足",
        atr=round(atr, 4) if atr is not None else None,
        atr_percent=round(atr_percent, 2) if atr_percent is not None else None,
        risk_per_trade_percent=risk_percent,
        max_position_percent=max_position,
        suggested_position_percent=0.0,
        account_size=account_size,
        risk_budget_amount=(
            round(account_size * risk_percent / 100, 2)
            if account_size is not None
            else None
        ),
        position_value=0.0 if account_size is not None else None,
        shares=0 if account_size is not None else None,
        basis=[],
        invalidation=decision.invalidation,
        note=note,
    )

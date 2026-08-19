# -*- coding: utf-8 -*-
"""Persistent trade lifecycle state machine."""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple
from uuid import uuid4

from .types import (
    StockData,
    TradeLifecycle,
    TradeLifecycleEvent,
    TradePlan,
)

LIFECYCLE_SCHEMA_VERSION = 1

STATE_CANDIDATE = "candidate"
STATE_TRIGGERED = "triggered"
STATE_HOLDING = "holding"
STATE_EXITED = "exited"
STATE_REVIEWED = "reviewed"

STATE_LABELS = {
    STATE_CANDIDATE: "候选",
    STATE_TRIGGERED: "已触发",
    STATE_HOLDING: "持仓中",
    STATE_EXITED: "已退出",
    STATE_REVIEWED: "已复盘",
}


def plan_fingerprint(stock: StockData, plan: TradePlan) -> str:
    """Return a stable identity for one planned setup."""
    return _plan_fingerprint_for_code(stock.code, plan)


def _plan_fingerprint_for_code(stock_code: str, plan: TradePlan) -> str:
    values = (
        stock_code,
        plan.profile,
        plan.action,
        _price_key(plan.trigger_price),
        _price_key(plan.stop_loss),
        _price_key(plan.target_2),
    )
    return "|".join(values)


def load_lifecycle_ledger(path: Path) -> List[TradeLifecycle]:
    """Load lifecycle records from a JSON ledger."""
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read lifecycle ledger: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid lifecycle ledger JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("lifecycle ledger must be a JSON object")
    schema_version = payload.get("schema_version", 1)
    if schema_version != LIFECYCLE_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported lifecycle schema version: {schema_version}"
        )
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise ValueError("lifecycle ledger records must be a list")
    return [lifecycle_from_dict(item) for item in records if isinstance(item, dict)]


def save_lifecycle_ledger(path: Path, records: Sequence[TradeLifecycle]) -> Path:
    """Atomically persist lifecycle records."""
    payload = {
        "schema_version": LIFECYCLE_SCHEMA_VERSION,
        "generated_by": "StockSight-Skill",
        "records": [asdict(item) for item in records],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
    return path.resolve()


def lifecycle_from_dict(payload: dict) -> TradeLifecycle:
    """Deserialize a lifecycle while tolerating future extra fields."""
    allowed = {item.name for item in fields(TradeLifecycle)}
    values = {key: value for key, value in payload.items() if key in allowed}
    values["events"] = [
        TradeLifecycleEvent(
            **{
                key: value
                for key, value in item.items()
                if key in {field.name for field in fields(TradeLifecycleEvent)}
            }
        )
        for item in payload.get("events", [])
        if isinstance(item, dict)
    ]
    return TradeLifecycle(**values)


def find_current_lifecycle(
    records: Sequence[TradeLifecycle],
    stock_code: str,
    profile: str,
) -> Optional[TradeLifecycle]:
    """Return the newest lifecycle for a stock and strategy profile."""
    matches = [
        item
        for item in records
        if item.stock_code == stock_code and item.profile == profile
    ]
    return matches[-1] if matches else None


def sync_trade_lifecycle(
    records: List[TradeLifecycle],
    stock: StockData,
    plan: Optional[TradePlan],
    *,
    timestamp: str,
    fill_price: Optional[float] = None,
    fill_shares: Optional[int] = None,
    exit_price: Optional[float] = None,
    exit_reason: str = "",
    review_note: str = "",
    review_grade: str = "",
) -> Tuple[Optional[TradeLifecycle], bool]:
    """Create or advance the current lifecycle using market and manual events."""
    profile = plan.profile if plan else "neutral"
    current = find_current_lifecycle(records, stock.code, profile)
    fingerprint = plan_fingerprint(stock, plan) if plan else ""
    changed = False

    if current is None or (
        current.state == STATE_REVIEWED
        and fingerprint
        and fingerprint != current.plan_fingerprint
    ):
        if not _is_actionable_plan(plan):
            return current, False
        current = _new_lifecycle(stock, plan, timestamp, fingerprint)
        records.append(current)
        changed = True
        if _market_triggered(stock, plan):
            _transition(
                current,
                STATE_TRIGGERED,
                timestamp,
                _trigger_observation_price(stock, plan),
                "价格进入计划入场区",
                "market",
            )

    if current is None:
        return None, changed

    if current.state == STATE_CANDIDATE and plan:
        _refresh_candidate_plan(current, plan, timestamp)
        changed = True
        if _plan_invalid(plan) and fill_price is None:
            _close_without_fill(
                current,
                timestamp,
                stock.current_price,
                "候选条件失效，未成交",
            )
        elif _market_triggered(stock, plan):
            _transition(
                current,
                STATE_TRIGGERED,
                timestamp,
                _trigger_observation_price(stock, plan),
                "价格进入计划入场区",
                "market",
            )

    if fill_price is not None:
        if current.state == STATE_CANDIDATE:
            _transition(
                current,
                STATE_TRIGGERED,
                timestamp,
                fill_price,
                "手工确认触发",
                "manual",
            )
        if current.state != STATE_TRIGGERED:
            raise ValueError("fill can only be recorded for a candidate or triggered setup")
        if fill_price <= 0:
            raise ValueError("fill_price must be positive")
        if fill_shares is not None and fill_shares <= 0:
            raise ValueError("fill_shares must be positive")
        current.entry_at = timestamp
        current.entry_price = round(fill_price, 4)
        current.shares = (
            fill_shares
            if fill_shares is not None
            else current.shares
            if current.shares and current.shares > 0
            else None
        )
        _transition(
            current,
            STATE_HOLDING,
            timestamp,
            fill_price,
            "实际成交确认",
            "manual",
        )
        changed = True

    if current.state == STATE_TRIGGERED and plan and _plan_invalid(plan):
        _close_without_fill(
            current,
            timestamp,
            stock.current_price,
            "触发后策略失效，未成交",
        )
        changed = True

    if exit_price is not None:
        if current.state != STATE_HOLDING:
            raise ValueError("exit can only be recorded for a holding lifecycle")
        if exit_price <= 0:
            raise ValueError("exit_price must be positive")
        _close_holding(
            current,
            timestamp,
            exit_price,
            exit_reason or "手工确认退出",
            "manual",
        )
        changed = True
    elif current.state == STATE_HOLDING:
        automatic_exit = _automatic_exit(current, stock, plan)
        if automatic_exit:
            automatic_reason, automatic_price = automatic_exit
            _close_holding(
                current,
                timestamp,
                automatic_price,
                automatic_reason,
                "market",
            )
            changed = True

    if review_note:
        if current.state != STATE_EXITED:
            raise ValueError("review can only be recorded after exit")
        current.review_at = timestamp
        current.review_note = review_note.strip()
        current.review_grade = review_grade.strip().upper()
        _transition(
            current,
            STATE_REVIEWED,
            timestamp,
            current.exit_price,
            "复盘已封存",
            "manual",
        )
        changed = True

    return current, changed


def _new_lifecycle(
    stock: StockData,
    plan: TradePlan,
    timestamp: str,
    fingerprint: str,
) -> TradeLifecycle:
    lifecycle = TradeLifecycle(
        lifecycle_id=uuid4().hex,
        stock_code=stock.code,
        stock_name=stock.name,
        market=stock.market,
        profile=plan.profile,
        state=STATE_CANDIDATE,
        state_label=STATE_LABELS[STATE_CANDIDATE],
        plan_fingerprint=fingerprint,
        created_at=timestamp,
        updated_at=timestamp,
        action=plan.action,
        trigger_price=plan.trigger_price,
        entry_low=plan.entry_low,
        entry_high=plan.entry_high,
        planned_stop=plan.stop_loss,
        target_1=plan.target_1,
        target_2=plan.target_2,
        shares=plan.shares,
    )
    lifecycle.events.append(
        TradeLifecycleEvent(
            from_state="",
            to_state=STATE_CANDIDATE,
            timestamp=timestamp,
            price=stock.current_price,
            reason="策略与交易计划进入候选",
            source="system",
        )
    )
    return lifecycle


def _refresh_candidate_plan(
    lifecycle: TradeLifecycle,
    plan: TradePlan,
    timestamp: str,
) -> None:
    lifecycle.updated_at = timestamp
    lifecycle.action = plan.action
    lifecycle.plan_fingerprint = _plan_fingerprint_for_code(
        lifecycle.stock_code,
        plan,
    )
    lifecycle.trigger_price = plan.trigger_price
    lifecycle.entry_low = plan.entry_low
    lifecycle.entry_high = plan.entry_high
    lifecycle.planned_stop = plan.stop_loss
    lifecycle.target_1 = plan.target_1
    lifecycle.target_2 = plan.target_2
    lifecycle.shares = plan.shares


def _transition(
    lifecycle: TradeLifecycle,
    to_state: str,
    timestamp: str,
    price: Optional[float],
    reason: str,
    source: str,
) -> None:
    from_state = lifecycle.state
    lifecycle.state = to_state
    lifecycle.state_label = STATE_LABELS[to_state]
    lifecycle.updated_at = timestamp
    if to_state == STATE_TRIGGERED:
        lifecycle.triggered_at = timestamp
        lifecycle.triggered_price = round(price, 4) if price is not None else None
    lifecycle.events.append(
        TradeLifecycleEvent(
            from_state=from_state,
            to_state=to_state,
            timestamp=timestamp,
            price=round(price, 4) if price is not None else None,
            reason=reason,
            source=source,
        )
    )


def _close_without_fill(
    lifecycle: TradeLifecycle,
    timestamp: str,
    price: float,
    reason: str,
) -> None:
    lifecycle.exit_at = timestamp
    lifecycle.exit_price = round(price, 4)
    lifecycle.exit_reason = reason
    _transition(
        lifecycle,
        STATE_EXITED,
        timestamp,
        price,
        reason,
        "system",
    )


def _close_holding(
    lifecycle: TradeLifecycle,
    timestamp: str,
    price: float,
    reason: str,
    source: str,
) -> None:
    lifecycle.exit_at = timestamp
    lifecycle.exit_price = round(price, 4)
    lifecycle.exit_reason = reason
    if lifecycle.entry_price is not None:
        lifecycle.pnl_percent = round(
            (price / lifecycle.entry_price - 1) * 100,
            2,
        )
        if lifecycle.shares:
            lifecycle.pnl_amount = round(
                (price - lifecycle.entry_price) * lifecycle.shares,
                2,
            )
        risk_per_share = (
            lifecycle.entry_price - lifecycle.planned_stop
            if lifecycle.planned_stop is not None
            else 0
        )
        if risk_per_share > 0:
            lifecycle.r_multiple = round(
                (price - lifecycle.entry_price) / risk_per_share,
                2,
            )
    lifecycle.holding_days = _days_between(lifecycle.entry_at, timestamp)
    _transition(
        lifecycle,
        STATE_EXITED,
        timestamp,
        price,
        reason,
        source,
    )


def _automatic_exit(
    lifecycle: TradeLifecycle,
    stock: StockData,
    plan: Optional[TradePlan],
) -> Optional[Tuple[str, float]]:
    if lifecycle.planned_stop is not None and stock.low <= lifecycle.planned_stop:
        price = (
            stock.open_price
            if stock.open_price > 0 and stock.open_price <= lifecycle.planned_stop
            else lifecycle.planned_stop
        )
        return "价格触及或跌破计划止损", price
    if lifecycle.target_2 is not None and stock.high >= lifecycle.target_2:
        price = (
            stock.open_price
            if stock.open_price >= lifecycle.target_2
            else lifecycle.target_2
        )
        return "价格达到第二目标", price
    if plan and _plan_invalid(plan):
        return f"策略状态转为{plan.status_label}", stock.current_price
    return None


def _is_actionable_plan(plan: Optional[TradePlan]) -> bool:
    return bool(
        plan
        and plan.status in {"ready", "wait"}
        and plan.trigger_price is not None
        and plan.entry_low is not None
        and plan.entry_high is not None
        and plan.stop_loss is not None
    )


def _plan_invalid(plan: TradePlan) -> bool:
    return plan.status in {"avoid", "unavailable"}


def _market_triggered(stock: StockData, plan: TradePlan) -> bool:
    if plan.entry_low is None or plan.entry_high is None:
        return False
    return stock.high >= plan.entry_low and stock.low <= plan.entry_high


def _trigger_observation_price(stock: StockData, plan: TradePlan) -> float:
    if plan.entry_low is None or plan.entry_high is None:
        return stock.current_price
    if plan.entry_low <= stock.current_price <= plan.entry_high:
        return stock.current_price
    if plan.entry_low <= stock.open_price <= plan.entry_high:
        return stock.open_price
    if plan.trigger_price is not None:
        return min(max(plan.trigger_price, plan.entry_low), plan.entry_high)
    return plan.entry_low


def _price_key(value: Optional[float]) -> str:
    return "" if value is None else f"{value:.4f}"


def _days_between(start: str, end: str) -> Optional[int]:
    try:
        start_date = datetime.fromisoformat(start).date()
        end_date = datetime.fromisoformat(end).date()
    except (TypeError, ValueError):
        return None
    return max((end_date - start_date).days, 0)

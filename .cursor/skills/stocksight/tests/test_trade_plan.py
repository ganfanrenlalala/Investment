# -*- coding: utf-8 -*-
import unittest

from core import (
    HistoryBar,
    StockHistory,
    StrategyDecision,
    build_trade_plan,
    compute_atr,
    resize_trade_plan,
)
from tests.fixtures import sample_stock


def rising_history(code="600001", count=80):
    bars = []
    price = 10.0
    for index in range(count):
        close = price + 0.10
        bars.append(
            HistoryBar(
                date=f"2025-{(index // 28) + 1:02d}-{(index % 28) + 1:02d}",
                open=price,
                high=close + 0.20,
                low=price - 0.20,
                close=close,
                volume=100000 + index * 1000,
                turnover_rate=3.0,
            )
        )
        price = close
    return StockHistory(code=code, bars=bars)


class TradePlanTests(unittest.TestCase):
    def test_compute_atr_uses_true_range(self):
        history = rising_history(count=20)
        atr = compute_atr(history, period=14)

        self.assertIsNotNone(atr)
        self.assertAlmostEqual(atr, 0.5, places=6)

    def test_build_trade_plan_generates_structural_levels_and_position_size(self):
        history = rising_history()
        last = history.bars[-1]
        stock = sample_stock(
            current_price=last.close,
            prev_close=history.bars[-2].close,
            open_price=last.open,
            high=last.high,
            low=last.low,
            timestamp=f"{last.date} 15:00:00",
            market="sh",
        )
        decision = StrategyDecision(
            action="波段候选",
            tone="healthy",
            summary="",
            profile="swing",
        )

        plan = build_trade_plan(
            stock,
            history,
            decision,
            account_size=100000,
            risk_per_trade_percent=0.5,
            max_position_percent=20,
        )

        self.assertEqual(plan.status, "ready")
        self.assertGreater(plan.trigger_price, 0)
        self.assertLess(plan.stop_loss, plan.trigger_price)
        self.assertGreater(plan.target_1, plan.trigger_price)
        self.assertGreaterEqual(plan.reward_risk_1, 1.5)
        self.assertLessEqual(plan.suggested_position_percent, 20)
        self.assertEqual(plan.shares % 100, 0)
        self.assertLessEqual(
            plan.shares * (plan.trigger_price - plan.stop_loss),
            plan.risk_budget_amount,
        )

    def test_risk_action_disables_new_position(self):
        history = rising_history()
        last = history.bars[-1]
        stock = sample_stock(
            current_price=last.close,
            prev_close=history.bars[-2].close,
            open_price=last.open,
            high=last.high,
            low=last.low,
            timestamp=f"{last.date} 15:00:00",
        )
        decision = StrategyDecision(
            action="触发退出",
            tone="danger",
            summary="",
            profile="swing",
            invalidation="继续下跌。",
        )

        plan = build_trade_plan(stock, history, decision, account_size=100000)

        self.assertEqual(plan.status, "avoid")
        self.assertEqual(plan.suggested_position_percent, 0)
        self.assertEqual(plan.shares, 0)
        self.assertIsNone(plan.target_1)

    def test_risk_avoid_profile_never_creates_attack_position(self):
        history = rising_history()
        last = history.bars[-1]
        stock = sample_stock(
            current_price=last.close,
            prev_close=history.bars[-2].close,
            open_price=last.open,
            high=last.high,
            low=last.low,
            timestamp=f"{last.date} 15:00:00",
        )
        decision = StrategyDecision(
            action="排雷通过",
            tone="healthy",
            summary="",
            profile="risk_avoid",
        )

        plan = build_trade_plan(stock, history, decision, account_size=100000)

        self.assertEqual(plan.status, "avoid")
        self.assertEqual(plan.shares, 0)

    def test_wide_structure_stop_requires_waiting(self):
        history = rising_history()
        for bar in history.bars[-5:]:
            bar.low = bar.close * 0.75
        last = history.bars[-1]
        stock = sample_stock(
            current_price=last.close,
            prev_close=history.bars[-2].close,
            open_price=last.open,
            high=last.high,
            low=last.low,
            timestamp=f"{last.date} 15:00:00",
        )
        decision = StrategyDecision(
            action="波段候选",
            tone="healthy",
            summary="",
            profile="swing",
        )

        plan = build_trade_plan(stock, history, decision, max_stop_percent=8)

        self.assertEqual(plan.status, "wait")
        self.assertEqual(plan.suggested_position_percent, 0)
        self.assertGreater(plan.stop_distance_percent, 8)

    def test_resize_trade_plan_changes_account_sizing_not_price_levels(self):
        history = rising_history()
        last = history.bars[-1]
        stock = sample_stock(
            current_price=last.close,
            prev_close=history.bars[-2].close,
            open_price=last.open,
            high=last.high,
            low=last.low,
            timestamp=f"{last.date} 15:00:00",
        )
        decision = StrategyDecision(
            action="波段候选",
            tone="healthy",
            summary="",
            profile="swing",
        )
        original = build_trade_plan(stock, history, decision)

        resized = resize_trade_plan(original, account_size=200000)

        self.assertEqual(resized.trigger_price, original.trigger_price)
        self.assertEqual(resized.stop_loss, original.stop_loss)
        self.assertEqual(resized.risk_budget_amount, 1000)
        self.assertEqual(resized.shares % 100, 0)


if __name__ == "__main__":
    unittest.main()

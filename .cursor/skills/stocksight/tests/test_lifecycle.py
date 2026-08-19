# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from core import (
    STATE_CANDIDATE,
    STATE_EXITED,
    STATE_HOLDING,
    STATE_REVIEWED,
    STATE_TRIGGERED,
    StockData,
    TradePlan,
    load_lifecycle_ledger,
    save_lifecycle_ledger,
    sync_trade_lifecycle,
)


def _stock(price: float, timestamp: str = "2026-06-11 15:00:00") -> StockData:
    return StockData(
        code="600570",
        name="恒生电子",
        current_price=price,
        prev_close=price,
        open_price=price,
        high=price,
        low=price,
        volume=10000,
        amount=1000,
        volume_ratio=1.2,
        change_percent=0.0,
        turnover_rate=1.0,
        timestamp=timestamp,
        market="sh",
    )


def _plan(
    *,
    trigger: float = 10.0,
    entry_low: float = 10.0,
    entry_high: float = 10.5,
    stop: float = 9.0,
    target_2: float = 13.0,
    status: str = "ready",
) -> TradePlan:
    return TradePlan(
        profile="swing",
        action="进入候选池",
        status=status,
        status_label="条件触发后执行" if status == "ready" else "不新开仓",
        entry_style="突破触发",
        trigger_price=trigger,
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=stop,
        target_1=11.5,
        target_2=target_2,
        suggested_position_percent=10.0 if status == "ready" else 0.0,
        shares=100,
    )


class TradeLifecycleTests(unittest.TestCase):
    def test_candidate_triggers_only_when_price_enters_entry_zone(self):
        records = []
        lifecycle, changed = sync_trade_lifecycle(
            records,
            _stock(9.8),
            _plan(),
            timestamp="2026-06-11 15:00:00",
        )
        self.assertTrue(changed)
        self.assertEqual(lifecycle.state, STATE_CANDIDATE)

        lifecycle, changed = sync_trade_lifecycle(
            records,
            _stock(10.2, "2026-06-12 15:00:00"),
            _plan(),
            timestamp="2026-06-12 15:00:00",
        )
        self.assertTrue(changed)
        self.assertEqual(lifecycle.state, STATE_TRIGGERED)
        self.assertEqual(lifecycle.triggered_price, 10.2)

    def test_intraday_range_triggers_and_gap_stop_uses_open_price(self):
        records = []
        sync_trade_lifecycle(
            records,
            _stock(9.8),
            _plan(),
            timestamp="2026-06-11 15:00:00",
        )
        trigger_day = _stock(9.8, "2026-06-12 15:00:00")
        trigger_day.open_price = 9.9
        trigger_day.high = 10.1
        trigger_day.low = 9.7
        lifecycle, _ = sync_trade_lifecycle(
            records,
            trigger_day,
            _plan(),
            timestamp="2026-06-12 15:00:00",
            fill_price=10.0,
            fill_shares=100,
        )
        self.assertEqual(lifecycle.state, STATE_HOLDING)

        gap_day = _stock(8.7, "2026-06-13 15:00:00")
        gap_day.open_price = 8.5
        gap_day.high = 8.9
        gap_day.low = 8.4
        lifecycle, _ = sync_trade_lifecycle(
            records,
            gap_day,
            _plan(),
            timestamp="2026-06-13 15:00:00",
        )
        self.assertEqual(lifecycle.state, STATE_EXITED)
        self.assertEqual(lifecycle.exit_price, 8.5)

    def test_fill_stop_exit_and_review_complete_the_loop(self):
        records = []
        lifecycle, _ = sync_trade_lifecycle(
            records,
            _stock(10.2),
            _plan(),
            timestamp="2026-06-11 15:00:00",
        )
        self.assertEqual(lifecycle.state, STATE_TRIGGERED)

        lifecycle, _ = sync_trade_lifecycle(
            records,
            _stock(10.2),
            _plan(),
            timestamp="2026-06-11 15:05:00",
            fill_price=10.2,
            fill_shares=100,
        )
        self.assertEqual(lifecycle.state, STATE_HOLDING)
        self.assertEqual(lifecycle.entry_price, 10.2)
        self.assertEqual(lifecycle.shares, 100)

        lifecycle, _ = sync_trade_lifecycle(
            records,
            _stock(8.8, "2026-06-14 15:00:00"),
            _plan(),
            timestamp="2026-06-14 15:00:00",
        )
        self.assertEqual(lifecycle.state, STATE_EXITED)
        self.assertEqual(lifecycle.exit_reason, "价格触及或跌破计划止损")
        self.assertEqual(lifecycle.pnl_amount, -140.0)
        self.assertEqual(lifecycle.pnl_percent, -13.73)
        self.assertEqual(lifecycle.r_multiple, -1.17)
        self.assertEqual(lifecycle.holding_days, 3)

        lifecycle, _ = sync_trade_lifecycle(
            records,
            _stock(8.8, "2026-06-15 15:00:00"),
            _plan(),
            timestamp="2026-06-15 15:00:00",
            review_note="入场后没有等待收盘确认，执行偏急。",
            review_grade="C",
        )
        self.assertEqual(lifecycle.state, STATE_REVIEWED)
        self.assertEqual(lifecycle.review_grade, "C")
        self.assertEqual(len(lifecycle.events), 5)

    def test_candidate_invalidation_exits_without_fake_pnl(self):
        records = []
        lifecycle, _ = sync_trade_lifecycle(
            records,
            _stock(9.8),
            _plan(),
            timestamp="2026-06-11 15:00:00",
        )
        lifecycle, _ = sync_trade_lifecycle(
            records,
            _stock(9.4, "2026-06-12 15:00:00"),
            _plan(status="avoid"),
            timestamp="2026-06-12 15:00:00",
        )
        self.assertEqual(lifecycle.state, STATE_EXITED)
        self.assertIsNone(lifecycle.entry_price)
        self.assertIsNone(lifecycle.pnl_percent)
        self.assertIn("未成交", lifecycle.exit_reason)

    def test_review_requires_exit(self):
        records = []
        sync_trade_lifecycle(
            records,
            _stock(9.8),
            _plan(),
            timestamp="2026-06-11 15:00:00",
        )
        with self.assertRaisesRegex(ValueError, "after exit"):
            sync_trade_lifecycle(
                records,
                _stock(9.8),
                _plan(),
                timestamp="2026-06-11 16:00:00",
                review_note="过早复盘",
            )

    def test_reviewed_setup_starts_new_cycle_only_for_changed_plan(self):
        records = []
        lifecycle, _ = sync_trade_lifecycle(
            records,
            _stock(10.2),
            _plan(),
            timestamp="2026-06-11 15:00:00",
            fill_price=10.2,
            exit_price=10.8,
            review_note="按计划完成。",
            review_grade="A",
        )
        self.assertEqual(lifecycle.state, STATE_REVIEWED)

        same, changed = sync_trade_lifecycle(
            records,
            _stock(10.2, "2026-06-12 15:00:00"),
            _plan(),
            timestamp="2026-06-12 15:00:00",
        )
        self.assertFalse(changed)
        self.assertIs(same, lifecycle)
        self.assertEqual(len(records), 1)

        newer, changed = sync_trade_lifecycle(
            records,
            _stock(10.7, "2026-06-13 15:00:00"),
            _plan(trigger=10.6, entry_low=10.6, entry_high=10.9, stop=9.8),
            timestamp="2026-06-13 15:00:00",
        )
        self.assertTrue(changed)
        self.assertIsNot(newer, lifecycle)
        self.assertEqual(len(records), 2)
        self.assertEqual(newer.state, STATE_TRIGGERED)

    def test_ledger_roundtrip_preserves_nested_events(self):
        records = []
        lifecycle, _ = sync_trade_lifecycle(
            records,
            _stock(10.2),
            _plan(),
            timestamp="2026-06-11 15:00:00",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "trades.json"
            save_lifecycle_ledger(path, records)
            loaded = load_lifecycle_ledger(path)
        self.assertEqual(loaded[0].lifecycle_id, lifecycle.lifecycle_id)
        self.assertEqual(loaded[0].events[0].to_state, STATE_CANDIDATE)
        self.assertEqual(loaded[0].events[-1].to_state, STATE_TRIGGERED)


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
import tempfile
import unittest
from pathlib import Path

from core import (
    BacktestConfig,
    BacktestObservation,
    HistoryBar,
    StrategyDecision,
    StockHistory,
    estimate_strategy_performance,
    render_backtest_markdown,
    run_swing_backtest,
    save_calibration,
)
from core.backtest import build_calibration_artifact, load_calibration


def observation(index, action="波段候选", score=6, result=1.0):
    return BacktestObservation(
        code=f"600{index:03d}",
        signal_date=f"2025-{(index // 28) + 1:02d}-{(index % 28) + 1:02d}",
        entry_date=f"2025-{(index // 28) + 1:02d}-{(index % 28) + 2:02d}",
        action=action,
        tone="healthy",
        score=float(score),
        score_max=8.0,
        entry_price=10.0,
        returns={"5": result, "10": result, "20": result},
        primary_return=result,
        maximum_favorable_excursion=max(result, 0.0) + 1.0,
        maximum_adverse_excursion=min(result, 0.0) - 1.0,
    )


def trend_history(code="600001"):
    bars = []
    price = 10.0
    for index in range(130):
        if index < 65:
            close = 10.0
            volume = 100000
        elif index == 65:
            close = 10.5
            volume = 300000
        else:
            close = price * 1.004
            volume = 150000
        bars.append(
            HistoryBar(
                date=f"2025-{(index // 28) + 1:02d}-{(index % 28) + 1:02d}",
                open=price,
                high=max(price, close) * 1.01,
                low=min(price, close) * 0.99,
                close=close,
                volume=volume,
                turnover_rate=3.0,
            )
        )
        price = close
    return StockHistory(code=code, bars=bars)


class BacktestTests(unittest.TestCase):
    def test_calibration_uses_chronological_holdout_and_can_be_loaded(self):
        items = [
            observation(index, result=2.0 if index % 3 else -1.0)
            for index in range(60)
        ]
        config = BacktestConfig(train_fraction=0.7, minimum_bucket_samples=5)
        artifact = build_calibration_artifact(items, config)

        self.assertEqual(artifact["holdout"]["train_size"], 42)
        self.assertEqual(artifact["holdout"]["test_size"], 18)
        self.assertIsNotNone(artifact["holdout"]["brier_score"])
        self.assertIsNotNone(artifact["holdout"]["baseline_brier_score"])
        self.assertIsNotNone(artifact["holdout"]["brier_skill_score"])

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calibration.json"
            save_calibration(path, artifact)
            restored = load_calibration(path)

        decision = StrategyDecision(
            action="波段候选",
            tone="healthy",
            summary="",
            profile="swing",
            score=6.0,
            score_max=8.0,
            strategy_version="swing-v1",
        )
        performance = estimate_strategy_performance(restored, decision)
        self.assertEqual(performance.sample_size, 60)
        self.assertEqual(performance.match_basis, "动作 + 评分")
        self.assertGreater(performance.probability_positive, 0.5)

    def test_incompatible_strategy_version_is_rejected(self):
        artifact = build_calibration_artifact(
            [observation(index) for index in range(10)],
            BacktestConfig(minimum_bucket_samples=1),
        )
        artifact["strategy_version"] = "swing-v0"
        decision = StrategyDecision(action="波段候选", tone="healthy", summary="")

        with self.assertRaisesRegex(ValueError, "incompatible strategy version"):
            estimate_strategy_performance(artifact, decision)

    def test_unsupported_calibration_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calibration.json"
            path.write_text('{"schema_version": 999}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported calibration schema"):
                load_calibration(path)

    def test_backtest_records_state_transitions_not_every_day(self):
        result = run_swing_backtest(
            {"600001": trend_history()},
            BacktestConfig(minimum_bucket_samples=1),
        )

        self.assertGreater(len(result.observations), 0)
        actions = [item.action for item in result.observations]
        self.assertLess(len(actions), 20)
        self.assertTrue(all(left != right for left, right in zip(actions, actions[1:])))
        self.assertIn("样本外校准", render_backtest_markdown(result))

    def test_backtest_enters_on_next_open_and_deducts_cost(self):
        result = run_swing_backtest(
            {"600001": trend_history()},
            BacktestConfig(total_cost_bps=25.0, minimum_bucket_samples=1),
        )
        item = result.observations[0]
        history = trend_history()
        signal_index = next(
            index for index, bar in enumerate(history.bars)
            if bar.date == item.signal_date
        )
        entry = history.bars[signal_index + 1]
        exit_bar = history.bars[signal_index + 10]
        expected = (exit_bar.close / entry.open - 1 - 0.0025) * 100

        self.assertEqual(item.entry_date, entry.date)
        self.assertAlmostEqual(item.entry_price, entry.open)
        self.assertAlmostEqual(item.primary_return, expected)


if __name__ == "__main__":
    unittest.main()

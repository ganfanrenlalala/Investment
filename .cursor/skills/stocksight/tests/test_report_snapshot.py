# -*- coding: utf-8 -*-
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from core import (
    RSIResult,
    StrategyPerformance,
    TechnicalAnalysis,
    TechnicalSignal,
    TradeLifecycle,
    TradeLifecycleEvent,
    TradePlan,
)
from scripts import report
from tests.fixtures import sample_report


def sample_technical():
    return TechnicalAnalysis(
        rsi=RSIResult(values=[0.0, 72.5], dates=["2026-01-02", "2026-01-03"], period=14),
        signals=[
            TechnicalSignal(
                indicator="RSI",
                signal_type="overbought",
                level=2,
                direction="bearish",
                date="2026-01-03",
                value=72.5,
                description="超买：RSI 高于 70，需警惕追高风险。",
            )
        ],
    )


class ReportSnapshotTests(unittest.TestCase):
    def test_cli_persists_trigger_and_manual_fill_to_lifecycle_ledger(self):
        data = sample_report(
            strategy_profile="swing",
            trade_plan=TradePlan(
                profile="swing",
                action="波段候选",
                status="ready",
                status_label="条件触发后执行",
                entry_style="突破触发",
                trigger_price=10.0,
                entry_low=10.0,
                entry_high=10.3,
                stop_loss=9.4,
                target_1=10.9,
                target_2=11.5,
                suggested_position_percent=8.0,
                shares=100,
            ),
        )
        data.stocks[0].current_price = 10.1
        data.stocks[0].timestamp = "2026-06-11 10:00:00"

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            ledger = base / "trades.json"
            markdown = base / "sample.md"
            with patch.object(
                report,
                "_build_live_report",
                return_value=(data, "detailed", [], []),
            ):
                first_exit = report.main(
                    [
                        "600001",
                        "--mode",
                        "detailed",
                        "--lifecycle-file",
                        str(ledger),
                        "--markdown-out",
                        str(markdown),
                    ]
                )
                second_exit = report.main(
                    [
                        "600001",
                        "--mode",
                        "detailed",
                        "--lifecycle-file",
                        str(ledger),
                        "--fill-price",
                        "10.12",
                        "--fill-shares",
                        "100",
                        "--markdown-out",
                        str(markdown),
                    ]
                )

            records = report.load_lifecycle_ledger(ledger)
            markdown_text = markdown.read_text(encoding="utf-8")

        self.assertEqual(first_exit, 0)
        self.assertEqual(second_exit, 0)
        self.assertEqual(records[-1].state, "holding")
        self.assertEqual(records[-1].entry_price, 10.12)
        self.assertIn("当前状态：**持仓中**", markdown_text)

    def test_snapshot_roundtrip_preserves_report_payload(self):
        data = sample_report(
            technical=sample_technical(),
            source_notes=["实时行情：unit", "历史行情：unit-history（80条）"],
            strategy_profile="mainline",
            strategy_performance=StrategyPerformance(
                profile="swing",
                strategy_version="swing-v1",
                horizon_days=10,
                probability_positive=0.61,
                sample_size=88,
                reliability="中等",
            ),
            trade_plan=TradePlan(
                profile="swing",
                action="波段候选",
                status="ready",
                status_label="条件触发后执行",
                entry_style="突破触发",
                trigger_price=10.2,
                entry_low=10.2,
                entry_high=10.3,
                stop_loss=9.6,
                target_1=11.1,
                target_2=11.7,
                suggested_position_percent=8.0,
            ),
            trade_lifecycle=TradeLifecycle(
                lifecycle_id="life-1",
                stock_code="600001",
                stock_name="Sample",
                market="sh",
                profile="mainline",
                state="holding",
                state_label="持仓中",
                plan_fingerprint="600001|mainline|test",
                created_at="2026-06-10 15:00:00",
                updated_at="2026-06-11 10:00:00",
                entry_at="2026-06-11 10:00:00",
                entry_price=10.2,
                shares=100,
                events=[
                    TradeLifecycleEvent(
                        from_state="triggered",
                        to_state="holding",
                        timestamp="2026-06-11 10:00:00",
                        price=10.2,
                        reason="实际成交确认",
                        source="manual",
                    )
                ],
            ),
        )

        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "sample.json"
            report._save_snapshot(
                snapshot,
                data,
                mode="detailed",
                provider="unit",
                failed=["bad-code"],
                quality_notes=["turnover_rate skipped"],
            )

            restored, meta = report._load_snapshot(snapshot)

        self.assertEqual(restored.title, data.title)
        self.assertEqual(restored.stocks[0].code, data.stocks[0].code)
        self.assertEqual(restored.signals[0].risk_type, data.signals[0].risk_type)
        self.assertEqual(restored.news[0].title, data.news[0].title)
        self.assertIsNotNone(restored.technical)
        self.assertEqual(restored.technical.rsi.latest, 72.5)
        self.assertEqual(restored.technical.signals[0].indicator, "RSI")
        self.assertEqual(restored.source_notes, data.source_notes)
        self.assertEqual(restored.strategy_profile, "mainline")
        self.assertIsNotNone(restored.strategy_performance)
        self.assertEqual(restored.strategy_performance.sample_size, 88)
        self.assertIsNotNone(restored.trade_plan)
        self.assertEqual(restored.trade_plan.trigger_price, 10.2)
        self.assertIsNotNone(restored.trade_lifecycle)
        self.assertEqual(restored.trade_lifecycle.state, "holding")
        self.assertEqual(restored.trade_lifecycle.events[0].to_state, "holding")
        self.assertEqual(restored.snapshot_source, str(snapshot))
        self.assertEqual(meta["mode"], "detailed")
        self.assertEqual(meta["provider"], "unit")
        self.assertEqual(meta["failed_codes"], ["bad-code"])
        self.assertEqual(meta["quality_notes"], ["turnover_rate skipped"])

    def test_cli_renders_from_snapshot_without_codes(self):
        data = sample_report()

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            snapshot = base / "sample.json"
            markdown = base / "sample.md"
            html = base / "sample.html"
            report._save_snapshot(snapshot, data, mode="detailed", provider="unit", failed=[], quality_notes=[])

            exit_code = report.main(
                [
                    "--from-snapshot",
                    str(snapshot),
                    "--markdown-out",
                    str(markdown),
                    "--html",
                    "--out",
                    str(html),
                ]
            )

            self.assertEqual(exit_code, 0)
            markdown_text = markdown.read_text(encoding="utf-8")
            html_text = html.read_text(encoding="utf-8")
            self.assertIn("Sample (600001)", markdown_text)
            self.assertIn("使用 Snapshot", markdown_text)
            self.assertIn(str(snapshot), markdown_text)
            self.assertIn("<!doctype html>", html_text.lower())
            self.assertIn("Snapshot", html_text)

    def test_old_snapshot_without_technical_still_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "old.json"
            report._save_snapshot(snapshot, sample_report(), mode="detailed", provider="unit", failed=[], quality_notes=[])
            payload = json.loads(snapshot.read_text(encoding="utf-8"))
            payload["report"].pop("technical", None)
            payload["report"].pop("source_notes", None)
            snapshot.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            restored, _ = report._load_snapshot(snapshot)

        self.assertIsNone(restored.technical)
        self.assertEqual(restored.source_notes, [])
        self.assertEqual(restored.strategy_profile, "neutral")

    def test_cli_strategy_overrides_snapshot_strategy_for_rendering(self):
        data = sample_report(strategy_profile="neutral")
        data.stocks[0].raw = {"industry": "机器人", "concepts": ["人工智能"]}

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            snapshot = base / "sample.json"
            markdown = base / "sample.md"
            report._save_snapshot(snapshot, data, mode="detailed", provider="unit", failed=[], quality_notes=[])

            exit_code = report.main(
                [
                    "--from-snapshot",
                    str(snapshot),
                    "--strategy",
                    "mainline",
                    "--markdown-out",
                    str(markdown),
                ]
            )

            self.assertEqual(exit_code, 0)
            markdown_text = markdown.read_text(encoding="utf-8")
            self.assertIn("策略视角：A股主线第一波中段趋势策略", markdown_text)

    def test_cli_loads_swing_calibration_into_markdown_and_html(self):
        data = sample_report(strategy_profile="swing")
        calibration = {
            "schema_version": 1,
            "profile": "swing",
            "strategy_version": "swing-v1",
            "generated_at": "2026-06-10 15:00:00",
            "primary_horizon_days": 10,
            "mapping": {
                "minimum_bucket_samples": 1,
                "exact": {},
                "actions": {},
                "scores": {},
                "global": {
                    "sample_size": 50,
                    "probability_positive": 0.62,
                    "mean_return": 2.1,
                    "median_return": 1.4,
                },
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            snapshot = base / "sample.json"
            calibration_path = base / "calibration.json"
            markdown = base / "sample.md"
            html = base / "sample.html"
            report._save_snapshot(snapshot, data, mode="detailed", provider="unit", failed=[], quality_notes=[])
            calibration_path.write_text(json.dumps(calibration, ensure_ascii=False), encoding="utf-8")

            exit_code = report.main(
                [
                    "--from-snapshot",
                    str(snapshot),
                    "--strategy",
                    "swing",
                    "--calibration-file",
                    str(calibration_path),
                    "--markdown-out",
                    str(markdown),
                    "--html",
                    "--out",
                    str(html),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("历史样本外表现", markdown.read_text(encoding="utf-8"))
            self.assertIn("62.0%", markdown.read_text(encoding="utf-8"))
            self.assertIn("历史样本外表现", html.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

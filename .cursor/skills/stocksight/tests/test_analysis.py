# -*- coding: utf-8 -*-
import unittest

from core import HistoryBar, MACDResult, StockHistory, TechnicalAnalysis, TechnicalSignal
from core.analysis import (
    analyze_technical_indicators,
    compute_macd,
    compute_boll,
    compute_kdj,
    compute_rsi,
    detect_boll_signals,
    detect_kdj_signals,
    detect_macd_signals,
    detect_rsi_signals,
    technical_risk_signals,
    _macd_trend_summary,
    _rsi_trend_summary,
    _detect_divergence,
    _build_trend_summary,
)


def history_from_closes(closes):
    return StockHistory(
        code="TEST",
        bars=[
            HistoryBar(
                date=f"2026-01-{index + 1:02d}",
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
                volume=1000 + index,
            )
            for index, close in enumerate(closes)
        ],
    )


def macd_from_dif(dif):
    dates = [f"2026-02-{index + 1:02d}" for index in range(len(dif))]
    return MACDResult(
        dif=list(dif),
        dea=[value * 0.8 for value in dif],
        macd=[value * 0.4 for value in dif],
        dates=dates,
    )


class TechnicalAnalysisTests(unittest.TestCase):

    # ---- Existing tests ----

    def test_compute_macd_returns_series_for_enough_history(self):
        history = history_from_closes([100 + index * 0.5 for index in range(60)])
        macd = compute_macd(history)
        self.assertEqual(len(macd.dif), 60)
        self.assertEqual(len(macd.dea), 60)
        self.assertEqual(len(macd.macd), 60)
        self.assertEqual(macd.dates[-1], "2026-01-60")

    def test_detect_macd_signals_finds_death_cross(self):
        history = history_from_closes(
            [100 + index * 0.8 for index in range(45)] + [136 - index * 1.2 for index in range(20)]
        )
        signals = detect_macd_signals(compute_macd(history), lookback=20)
        self.assertTrue(any(signal.signal_type == "death_cross" for signal in signals))

    def test_rsi_overbought_and_oversold_levels(self):
        overbought = compute_rsi(history_from_closes([100 + index for index in range(35)]))
        oversold = compute_rsi(history_from_closes([140 - index for index in range(35)]))
        overbought_signals = detect_rsi_signals(overbought)
        oversold_signals = detect_rsi_signals(oversold)
        self.assertEqual(overbought_signals[0].level, 3)
        self.assertEqual(overbought_signals[0].signal_type, "overbought_extreme")
        self.assertEqual(oversold_signals[0].level, 2)
        self.assertEqual(oversold_signals[0].signal_type, "oversold_extreme")

    def test_boll_detects_upper_band_risk(self):
        closes = [100.0] * 25 + [130.0]
        history = history_from_closes(closes)
        boll = compute_boll(history)
        signals = detect_boll_signals(boll, history)

        self.assertTrue(signals)
        self.assertEqual(signals[0].indicator, "BOLL")
        self.assertEqual(signals[0].direction, "bearish")

    def test_kdj_detects_overbought_state(self):
        history = history_from_closes([100 + index * 2 for index in range(35)])
        kdj = compute_kdj(history)
        signals = detect_kdj_signals(kdj, lookback=5)

        self.assertTrue(any(signal.indicator == "KDJ" for signal in signals))
        self.assertTrue(any(signal.direction == "bearish" for signal in signals))

    def test_analyze_handles_insufficient_history(self):
        analysis = analyze_technical_indicators(history_from_closes([1, 2, 3]))
        self.assertEqual(analysis.macd.dates, [])
        self.assertIsNone(analysis.rsi.latest)
        self.assertTrue(analysis.notes)

    def test_technical_risk_signals_keeps_bullish_auxiliary_out_of_risk(self):
        analysis = TechnicalAnalysis(signals=[
            TechnicalSignal(
                indicator="MACD",
                signal_type="golden_cross",
                level=0,
                direction="bullish",
                date="2026-01-01",
                value=0.1,
                description="bullish helper",
            ),
            TechnicalSignal(
                indicator="MACD",
                signal_type="bullish_divergence",
                level=1,
                direction="bullish",
                date="2026-01-02",
                value=0.0,
                description="bullish divergence",
            ),
            TechnicalSignal(
                indicator="MACD",
                signal_type="death_cross",
                level=2,
                direction="bearish",
                date="2026-01-03",
                value=-0.1,
                description="bearish risk",
            ),
        ])
        risks = technical_risk_signals(analysis, "TEST")
        self.assertEqual(len(risks), 1)
        self.assertTrue(all(signal.stock_code == "TEST" for signal in risks))
        self.assertEqual(risks[0].risk_type, "MACD技术信号")
        self.assertEqual(risks[0].description, "bearish risk")

    # ---- Trend summary tests ----

    def test_macd_trend_summary_bullish_alignment(self):
        history = history_from_closes([100 + index * 0.8 for index in range(50)])
        macd = compute_macd(history)
        alignment, desc, hist_trend = _macd_trend_summary(macd)
        self.assertEqual(alignment, "bullish")
        self.assertIn("多", desc)

    def test_macd_trend_summary_bearish_alignment(self):
        history = history_from_closes([200 - index * 0.8 for index in range(50)])
        macd = compute_macd(history)
        alignment, desc, hist_trend = _macd_trend_summary(macd)
        self.assertEqual(alignment, "bearish")
        self.assertIn("空", desc)

    def test_macd_trend_summary_insufficient_data_returns_empty(self):
        history = history_from_closes([100 + index for index in range(5)])
        macd = compute_macd(history)
        alignment, desc, hist_trend = _macd_trend_summary(macd)
        self.assertEqual(alignment, "")
        self.assertEqual(hist_trend, "")

    def test_rsi_trend_overbought_pullback(self):
        # Steep rise pushes RSI over 70, short decline keeps extreme in lookback
        closes = [100]
        for i in range(1, 24):
            closes.append(closes[-1] + 2.0)
        for i in range(24, 34):
            closes.append(closes[-1] - 1.5)
        history = history_from_closes(closes)
        rsi = compute_rsi(history)
        trend, desc = _rsi_trend_summary(rsi)
        self.assertEqual(trend, "overbought_pullback")
        self.assertIn("超买", desc)

    def test_rsi_trend_oversold_bounce(self):
        # Steep drop pushes RSI under 30, short rise keeps extreme in lookback
        closes = [150]
        for i in range(1, 24):
            closes.append(closes[-1] - 2.0)
        for i in range(24, 34):
            closes.append(closes[-1] + 1.0)
        history = history_from_closes(closes)
        rsi = compute_rsi(history)
        trend, desc = _rsi_trend_summary(rsi)
        self.assertEqual(trend, "oversold_bounce")
        self.assertIn("超卖", desc)

    def test_analyze_returns_trend_summary(self):
        history = history_from_closes([100 + index * 0.5 for index in range(60)])
        analysis = analyze_technical_indicators(history)
        self.assertIsNotNone(analysis.trend)
        self.assertTrue(len(analysis.trend.macd_alignment) > 0)
        self.assertTrue(len(analysis.trend.rsi_trend_desc) > 0)

    def test_build_trend_summary_returns_valid_object(self):
        history = history_from_closes([100 + index * 0.5 for index in range(60)])
        macd = compute_macd(history)
        rsi = compute_rsi(history)
        trend = _build_trend_summary(macd, rsi, history)
        self.assertIsNotNone(trend)
        self.assertIsInstance(trend.macd_alignment, str)

    def test_macd_trend_summary_turning_detected(self):
        # Price drops then surges: DIF crosses from below to above DEA
        closes = [200]
        for i in range(1, 15):
            closes.append(closes[-1] - 2.0)
        for i in range(15, 60):
            closes.append(closes[-1] + 3.0)
        history = history_from_closes(closes)
        macd = compute_macd(history)
        alignment, desc, hist_trend = _macd_trend_summary(macd)
        self.assertIn(alignment, ("bullish", "turning", "neutral"))

    def test_divergence_bearish(self):
        # Price makes higher high, DIF makes lower high -> bearish divergence
        closes = [10, 12, 10, 9.8, 9.7, 9.8, 9.7, 9.9, 10, 13, 12, 11, 10, 9, 8, 7, 6]
        dif = [0.10, 1.00, 0.30, 0.20, 0.15, 0.80, 0.16, 0.17, 0.19, 0.50, 0.35, 0.25, 0.18, 0.14, 0.12, 0.11, 0.10]
        history = history_from_closes(closes)
        macd = macd_from_dif(dif)
        divergence, desc = _detect_divergence(history, macd)
        self.assertEqual(divergence, "bearish")
        self.assertIn("顶背离", desc)

    def test_divergence_bullish(self):
        # Price makes lower low, DIF makes higher low -> bullish divergence
        closes = [20, 18, 20, 21, 21.2, 21.1, 21.3, 21.4, 20, 17, 18, 19, 20, 21, 22, 23, 24]
        dif = [-0.10, -1.00, -0.40, -0.25, -0.20, -0.80, -0.15, -0.14, -0.20, -0.50, -0.35, -0.25, -0.18, -0.14, -0.12, -0.11, -0.10]
        history = history_from_closes(closes)
        macd = macd_from_dif(dif)
        divergence, desc = _detect_divergence(history, macd)
        self.assertEqual(divergence, "bullish")
        self.assertIn("底背离", desc)


if __name__ == "__main__":
    unittest.main()

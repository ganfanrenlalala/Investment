# -*- coding: utf-8 -*-
import unittest

from core import detect_anomalies, normalize_quote_data

from tests.fixtures import sample_stock


class QualityAndDetectorTests(unittest.TestCase):
    def test_normalize_quote_data_clears_suspicious_optional_fields(self):
        stock = sample_stock(
            volume_ratio=-1.0,
            turnover_rate=678.8,
            volume=-100,
            amount=-1.0,
        )

        normalized, notes = normalize_quote_data([stock])

        self.assertEqual(normalized[0].volume_ratio, 0.0)
        self.assertEqual(normalized[0].turnover_rate, 0.0)
        self.assertEqual(normalized[0].volume, 0)
        self.assertEqual(normalized[0].amount, 0.0)
        self.assertTrue(notes)

    def test_detector_ignores_unavailable_turnover_rate(self):
        stock = sample_stock(volume_ratio=1.0, turnover_rate=0.0, change_percent=1.0)

        signals = detect_anomalies([stock])

        self.assertFalse(
            [signal for signal in signals if "turnover" in signal.risk_type.lower()]
        )

    def test_positive_limit_move_without_overheated_flow_is_warning(self):
        stock = sample_stock(
            change_percent=10.0,
            volume_ratio=1.4,
            turnover_rate=1.4,
        )

        signals = detect_anomalies([stock])
        price_signal = next(sig for sig in signals if sig.risk_type == "超额收益异动")

        self.assertEqual(price_signal.level, 2)
        self.assertIn("强异动观察", price_signal.description)

    def test_positive_limit_move_with_overheated_flow_stays_danger(self):
        stock = sample_stock(
            change_percent=10.0,
            volume_ratio=3.2,
            turnover_rate=1.4,
        )

        signals = detect_anomalies([stock])
        price_signal = next(sig for sig in signals if sig.risk_type == "超额收益异动")

        self.assertEqual(price_signal.level, 3)
        self.assertIn("同步过热", price_signal.description)

    def test_negative_limit_move_stays_danger(self):
        stock = sample_stock(
            change_percent=-10.0,
            volume_ratio=1.0,
            turnover_rate=1.0,
        )

        signals = detect_anomalies([stock])
        price_signal = next(sig for sig in signals if sig.risk_type == "超额收益异动")

        self.assertEqual(price_signal.level, 3)



    def test_detector_thresholds_accepts_old_chinese_field_names(self):
        """Backward compat: Chinese field names still work."""
        from core.detector import DetectorThresholds
        t = DetectorThresholds(
            volume_ratio_关注=9.99,       # simplified watch
            turnover_rate_關注=8.88,      # traditional watch
            excess_return_警告=7.77,       # warn (same in both)
            change_abs_危险=6.66,           # simplified danger
            turnover_rate_pct_危險=5.55,     # traditional danger
        )
        self.assertAlmostEqual(t.volume_ratio_watch, 9.99)
        self.assertAlmostEqual(t.turnover_rate_watch, 8.88)
        self.assertAlmostEqual(t.excess_return_warn, 7.77)
        self.assertAlmostEqual(t.change_abs_danger, 6.66)
        self.assertAlmostEqual(t.turnover_rate_pct_danger, 5.55)

if __name__ == "__main__":
    unittest.main()

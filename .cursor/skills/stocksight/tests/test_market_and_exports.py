# -*- coding: utf-8 -*-
import unittest

from core import (
    detect_market,
    detect_sina_prefix,
    detect_tencent_prefix,
    to_eastmoney_secid,
)
from formatter import render_html_report
from formatter.html import render_html_report as html_render_html_report
from providers import YahooFinanceDataSource
from providers.yahoo import _parse_yahoo_chart


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


def yahoo_payload():
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "symbol": "AAPL",
                        "currency": "USD",
                        "exchangeName": "NMS",
                        "regularMarketPrice": 212.45,
                        "previousClose": 210.0,
                        "regularMarketOpen": 211.0,
                        "regularMarketDayHigh": 213.0,
                        "regularMarketDayLow": 209.5,
                        "regularMarketVolume": 12345678,
                        "regularMarketTime": 1716235200,
                    },
                    "indicators": {
                        "quote": [
                            {
                                "open": [211.0],
                                "high": [213.0],
                                "low": [209.5],
                                "close": [212.45],
                                "volume": [12345678],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


def yahoo_history_payload():
    return {
        "chart": {
            "result": [
                {
                    "timestamp": [1716163200, 1716249600],
                    "indicators": {
                        "quote": [
                            {
                                "open": [210.0, 211.0],
                                "high": [213.0, 214.0],
                                "low": [209.0, 210.0],
                                "close": [212.0, 213.5],
                                "volume": [1000, 1200],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


class MarketAndExportTests(unittest.TestCase):
    def test_market_detection_helpers(self):
        self.assertEqual(detect_market("600001"), "sh")
        self.assertEqual(detect_market("000001"), "sz")
        self.assertEqual(detect_market("00700"), "hk")
        self.assertEqual(detect_market("AAPL"), "us")

        self.assertEqual(detect_tencent_prefix("600001"), "sh")
        self.assertEqual(detect_sina_prefix("AAPL"), "gb_")
        self.assertEqual(to_eastmoney_secid("600001"), "1.600001")

    def test_formatter_html_export_is_stable(self):
        self.assertIs(render_html_report, html_render_html_report)

    def test_yahoo_chart_parser_returns_us_stock_data(self):
        stock = _parse_yahoo_chart(yahoo_payload(), "AAPL")

        self.assertEqual(stock.code, "AAPL")
        self.assertEqual(stock.market, "us")
        self.assertEqual(stock.name, "AAPL")
        self.assertAlmostEqual(stock.current_price, 212.45)
        self.assertAlmostEqual(stock.change_percent, (212.45 - 210.0) / 210.0 * 100)
        self.assertEqual(stock.volume, 12345678)
        self.assertEqual(stock.raw["provider"], "yahoo")

    def test_yahoo_provider_fetch_uses_uppercase_symbol_and_skips_non_us(self):
        provider = YahooFinanceDataSource()
        provider._session = FakeSession(yahoo_payload())

        data, failed = provider.fetch(["aapl", "600001"])

        self.assertIn("aapl", data)
        self.assertIn("600001", failed)
        self.assertIn("/AAPL", provider._session.calls[0][0])

    def test_yahoo_fetch_history_parses_daily_bars(self):
        provider = YahooFinanceDataSource()
        provider._session = FakeSession(yahoo_history_payload())

        history = provider.fetch_history("aapl", days=2)

        self.assertEqual(history.code, "aapl")
        self.assertEqual(len(history.bars), 2)
        self.assertAlmostEqual(history.bars[-1].close, 213.5)
        self.assertIn("/AAPL", provider._session.calls[0][0])

    def test_yahoo_fetch_history_returns_empty_on_http_error(self):
        class ErrorSession:
            def get(self, url, **kwargs):
                response = FakeResponse({})
                response.status_code = 500
                return response

        provider = YahooFinanceDataSource(max_retries=0)
        provider._session = ErrorSession()

        history = provider.fetch_history("AAPL")

        self.assertEqual(history.bars, [])


if __name__ == "__main__":
    unittest.main()

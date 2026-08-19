# -*- coding: utf-8 -*-
import unittest

from providers.tencent import (
    _parse_a_line,
    _parse_hk_line,
    _derive_a_turnover_rate,
    TencentDataSource,
)
from core import DataSourceError


# ---------------------------------------------------------------------------
# Build valid Tencent response lines programmatically (guarantees field count)
# ---------------------------------------------------------------------------

def _build_a_line(code, name, curr, prev, open_p, vol, chg_pct, high, low,
                  amount, vr, tr, float_sh=50000, total_sh=100000):
    """Build a Tencent A-share response line with correct field positions."""
    parts = ["1", name, code, str(curr), str(prev), str(open_p), str(vol)]
    # Fields 7-31: zero placeholders (25 fields)
    parts.extend(["0"] * 25)
    # Field 32: change_percent
    parts.append(str(chg_pct))
    # Field 33-34: high, low
    parts.extend([str(high), str(low)])
    # Fields 35-36: zero
    parts.extend(["0", "0"])
    # Field 37: amount
    parts.append(str(amount))
    # Field 38-39: volume_ratio, turnover_rate
    parts.extend([str(vr), str(tr)])
    # Fields 40-71: zeros (32 fields)
    parts.extend(["0"] * 32)
    # Field 72-73: float_shares, total_shares
    parts.extend([str(float_sh), str(total_sh)])
    return f'v_sh{code}="' + "~".join(parts) + '~";'


def _build_hk_line(code, name, curr, prev, open_p, vol, chg_pct, high, low, amount):
    """Build a Tencent HK response line with correct field positions."""
    parts = ["1", name, code, str(curr), str(prev), str(open_p), str(vol)]
    # Fields 7-31: zero placeholders (25 fields)
    parts.extend(["0"] * 25)
    # Field 32: change_percent
    parts.append(str(chg_pct))
    # Field 33-34: high, low
    parts.extend([str(high), str(low)])
    # Fields 35-36: zero
    parts.extend(["0", "0"])
    # Field 37: amount
    parts.append(str(amount))
    # Remaining fields: zeros
    parts.extend(["0"] * 37)
    return f'v_hk{code}="' + "~".join(parts) + '~";'


A_LINE_VALID = _build_a_line(
    code="600570", name="恒生电子", curr=35.50, prev=34.80, open_p=35.00,
    vol=123456, chg_pct=2.01, high=35.80, low=33.90,
    amount=1000000, vr=1.80, tr=3.20,
)

HK_LINE_VALID = _build_hk_line(
    code="00700", name="腾讯控股", curr=380.00, prev=375.00, open_p=378.00,
    vol=12345678, chg_pct=1.33, high=382.00, low=374.00,
    amount=500000000,
)


class TencentParserTests(unittest.TestCase):
    """Test Tencent response line parsing without network access."""

    def test_parse_a_line_returns_valid_stock_data(self):
        stock = _parse_a_line(A_LINE_VALID, "600570")

        self.assertEqual(stock.code, "600570")
        self.assertEqual(stock.name, "恒生电子")
        self.assertAlmostEqual(stock.current_price, 35.50)
        self.assertAlmostEqual(stock.prev_close, 34.80)
        self.assertAlmostEqual(stock.change_percent, 2.01)
        self.assertEqual(stock.market, "sh")
        self.assertEqual(stock.volume, 12345600)  # 手→股

    def test_parse_a_line_raises_on_short_line(self):
        with self.assertRaises(DataSourceError):
            _parse_a_line("short", "600001")

    def test_parse_a_line_raises_on_missing_separator(self):
        with self.assertRaises(DataSourceError):
            _parse_a_line("v_sh600001=short", "600001")

    def test_parse_hk_line_returns_valid_stock_data(self):
        stock = _parse_hk_line(HK_LINE_VALID, "00700")

        self.assertEqual(stock.code, "00700")
        self.assertAlmostEqual(stock.current_price, 380.00)
        self.assertAlmostEqual(stock.prev_close, 375.00)
        self.assertAlmostEqual(stock.change_percent, 1.33)
        self.assertEqual(stock.market, "hk")
        self.assertEqual(stock.volume, 12345678)
        self.assertEqual(stock.volume_ratio, 0.0)
        self.assertEqual(stock.turnover_rate, 0.0)

    def test_parse_hk_line_raises_on_short_line(self):
        with self.assertRaises(DataSourceError):
            _parse_hk_line("short", "00700")

    def test_derive_turnover_rate_from_float_shares(self):
        fields = [""] * 80
        fields[72] = "100000"
        volume = 50000
        rate, source = _derive_a_turnover_rate(fields, volume, raw_turnover=0.0)

        self.assertAlmostEqual(rate, 50.0)
        self.assertEqual(source, "derived_float_shares")

    def test_derive_turnover_rate_falls_back_to_provider_field(self):
        fields = [""] * 80
        volume = 0
        rate, source = _derive_a_turnover_rate(fields, volume, raw_turnover=3.5)

        self.assertAlmostEqual(rate, 3.5)
        self.assertEqual(source, "provider_field")

    def test_derive_turnover_rate_returns_untrusted_when_overflow(self):
        fields = [""] * 80
        volume = 500000
        rate, source = _derive_a_turnover_rate(fields, volume, raw_turnover=500.0)

        self.assertAlmostEqual(rate, 500.0)
        self.assertEqual(source, "provider_field_untrusted")


class TencentDataSourceTests(unittest.TestCase):
    """Test TencentDataSource with mocked HTTP session."""

    def _make_response(self, resp_text):
        class _FakeResp:
            status_code = 200
            encoding = "gbk"
            def __init__(self):
                self.text = resp_text
        return _FakeResp()

    def test_fetch_parses_multiple_stocks(self):
        class FakeSession:
            def get(self, url, timeout):
                return self._response
        session = FakeSession()
        session._response = self._make_response(
            A_LINE_VALID + "\n" + HK_LINE_VALID
        )

        ds = TencentDataSource()
        ds._session = session

        data, failed = ds.fetch(["600570", "00700"])

        self.assertIn("600570", data)
        self.assertIn("00700", data)
        self.assertEqual(len(failed), 0)
        self.assertAlmostEqual(data["600570"].current_price, 35.50)
        self.assertAlmostEqual(data["00700"].current_price, 380.00)

    def test_fetch_reports_failed_codes_not_in_response(self):
        class FakeSession:
            def get(self, url, timeout):
                return self._response
        session = FakeSession()
        session._response = self._make_response(A_LINE_VALID)

        ds = TencentDataSource()
        ds._session = session

        data, failed = ds.fetch(["600570", "000001"])

        self.assertIn("600570", data)
        self.assertIn("000001", failed)

    def test_fetch_empty_codes_returns_empty(self):
        ds = TencentDataSource()
        data, failed = ds.fetch([])
        self.assertEqual(data, {})
        self.assertEqual(failed, [])

    def test_fetch_skips_us_tickers(self):
        ds = TencentDataSource()
        data, failed = ds.fetch(["TSLA"])
        self.assertEqual(data, {})
        self.assertEqual(failed, ["TSLA"])

    def test_provider_name_is_chinese(self):
        self.assertEqual(TencentDataSource().name(), "腾讯财经")


# ---------------------------------------------------------------------------
# Sina provider tests
# ---------------------------------------------------------------------------

SINA_A_RESPONSE = 'var hq_str_sh600570="恒生电子,35.00,34.80,35.50,35.80,33.90,35.50,35.51,123456,12345678,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0";'
SINA_HK_RESPONSE = 'var hq_str_hk00700="TENCENT,腾讯控股,378.00,375.00,382.00,374.00,380.00,5.00,1.33,0,0,500000000,12345678,2025/01/01,0,0";'
SINA_US_RESPONSE = 'var hq_str_gb_aapl="Apple Inc.,212.45,1.17,0,212.00,213.00,209.50,210.00,0,0,12345678,0,1234567890,0,0,0,0,0,0,0,0";'

from providers.sina import (
    _parse_sina_response_line,
    _parse_a_fields,
    _parse_hk_fields,
    _parse_us_fields,
    SinaDataSource,
)


class SinaParserTests(unittest.TestCase):
    def test_parse_sina_response_line_extracts_fields(self):
        fields = _parse_sina_response_line(SINA_A_RESPONSE)
        self.assertIsNotNone(fields)
        self.assertEqual(fields[0], "恒生电子")

    def test_parse_sina_response_line_returns_none_on_bad_line(self):
        self.assertIsNone(_parse_sina_response_line("no quotes here"))

    def test_parse_a_fields_returns_valid_stock_data(self):
        fields = _parse_sina_response_line(SINA_A_RESPONSE)
        stock = _parse_a_fields(fields, "600570", "2026-01-01 15:00:00")

        self.assertEqual(stock.code, "600570")
        self.assertEqual(stock.name, "恒生电子")
        self.assertAlmostEqual(stock.current_price, 35.50)
        self.assertAlmostEqual(stock.prev_close, 34.80)
        self.assertEqual(stock.market, "sh")
        self.assertEqual(stock.volume_ratio, 0.0)
        self.assertEqual(stock.turnover_rate, 0.0)

    def test_parse_hk_fields_returns_valid_stock_data(self):
        fields = _parse_sina_response_line(SINA_HK_RESPONSE)
        stock = _parse_hk_fields(fields, "00700", "2026-01-01 16:00:00")

        self.assertEqual(stock.code, "00700")
        self.assertEqual(stock.name, "腾讯控股")
        self.assertAlmostEqual(stock.current_price, 380.00)
        self.assertAlmostEqual(stock.change_percent, 1.33)
        self.assertEqual(stock.market, "hk")

    def test_parse_us_fields_returns_valid_stock_data(self):
        fields = _parse_sina_response_line(SINA_US_RESPONSE)
        stock = _parse_us_fields(fields, "AAPL", "2026-01-01 16:00:00")

        self.assertEqual(stock.code, "AAPL")
        self.assertEqual(stock.name, "Apple Inc.")
        self.assertAlmostEqual(stock.current_price, 212.45)
        self.assertEqual(stock.market, "us")

    def test_parse_a_fields_handles_empty_fields_gracefully(self):
        fields = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        stock = _parse_a_fields(fields, "600001", "2026-01-01")
        self.assertEqual(stock.code, "600001")
        self.assertAlmostEqual(stock.current_price, 0.0)


# ---------------------------------------------------------------------------
# EastMoney provider tests
# ---------------------------------------------------------------------------

from providers.eastmoney import EastMoneyDataSource
from providers.akshare_provider import AkShareDataSource
from providers.ashare_history import AShareHistoryDataSource, _market_symbol
from core.market import to_eastmoney_secid


EASTMONEY_STOCK_RESPONSE = {
    "rc": 0,
    "data": {
        "f43": 3550,
        "f44": 3580,
        "f45": 3390,
        "f46": 3500,
        "f47": 123456,
        "f48": 12345678,
        "f50": 180,
        "f57": "600570",
        "f58": "恒生电子",
        "f60": 3480,
        "f127": "软件开发",
        "f129": "人工智能,区块链,金融科技",
        "f167": 320,
        "f170": 201,
    },
}

EASTMONEY_HISTORY_RESPONSE = {
    "rc": 0,
    "data": {
        "klines": [
            "2026-01-01,10.00,10.50,10.80,9.90,1000,2000000,0,5.00,0.50,2.30",
            "2026-01-02,10.50,10.80,11.00,10.40,1200,2500000,0,2.86,0.30,2.60",
        ]
    },
}

EASTMONEY_SECTOR_RESPONSE = {
    "rc": 0,
    "data": {
        "diff": [
            {
                "f12": "BK1234",
                "f14": "机器人",
                "f2": 1234.5,
                "f3": 3.21,
                "f4": 38.2,
                "f8": 2.5,
                "f20": 100000000,
                "f62": 1200000,
                "f104": 42,
                "f105": 8,
                "f128": "强势股份",
                "f136": 8.6,
            }
        ]
    },
}


class EastMoneyParserTests(unittest.TestCase):
    def test_to_secid_shanghai(self):
        self.assertEqual(to_eastmoney_secid("600570"), "1.600570")

    def test_to_secid_shenzhen(self):
        self.assertEqual(to_eastmoney_secid("000001"), "0.000001")
        self.assertEqual(to_eastmoney_secid("002346"), "0.002346")

    def test_to_secid_returns_none_for_hk(self):
        self.assertIsNone(to_eastmoney_secid("00700"))

    def test_to_secid_returns_none_for_us(self):
        self.assertIsNone(to_eastmoney_secid("AAPL"))

    def test_fetch_single_parses_stock_data(self):
        class FakeSession:
            def get(self, url, params, headers, timeout):
                class FakeResp:
                    encoding = "utf-8"
                    @staticmethod
                    def json():
                        return EASTMONEY_STOCK_RESPONSE
                return FakeResp()

        ds = EastMoneyDataSource()
        ds._session = FakeSession()

        stock = ds._fetch_single("600570", "1.600570", "2026-01-01 15:00:00")

        self.assertEqual(stock.code, "600570")
        self.assertEqual(stock.name, "恒生电子")
        self.assertAlmostEqual(stock.current_price, 35.50)
        self.assertAlmostEqual(stock.change_percent, 2.01)
        self.assertAlmostEqual(stock.volume_ratio, 1.80)
        self.assertAlmostEqual(stock.turnover_rate, 3.20)
        self.assertEqual(stock.market, "sh")
        self.assertEqual(stock.volume, 12345600)

    def test_fetch_single_returns_none_on_error(self):
        class FakeSession:
            def get(self, url, params, headers, timeout):
                raise Exception("network error")

        ds = EastMoneyDataSource()
        ds._session = FakeSession()

        stock = ds._fetch_single("600570", "1.600570", "2026-01-01")
        self.assertIsNone(stock)

    def test_fetch_skips_non_a_share_codes(self):
        ds = EastMoneyDataSource()
        data, failed = ds.fetch(["AAPL", "00700"])

        self.assertEqual(data, {})
        self.assertIn("AAPL", failed)
        self.assertIn("00700", failed)

    def test_provider_name_is_chinese(self):
        self.assertEqual(EastMoneyDataSource().name(), "东方财富")

    def test_fetch_history_parses_kline_bars(self):
        class FakeSession:
            def get(self, url, params, headers, timeout):
                class FakeResp:
                    @staticmethod
                    def json():
                        return EASTMONEY_HISTORY_RESPONSE
                return FakeResp()

        ds = EastMoneyDataSource()
        ds._session = FakeSession()

        history = ds.fetch_history("600570", days=2)

        self.assertEqual(history.code, "600570")
        self.assertEqual(len(history.bars), 2)
        self.assertEqual(history.bars[0].date, "2026-01-01")
        self.assertAlmostEqual(history.bars[-1].close, 10.80)
        self.assertAlmostEqual(history.bars[-1].amount, 250.0)
        self.assertAlmostEqual(history.bars[-1].change_percent, 2.86)
        self.assertAlmostEqual(history.bars[-1].turnover_rate, 2.60)

    def test_get_sector_list_parses_radar_fields(self):
        calls = []

        class FakeSession:
            def get(self, url, params, headers, timeout):
                calls.append(params)

                class FakeResp:
                    @staticmethod
                    def json():
                        return EASTMONEY_SECTOR_RESPONSE
                return FakeResp()

        ds = EastMoneyDataSource()
        ds._session = FakeSession()

        sectors = ds.get_sector_list(board_type="concept")

        self.assertEqual(calls[0]["fs"], "m:90+t:3+f:!50")
        self.assertEqual(sectors[0]["code"], "BK1234")
        self.assertEqual(sectors[0]["name"], "机器人")
        self.assertEqual(sectors[0]["board_type"], "concept")
        self.assertAlmostEqual(sectors[0]["change"], 3.21)
        self.assertEqual(sectors[0]["up_count"], 42)
        self.assertEqual(sectors[0]["leader"], "强势股份")


# ---------------------------------------------------------------------------
# AkShare optional provider tests
# ---------------------------------------------------------------------------

class _FakeFrame:
    def __init__(self, rows):
        self._rows = rows

    def to_dict(self, orient):
        self.assert_orient = orient
        return self._rows


class _FakeAkShare:
    @staticmethod
    def stock_zh_a_spot_em():
        return _FakeFrame([
            {
                "代码": "600570",
                "名称": "恒生电子",
                "最新价": 35.50,
                "昨收": 34.80,
                "今开": 35.00,
                "最高": 35.80,
                "最低": 33.90,
                "成交量": 12345600,
                "成交额": 438000000,
                "量比": 1.8,
                "涨跌幅": 2.01,
                "换手率": 3.2,
                "总市值": 1000000000,
                "流通市值": 800000000,
                "市盈率-动态": 28.5,
                "市净率": 4.2,
            }
        ])

    @staticmethod
    def stock_zh_a_hist(symbol, period, start_date, end_date, adjust):
        return _FakeFrame([
            {"日期": "2026-01-01", "开盘": 10.0, "收盘": 10.5, "最高": 10.8, "最低": 9.9, "成交量": 1000},
            {"日期": "2026-01-02", "开盘": 10.5, "收盘": 10.8, "最高": 11.0, "最低": 10.4, "成交量": 1200},
        ])


class AkShareProviderTests(unittest.TestCase):
    def test_fetch_parses_a_share_spot_frame(self):
        ds = AkShareDataSource(ak_module=_FakeAkShare)

        data, failed = ds.fetch(["600570", "AAPL"])

        self.assertIn("600570", data)
        self.assertIn("AAPL", failed)
        stock = data["600570"]
        self.assertEqual(stock.name, "恒生电子")
        self.assertAlmostEqual(stock.current_price, 35.50)
        self.assertAlmostEqual(stock.change_percent, 2.01)
        self.assertEqual(stock.market, "sh")
        self.assertEqual(stock.raw["provider"], "akshare")
        self.assertEqual(stock.raw["source_api"], "stock_zh_a_spot_em")

    def test_fetch_history_parses_daily_bars(self):
        ds = AkShareDataSource(ak_module=_FakeAkShare)

        history = ds.fetch_history("600570", days=2)

        self.assertEqual(history.code, "600570")
        self.assertEqual(len(history.bars), 2)
        self.assertEqual(history.bars[0].date, "2026-01-01")
        self.assertAlmostEqual(history.bars[-1].close, 10.80)

    def test_fetch_raises_data_source_error_when_package_missing(self):
        ds = AkShareDataSource()

        try:
            import akshare  # noqa: F401
        except ImportError:
            with self.assertRaises(DataSourceError):
                ds.fetch(["600570"])

    def test_fetch_history_returns_empty_when_package_missing(self):
        ds = AkShareDataSource()

        try:
            import akshare  # noqa: F401
        except ImportError:
            history = ds.fetch_history("600570", days=2)
            self.assertEqual(history.code, "600570")
            self.assertEqual(history.bars, [])


# ---------------------------------------------------------------------------
# A-share fallback history provider tests
# ---------------------------------------------------------------------------

SINA_HISTORY_ROWS = [
    {"day": "2026-01-01", "open": "10.00", "high": "10.80", "low": "9.90", "close": "10.50", "volume": "1000"},
    {"day": "2026-01-02", "open": "10.50", "high": "11.00", "low": "10.40", "close": "10.80", "volume": "1200"},
]

TENCENT_HISTORY_PAYLOAD = {
    "data": {
        "sz002346": {
            "qfqday": [
                ["2026-01-01", "10.00", "10.50", "10.80", "9.90", "1000"],
                ["2026-01-02", "10.50", "10.80", "11.00", "10.40", "1200"],
            ]
        }
    }
}


class AShareHistoryDataSourceTests(unittest.TestCase):
    def test_market_symbol_derives_exchange_prefix(self):
        self.assertEqual(_market_symbol("600570"), "sh600570")
        self.assertEqual(_market_symbol("002346"), "sz002346")
        self.assertEqual(_market_symbol("sz002346"), "sz002346")
        self.assertIsNone(_market_symbol("AAPL"))

    def test_fetch_history_parses_sina_rows(self):
        class FakeSession:
            def get(self, url, params, headers, timeout):
                class FakeResp:
                    @staticmethod
                    def json():
                        return SINA_HISTORY_ROWS
                return FakeResp()

        ds = AShareHistoryDataSource()
        ds._session = FakeSession()

        history = ds.fetch_history("600570", days=2)

        self.assertEqual(history.code, "600570")
        self.assertEqual(len(history.bars), 2)
        self.assertEqual(history.bars[0].date, "2026-01-01")
        self.assertAlmostEqual(history.bars[-1].close, 10.80)

    def test_fetch_history_falls_back_to_tencent_rows(self):
        class FakeSession:
            def __init__(self):
                self.calls = 0

            def get(self, url, params, headers, timeout):
                self.calls += 1

                class FakeResp:
                    def __init__(self, payload):
                        self._payload = payload

                    def json(self):
                        return self._payload

                if self.calls == 1:
                    return FakeResp([])
                return FakeResp(TENCENT_HISTORY_PAYLOAD)

        ds = AShareHistoryDataSource()
        ds._session = FakeSession()

        history = ds.fetch_history("002346", days=2)

        self.assertEqual(history.code, "002346")
        self.assertEqual(len(history.bars), 2)
        self.assertEqual(history.bars[0].date, "2026-01-01")
        self.assertAlmostEqual(history.bars[-1].high, 11.00)

    def test_fetch_history_returns_empty_for_invalid_code(self):
        ds = AShareHistoryDataSource()
        history = ds.fetch_history("AAPL", days=2)

        self.assertEqual(history.code, "AAPL")
        self.assertEqual(history.bars, [])


if __name__ == "__main__":
    unittest.main()

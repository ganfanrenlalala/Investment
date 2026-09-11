# -*- coding: utf-8 -*-
import unittest

from router import KLINE_ANALYSIS, KLINE_CHART, parse_query


class RouterTests(unittest.TestCase):
    def test_kline_chart_is_not_captured_by_generic_kline_route(self):
        self.assertEqual(parse_query("茅台K线图").intent, KLINE_CHART)
        self.assertEqual(parse_query("茅台近30日K线").intent, KLINE_ANALYSIS)


if __name__ == "__main__":
    unittest.main()

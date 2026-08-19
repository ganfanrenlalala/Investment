# -*- coding: utf-8 -*-

import unittest

from core.mainline_radar import (
    SectorRadarInput,
    evaluate_sector_radar,
    evaluate_sector_rows,
    render_mainline_radar_markdown,
    sector_from_mapping,
)


class MainlineRadarTests(unittest.TestCase):
    def test_evaluate_strong_sector_returns_tracking_radar_not_final_score(self):
        sector = SectorRadarInput(
            code="BK0999",
            name="机器人",
            board_type="concept",
            change_percent=3.8,
            turnover_rate=3.2,
            up_count=42,
            down_count=10,
            leader="强势股份",
            leader_change_percent=8.6,
            main_net_inflow=120000000,
        )

        result = evaluate_sector_radar(sector, market_change=0.5)

        self.assertGreaterEqual(result.radar_score, 7)
        self.assertEqual(result.status, "强势雷达")
        self.assertTrue(any("今日明显强于大盘" in item for item in result.auto_hits))
        self.assertTrue(any("60 日涨幅" in item for item in result.pending_checks))

    def test_unknown_inputs_stay_pending_instead_of_zero(self):
        sector = SectorRadarInput(
            code="BK0001",
            name="低空经济",
            change_percent=2.2,
            leader="样本股",
            leader_change_percent=5.5,
        )

        result = evaluate_sector_radar(sector, market_change=0.0)

        self.assertIn("缺少上涨/下跌家数，同步性待确认", result.warnings)
        self.assertGreater(len(result.pending_checks), 5)

    def test_sector_from_mapping_accepts_eastmoney_style_fields(self):
        sector = sector_from_mapping({
            "code": "BK1234",
            "name": "光模块CPO",
            "board_type": "concept",
            "change": "2.5",
            "turnover_rate": "4.2",
            "up_count": "18",
            "down_count": "3",
            "leader": "中际旭创",
            "leader_change": "7.8",
            "main_net_inflow": "100",
        })

        self.assertEqual(sector.code, "BK1234")
        self.assertEqual(sector.board_type, "concept")
        self.assertAlmostEqual(sector.change_percent, 2.5)
        self.assertEqual(sector.up_count, 18)
        self.assertAlmostEqual(sector.leader_change_percent, 7.8)

    def test_evaluate_sector_rows_sorts_by_radar_score(self):
        rows = [
            {"code": "BK1", "name": "弱方向", "change": -1.0, "up_count": 2, "down_count": 20},
            {
                "code": "BK2",
                "name": "强方向",
                "change": 4.0,
                "up_count": 30,
                "down_count": 5,
                "leader_change": 9.0,
                "main_net_inflow": 1,
                "turnover_rate": 3.0,
            },
        ]

        results = evaluate_sector_rows(rows, market_change=0.0)

        self.assertEqual(results[0].sector.name, "强方向")
        self.assertGreater(results[0].radar_score, results[1].radar_score)

    def test_render_markdown_marks_pending_checks(self):
        result = evaluate_sector_radar(SectorRadarInput(
            code="BK2",
            name="强方向",
            change_percent=4.0,
            up_count=30,
            down_count=5,
            leader_change_percent=9.0,
            main_net_inflow=1,
            turnover_rate=3.0,
        ))

        markdown = render_mainline_radar_markdown([result])

        self.assertIn("自动雷达分只用于发现方向", markdown)
        self.assertIn("10项主线评分待确认", markdown)
        self.assertIn("- [ ]", markdown)


if __name__ == "__main__":
    unittest.main()

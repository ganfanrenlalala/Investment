# -*- coding: utf-8 -*-
import unittest

from core import (
    BOLLResult,
    KDJResult,
    MACDResult,
    NewsItem,
    RSIResult,
    TechnicalAnalysis,
    TrendSummary,
    evaluate_strategy_action,
    evaluate_strategy_separation,
)

from tests.fixtures import sample_signal, sample_stock


def technical_context(
    *,
    macd_alignment="neutral",
    histogram="flat",
    rsi=55.0,
    rsi_trend="neutral",
    divergence="",
    boll_latest=None,
    kdj_j=50.0,
):
    return TechnicalAnalysis(
        macd=MACDResult(dif=[0.1, 0.2, 0.3], dea=[0.0, 0.1, 0.2], macd=[0.1, 0.2, 0.3]),
        rsi=RSIResult(values=[rsi], dates=["2026-05-20"]),
        boll=BOLLResult(
            upper=[boll_latest[0]] if boll_latest else [],
            middle=[boll_latest[1]] if boll_latest else [],
            lower=[boll_latest[2]] if boll_latest else [],
        ),
        kdj=KDJResult(k=[50.0], d=[45.0], j=[kdj_j]),
        trend=TrendSummary(
            macd_alignment=macd_alignment,
            macd_alignment_desc=f"MACD {macd_alignment}",
            macd_histogram_trend=histogram,
            rsi_trend=rsi_trend,
            rsi_trend_desc=f"RSI {rsi_trend}",
            divergence=divergence,
            divergence_desc="价格创新高但 MACD 未确认，顶背离风险" if divergence else "",
        ),
    )


class StrategyTests(unittest.TestCase):
    def test_hard_news_risk_overrides_technical_setup(self):
        stock = sample_stock(code="002346", name="柘中股份", change_percent=3.2, volume_ratio=2.2)
        decision = evaluate_strategy_action(
            stock,
            [],
            technical_context(macd_alignment="bullish", rsi=58.0),
            [NewsItem(title="柘中股份收到监管问询函", source="公告", published_at="2026-05-18")],
        )

        self.assertEqual(decision.action, "风险规避")
        self.assertEqual(decision.tone, "danger")

    def test_old_hard_news_does_not_override_current_technical_setup(self):
        stock = sample_stock(
            code="002346",
            name="柘中股份",
            change_percent=1.2,
            volume_ratio=1.2,
            turnover_rate=3.0,
            timestamp="2026-05-28 10:00:00",
        )
        old_news = NewsItem(
            title="柘中股份重大事项停牌进展公告",
            source="巨潮资讯",
            published_at="2015-04-29",
            snippet="[风险提示] 重大事项存在不确定性，提醒投资者注意风险。",
        )

        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=1, description="偏热但未超买")],
            technical_context(macd_alignment="bullish", rsi=56.0),
            [old_news],
        )

        self.assertEqual(decision.action, "趋势持有")

    def test_unrelated_hard_news_does_not_cross_contaminate_strategy(self):
        stock = sample_stock(code="002346", name="柘中股份", change_percent=1.2, volume_ratio=1.2)
        unrelated_news = NewsItem(
            title="其他股份收到监管处罚",
            source="公告",
            published_at="2026-05-18",
            snippet="[风险提示] 其他股份存在退市风险。",
        )

        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=1, description="偏热但未超买")],
            technical_context(macd_alignment="bullish", rsi=56.0),
            [unrelated_news],
        )

        self.assertEqual(decision.action, "趋势持有")

    def test_undated_hard_news_is_report_context_only(self):
        stock = sample_stock(code="002346", name="柘中股份", change_percent=1.2, volume_ratio=1.2)
        undated_news = NewsItem(
            title="柘中股份风险提示公告",
            source="搜索结果",
            snippet="[风险提示] 未给出发布时间的历史搜索结果。",
        )

        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=1, description="偏热但未超买")],
            technical_context(macd_alignment="bullish", rsi=56.0),
            [undated_news],
        )

        self.assertEqual(decision.action, "趋势持有")

    def test_volume_breakout_with_bullish_macd_needs_confirmation(self):
        stock = sample_stock(change_percent=3.4, volume_ratio=2.1, turnover_rate=6.0)
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="量比偏离", level=2, description="量比放大")],
            technical_context(macd_alignment="bullish", rsi=62.0),
        )

        self.assertEqual(decision.action, "突破确认")
        self.assertIn("放量上涨", decision.summary)

    def test_bullish_trend_without_major_risk_is_trend_hold(self):
        stock = sample_stock(change_percent=1.2, volume_ratio=1.2, turnover_rate=3.0)
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=1, description="偏热但未超买")],
            technical_context(macd_alignment="bullish", rsi=56.0),
        )

        self.assertEqual(decision.action, "趋势持有")
        self.assertEqual(decision.tone, "healthy")

    def test_overheated_signal_cools_down_before_breakout(self):
        stock = sample_stock(change_percent=4.0, volume_ratio=2.2, turnover_rate=12.0)
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=2, description="RSI 超买")],
            technical_context(macd_alignment="bullish", rsi=78.0),
        )

        self.assertEqual(decision.action, "高位降温")
        self.assertEqual(decision.tone, "warning")

    def test_oversold_without_downside_event_is_low_repair(self):
        stock = sample_stock(change_percent=-0.8, volume_ratio=0.9, turnover_rate=2.0)
        decision = evaluate_strategy_action(
            stock,
            [],
            technical_context(macd_alignment="neutral", rsi=28.0, rsi_trend="oversold_bounce"),
        )

        self.assertEqual(decision.action, "低位修复")
        self.assertIn("修复", decision.summary)

    def test_mainline_hard_news_is_not_suitable(self):
        stock = sample_stock(code="002346", name="某中股份", change_percent=3.2, volume_ratio=2.2)
        decision = evaluate_strategy_action(
            stock,
            [],
            technical_context(macd_alignment="bullish", rsi=58.0),
            [NewsItem(title="某中股份收到监管问询函", source="公告", published_at="2026-05-18")],
            profile="mainline",
        )

        self.assertEqual(decision.action, "不适合参与")
        self.assertEqual(decision.profile, "mainline")
        self.assertIn("A股主线第一波中段趋势策略", decision.profile_label)

    def test_mainline_volume_breakout_can_small_trial(self):
        stock = sample_stock(
            change_percent=3.4,
            volume_ratio=2.1,
            turnover_rate=6.0,
            raw={"industry": "机器人", "concepts": ["人工智能", "高端制造"]},
        )
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="量比偏离", level=2, description="量比放大")],
            technical_context(macd_alignment="bullish", rsi=62.0, boll_latest=(12.0, 10.0, 8.0)),
            profile="mainline",
        )

        self.assertEqual(decision.action, "可小仓试错")
        self.assertIn("主线适配度评分", "；".join(decision.basis))
        self.assertIn("首笔试仓", decision.position_note)

    def test_mainline_overheated_signal_reduces_before_chasing(self):
        stock = sample_stock(
            change_percent=4.0,
            volume_ratio=2.2,
            turnover_rate=12.0,
            raw={"industry": "机器人"},
        )
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=2, description="RSI 超买")],
            technical_context(macd_alignment="bullish", rsi=78.0),
            profile="mainline",
        )

        self.assertEqual(decision.action, "触发减仓")
        self.assertEqual(decision.tone, "warning")

    def test_mainline_downside_break_triggers_exit(self):
        stock = sample_stock(
            change_percent=-4.2,
            volume_ratio=2.0,
            turnover_rate=8.0,
            raw={"industry": "机器人"},
        )
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="价格异动", level=2, description="放量下跌并跌回平台")],
            technical_context(macd_alignment="bearish", rsi=42.0),
            profile="mainline",
        )

        self.assertEqual(decision.action, "触发退出")
        self.assertEqual(decision.tone, "danger")

    def test_risk_avoid_st_name_fails_screening(self):
        stock = sample_stock(name="ST得润", change_percent=2.0, volume_ratio=1.4)
        decision = evaluate_strategy_action(
            stock,
            [],
            technical_context(macd_alignment="bullish", rsi=55.0),
            profile="risk_avoid",
        )

        self.assertEqual(decision.action, "排雷未通过")
        self.assertEqual(decision.profile, "risk_avoid")
        self.assertIn("风险排雷视角", decision.profile_label)

    def test_risk_avoid_hard_news_is_not_suitable(self):
        stock = sample_stock(code="002346", name="得润电子", change_percent=3.0, volume_ratio=1.8)
        decision = evaluate_strategy_action(
            stock,
            [],
            technical_context(macd_alignment="bullish", rsi=58.0),
            [NewsItem(title="得润电子收到监管问询函", source="公告", published_at="2026-05-18")],
            profile="risk_avoid",
        )

        self.assertEqual(decision.action, "不适合参与")
        self.assertEqual(decision.tone, "danger")

    def test_risk_avoid_clean_setup_passes_screening(self):
        stock = sample_stock(change_percent=1.0, volume_ratio=1.1, turnover_rate=3.0)
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=1, description="温和趋势")],
            technical_context(macd_alignment="bullish", rsi=56.0, boll_latest=(12.0, 10.0, 8.0), kdj_j=54.0),
            profile="risk_avoid",
        )

        self.assertEqual(decision.action, "排雷通过")
        self.assertEqual(decision.tone, "healthy")

    def test_swing_volume_breakout_becomes_candidate(self):
        stock = sample_stock(change_percent=3.4, volume_ratio=2.1, turnover_rate=6.0)
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="量比偏离", level=2, description="量比放大")],
            technical_context(macd_alignment="bullish", rsi=62.0, boll_latest=(12.0, 10.0, 8.0), kdj_j=64.0),
            profile="swing",
        )

        self.assertEqual(decision.action, "波段候选")
        self.assertEqual(decision.score, 8.0)
        self.assertEqual(decision.score_max, 8.0)
        self.assertEqual(decision.strategy_version, "swing-v1")
        self.assertEqual(decision.profile, "swing")
        self.assertIn("波段趋势视角", decision.profile_label)

    def test_swing_overheated_signal_cools_down(self):
        stock = sample_stock(change_percent=4.0, volume_ratio=2.2, turnover_rate=12.0)
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=2, description="RSI 超买")],
            technical_context(macd_alignment="bullish", rsi=78.0, kdj_j=104.0),
            profile="swing",
        )

        self.assertEqual(decision.action, "高位降温")
        self.assertEqual(decision.tone, "warning")

    def test_swing_downside_break_triggers_exit(self):
        stock = sample_stock(change_percent=-4.2, volume_ratio=2.0, turnover_rate=8.0)
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="价格异动", level=2, description="放量下跌并破位")],
            technical_context(macd_alignment="bearish", rsi=42.0, boll_latest=(12.0, 10.0, 8.0)),
            profile="swing",
        )

        self.assertEqual(decision.action, "触发退出")
        self.assertEqual(decision.tone, "danger")

    def test_strategy_separation_keeps_mainline_and_swing_scores_apart(self):
        stock = sample_stock(
            change_percent=3.4,
            volume_ratio=2.1,
            turnover_rate=6.0,
            raw={"industry": "机器人", "concepts": ["人工智能", "高端制造"]},
        )
        separation = evaluate_strategy_separation(
            stock,
            [sample_signal(risk_type="量比偏离", level=2, description="量比放大")],
            technical_context(macd_alignment="bullish", rsi=62.0, boll_latest=(12.0, 10.0, 8.0), kdj_j=64.0),
        )

        self.assertEqual(separation.mainline.label, "主线方向评分")
        self.assertEqual(separation.swing.label, "Swing 买点评分")
        self.assertEqual(separation.mainline.score, 8.0)
        self.assertEqual(separation.mainline.max_score, 8.0)
        self.assertEqual(separation.swing.score, 8.0)
        self.assertIn("共振", separation.summary)


if __name__ == "__main__":
    unittest.main()

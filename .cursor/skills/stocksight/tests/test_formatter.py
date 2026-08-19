# -*- coding: utf-8 -*-
import unittest

from core import BOLLResult, KDJResult, MACDResult, NewsItem, RSIResult, RiskSignal, TechnicalAnalysis, TechnicalSignal, TradeLifecycle, TradeLifecycleEvent, TradePlan, TrendSummary
from formatter import (
    render_detailed_report,
    render_html_report,
    render_standard_report,
    validate_report,
)
from formatter.html_utils import _calculate_risk_score, calculate_dual_risk_score

from tests.fixtures import sample_report


class FormatterTests(unittest.TestCase):
    def test_trade_lifecycle_renders_state_and_audit_trail(self):
        data = sample_report(
            strategy_profile="swing",
            trade_lifecycle=TradeLifecycle(
                lifecycle_id="life-1",
                stock_code="600001",
                stock_name="Sample",
                market="sh",
                profile="swing",
                state="exited",
                state_label="已退出",
                plan_fingerprint="600001|swing|test",
                created_at="2026-06-10 15:00:00",
                updated_at="2026-06-14 15:00:00",
                entry_at="2026-06-11 10:00:00",
                entry_price=10.2,
                shares=100,
                exit_at="2026-06-14 15:00:00",
                exit_price=11.2,
                exit_reason="达到计划目标",
                pnl_amount=100.0,
                pnl_percent=9.8,
                r_multiple=1.5,
                holding_days=3,
                events=[
                    TradeLifecycleEvent(
                        from_state="holding",
                        to_state="exited",
                        timestamp="2026-06-14 15:00:00",
                        price=11.2,
                        reason="达到计划目标",
                        source="market",
                    )
                ],
            ),
        )

        markdown = render_detailed_report(data)
        html = render_html_report(data)

        self.assertIn("交易生命周期", markdown)
        self.assertIn("当前状态：**已退出**", markdown)
        self.assertIn("+1.50R", markdown)
        self.assertIn("交易生命周期", html)
        self.assertIn("lifecycle-steps", html)
        self.assertIn("达到计划目标", html)

    def test_trade_plan_replaces_fixed_stop_and_target_copy(self):
        data = sample_report(
            strategy_profile="swing",
            trade_plan=TradePlan(
                profile="swing",
                action="波段候选",
                status="ready",
                status_label="条件触发后执行",
                entry_style="突破触发",
                trigger_price=10.20,
                entry_low=10.20,
                entry_high=10.35,
                stop_loss=9.55,
                target_1=11.18,
                target_2=11.83,
                atr=0.42,
                atr_percent=4.2,
                stop_distance_percent=6.37,
                reward_risk_1=1.5,
                reward_risk_2=2.5,
                suggested_position_percent=7.85,
            ),
        )

        markdown = render_detailed_report(data)
        html = render_html_report(data)

        self.assertIn("价格与波动率交易计划", html)
        self.assertIn("结构止损", markdown)
        self.assertIn("1.50R", markdown)
        self.assertNotIn("（-5%）", markdown)
        self.assertNotIn("+5.6%", html)

    def test_standard_report_validates(self):
        data = sample_report()
        report = render_standard_report(data)
        result = validate_report(report, data)

        self.assertTrue(result.passed, result.errors)
        self.assertIn("<kbd>", report)
        self.assertIn("▰", report)
        self.assertIn("报告口径", report)
        self.assertIn("行情时间", report)

    def test_detailed_report_validates(self):
        data = sample_report(source_notes=["实时行情：unit", "历史行情：unit-history（80条）"])
        report = render_detailed_report(data)
        result = validate_report(report, data)

        self.assertTrue(result.passed, result.errors)
        self.assertIn("<details>", report)
        self.assertIn("技术指标辅助", report)
        self.assertIn("最终判断", report)
        self.assertIn("数据可信度", report)
        self.assertIn("报告口径", report)
        self.assertIn("数据来源链", report)
        self.assertIn("历史行情：unit-history", report)
        self.assertIn("使用 Snapshot", report)
        self.assertIn("突破确认", report)
        self.assertIn("确认条件", report)
        self.assertIn("失效条件", report)

    def test_html_report_contains_split_sections(self):
        html = render_html_report(sample_report())

        self.assertIn("<!doctype html>", html)
        self.assertIn("<style>", html)
        self.assertIn("risk-dashboard-shell", html)
        self.assertIn("new-radar-svg", html)
        self.assertIn('id="judgment"', html)
        self.assertIn("数据可信度", html)
        self.assertIn("行情时间", html)
        self.assertIn("Snapshot", html)
        self.assertIn("StockSight v0.6.0", html)
        self.assertIn("异动强度", html)
        self.assertIn("下行风险", html)
        self.assertIn("异动强度拆解", html)
        self.assertIn("价格波动", html)
        self.assertIn("突破确认", html)
        self.assertIn("确认条件", html)
        self.assertNotIn("A股主线第一波中段趋势策略", html)

    def test_news_context_splits_hard_info_and_market_news(self):
        data = sample_report(news=[
            NewsItem(
                title="Sample 年度报告公告",
                source="东方财富公告",
                url="https://data.eastmoney.com/notices/detail/600001/a.html",
                published_at="2026-05-18",
                snippet="[财报] 年度报告摘要",
            ),
            NewsItem(
                title="Sample 股价异动",
                source="财经媒体",
                url="https://example.com/news",
                published_at="2026-05-18",
                snippet="[新闻] 市场关注度升温",
            ),
        ])

        markdown = render_detailed_report(data)
        html = render_html_report(data)

        self.assertIn("公司公告与硬信息", markdown)
        self.assertIn("市场资讯与舆情", markdown)
        self.assertIn("公司公告与硬信息", html)
        self.assertIn("市场资讯与舆情", html)

    def test_mainline_strategy_profile_renders_in_markdown_and_html(self):
        technical = TechnicalAnalysis(
            rsi=RSIResult(values=[62.0], dates=["2026-05-18"]),
            boll=BOLLResult(upper=[12.0], middle=[10.0], lower=[8.0]),
            kdj=KDJResult(k=[58.0], d=[52.0], j=[64.0]),
            trend=TrendSummary(
                macd_alignment="bullish",
                macd_alignment_desc="MACD 多头排列",
                macd_histogram_trend="expanding",
                rsi_trend="uptrend",
                rsi_trend_desc="RSI 强势区上行",
            ),
        )
        data = sample_report(
            strategy_profile="mainline",
            technical=technical,
        )
        data.stocks[0].raw = {"industry": "机器人", "concepts": ["人工智能", "高端制造"]}

        markdown = render_detailed_report(data)
        html = render_html_report(data)

        self.assertIn("策略视角：A股主线第一波中段趋势策略", markdown)
        self.assertIn("结论类型：策略适配度判断，不构成买卖建议", markdown)
        self.assertIn("时间止损", markdown)
        self.assertIn("仓位提示", markdown)
        self.assertIn("主线方向 / Swing 买点分离", markdown)
        self.assertIn("主线方向评分", markdown)
        self.assertIn("Swing 买点评分", markdown)
        self.assertIn("A股主线第一波中段趋势策略", html)
        self.assertIn("策略适配度判断", html)
        self.assertIn("主线方向 / Swing 买点分离", html)
        self.assertIn("Swing 买点评分", html)

    def test_risk_avoid_strategy_profile_renders_in_markdown_and_html(self):
        data = sample_report(strategy_profile="risk_avoid")

        markdown = render_detailed_report(data)
        html = render_html_report(data)

        self.assertIn("策略视角：风险排雷视角", markdown)
        self.assertIn("结论类型：策略适配度判断，不构成买卖建议", markdown)
        self.assertIn("风险排雷视角", html)
        self.assertIn("排雷", html)

    def test_swing_strategy_profile_renders_in_markdown_and_html(self):
        data = sample_report(strategy_profile="swing")

        markdown = render_detailed_report(data)
        html = render_html_report(data)

        self.assertIn("策略视角：波段趋势视角", markdown)
        self.assertIn("结论类型：策略适配度判断，不构成买卖建议", markdown)
        self.assertNotIn("主线方向 / Swing 买点分离", markdown)
        self.assertIn("波段趋势视角", html)
        self.assertIn("波段", html)
        self.assertNotIn("主线方向 / Swing 买点分离", html)

    def test_neutral_strategy_profile_does_not_render_mainline_copy(self):
        markdown = render_detailed_report(sample_report())
        html = render_html_report(sample_report())

        self.assertNotIn("A股主线第一波中段趋势策略", markdown)
        self.assertNotIn("风险排雷视角", markdown)
        self.assertNotIn("波段趋势视角", markdown)
        self.assertNotIn("策略适配度判断", markdown)
        self.assertNotIn("A股主线第一波中段趋势策略", html)
        self.assertNotIn("风险排雷视角", html)
        self.assertNotIn("波段趋势视角", html)

    def test_html_report_without_signals_does_not_create_fake_pie(self):
        html = render_html_report(sample_report(signal=None, news=[]))

        self.assertIn("<!doctype html>", html)
        self.assertIn("empty-state", html)
        self.assertNotIn("Sample news", html)

    def test_technical_analysis_renders_in_markdown_and_html(self):
        technical = TechnicalAnalysis(
            macd=MACDResult(
                dif=[0.0, 0.1, 0.2],
                dea=[0.0, 0.12, 0.18],
                macd=[0.0, -0.04, 0.04],
                dates=["2026-01-01", "2026-01-02", "2026-01-03"],
            ),
            rsi=RSIResult(
                values=[0.0, 65.0, 72.5],
                dates=["2026-01-01", "2026-01-02", "2026-01-03"],
                period=14,
            ),
            boll=BOLLResult(
                upper=[0.0, 110.0, 112.0],
                middle=[0.0, 100.0, 101.0],
                lower=[0.0, 90.0, 91.0],
                dates=["2026-01-01", "2026-01-02", "2026-01-03"],
                period=20,
            ),
            kdj=KDJResult(
                k=[0.0, 76.0, 82.0],
                d=[0.0, 72.0, 78.0],
                j=[0.0, 84.0, 90.0],
                dates=["2026-01-01", "2026-01-02", "2026-01-03"],
                period=9,
            ),
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
        data = sample_report(technical=technical)

        markdown = render_detailed_report(data)
        html = render_html_report(data)

        self.assertIn("技术指标辅助", markdown)
        self.assertIn("异动强度拆解", markdown)
        self.assertIn("RSI14", markdown)
        self.assertIn("BOLL20", markdown)
        self.assertIn("KDJ9", markdown)
        self.assertIn("RSI技术信号", html)
        self.assertIn("BOLL20", html)
        self.assertIn("KDJ9", html)
        self.assertIn("technical-grid", html)
        self.assertIn("rsi-track", html)

    def test_technical_only_risk_score_is_capped(self):
        signals = [
            RiskSignal("AAPL", "RSI技术信号", 2, 72.1, "", "RSI overbought"),
            RiskSignal("AAPL", "MACD技术信号", 1, 0.0, "", "MACD helper"),
        ]

        self.assertLessEqual(_calculate_risk_score(signals), 60)

    def test_duplicate_technical_signals_have_diminishing_score(self):
        signals = [
            RiskSignal("AAPL", "RSI技术信号", 2, 72.1, "", "RSI overbought"),
            RiskSignal("AAPL", "KDJ技术信号", 2, 0.0, "", "KDJ death cross"),
            RiskSignal("AAPL", "KDJ技术信号", 2, 82.1, "", "KDJ overbought"),
        ]

        self.assertLess(_calculate_risk_score(signals), 60)

    def test_market_risks_can_score_higher_than_technical_only(self):
        technical = [RiskSignal("AAPL", "RSI技术信号", 2, 72.1, "", "RSI overbought")]
        market = [
            RiskSignal("TEST", "价格异动", 3, 9.8, "%", "跌停 price limit"),
            RiskSignal("TEST", "量比偏离", 3, 4.5, "x", "volume spike"),
            RiskSignal("TEST", "换手率异常", 2, 18.0, "%", "turnover spike"),
        ]

        self.assertGreater(_calculate_risk_score(market), _calculate_risk_score(technical))
        self.assertGreaterEqual(_calculate_risk_score(market), 80)

    def test_market_warnings_without_danger_are_capped_below_high_risk(self):
        signals = [
            RiskSignal("TEST", "超额收益异动", 2, 10.0, "%", "limit up watch"),
            RiskSignal("TEST", "RSI技术信号", 2, 73.0, "", "RSI overbought"),
            RiskSignal("TEST", "KDJ技术信号", 2, 0.0, "", "KDJ death cross"),
            RiskSignal("TEST", "BOLL技术信号", 1, 0.0, "", "near upper band"),
        ]

        self.assertLess(_calculate_risk_score(signals), 75)

    def test_limit_up_anomaly_can_be_high_while_downside_risk_is_capped(self):
        signals = [
            RiskSignal("TEST", "超额收益异动", 2, 10.0, "%", "涨幅绝对值10.0%，上涨方向按强异动观察"),
            RiskSignal("TEST", "量比偏离", 2, 2.4, "x", "量比放大但未到极端"),
        ]

        dual = calculate_dual_risk_score(signals)

        self.assertGreaterEqual(dual.anomaly_score, 60)
        self.assertLess(dual.risk_score, 70)

    def test_limit_down_keeps_higher_downside_risk(self):
        signals = [
            RiskSignal("TEST", "超额收益异动", 3, 10.0, "%", "跌停，下跌风险扩大"),
            RiskSignal("TEST", "量比偏离", 3, 4.1, "x", "放量下跌"),
        ]

        dual = calculate_dual_risk_score(signals)

        self.assertGreaterEqual(dual.risk_score, 75)


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""Separated strategy scorecards.

This module keeps market-direction fit separate from single-stock swing timing.
It reuses the existing strategy action layer so the new report section does not
drift from the current mainline and swing profile behavior.
"""

from dataclasses import dataclass, field
import re
from typing import List, Optional, Sequence

from .strategy import StrategyDecision, evaluate_strategy_action
from .types import NewsItem, RiskSignal, StockData, TechnicalAnalysis


_MAINLINE_SCORE_RE = re.compile(r"主线适配度评分\s+(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)")
_SWING_SCORE_RE = re.compile(r"波段趋势评分\s+(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)")


@dataclass(frozen=True)
class StrategyScorecard:
    """One separated scorecard in the combined strategy view."""

    label: str
    role: str
    decision: StrategyDecision
    score: Optional[float] = None
    max_score: Optional[float] = None
    status: str = ""
    hits: List[str] = field(default_factory=list)

    @property
    def score_text(self) -> str:
        if self.score is None or self.max_score is None:
            return "待确认"
        if float(self.score).is_integer() and float(self.max_score).is_integer():
            return f"{int(self.score)}/{int(self.max_score)}"
        return f"{self.score:.1f}/{self.max_score:.1f}"


@dataclass(frozen=True)
class StrategySeparation:
    """Mainline direction and swing timing shown as two independent layers."""

    mainline: StrategyScorecard
    swing: StrategyScorecard
    summary: str
    next_step: str


def _extract_score(decision: StrategyDecision, pattern: re.Pattern) -> tuple:
    text = "；".join(decision.basis or [])
    match = pattern.search(text)
    if not match:
        return None, None
    return float(match.group(1)), float(match.group(2))


def _score_status(score: Optional[float], max_score: Optional[float]) -> str:
    if score is None or max_score is None or max_score <= 0:
        return "待确认"
    ratio = score / max_score
    if ratio >= 0.75:
        return "通过"
    if ratio >= 0.60:
        return "接近"
    return "不足"


def _filter_hits(decision: StrategyDecision, score_label: str) -> List[str]:
    hits = []
    for item in decision.basis or []:
        if score_label in item:
            continue
        hits.append(item)
    return hits[:6]


def evaluate_strategy_separation(
    stock: StockData,
    signals: Sequence[RiskSignal],
    technical: Optional[TechnicalAnalysis] = None,
    news: Optional[Sequence[NewsItem]] = None,
) -> StrategySeparation:
    """Evaluate mainline direction fit and swing timing independently."""
    signals = list(signals or [])
    news = list(news or [])
    mainline_decision = evaluate_strategy_action(
        stock,
        signals,
        technical,
        news,
        profile="mainline",
    )
    swing_decision = evaluate_strategy_action(
        stock,
        signals,
        technical,
        news,
        profile="swing",
    )

    mainline_score, mainline_max = _extract_score(mainline_decision, _MAINLINE_SCORE_RE)
    swing_score = swing_decision.score
    swing_max = swing_decision.score_max
    if swing_score is None or swing_max is None:
        swing_score, swing_max = _extract_score(swing_decision, _SWING_SCORE_RE)
    mainline_card = StrategyScorecard(
        label="主线方向评分",
        role="判断这个方向/个股是否适合按 A 股主线第一波中段处理。",
        decision=mainline_decision,
        score=mainline_score,
        max_score=mainline_max,
        status=_score_status(mainline_score, mainline_max),
        hits=_filter_hits(mainline_decision, "主线适配度评分"),
    )
    swing_card = StrategyScorecard(
        label="Swing 买点评分",
        role="判断这只票当下是否具备波段入场、持有或回踩观察条件。",
        decision=swing_decision,
        score=swing_score,
        max_score=swing_max,
        status=_score_status(swing_score, swing_max),
        hits=_filter_hits(swing_decision, "波段趋势评分"),
    )

    summary, next_step = _combined_summary(mainline_card, swing_card)
    return StrategySeparation(
        mainline=mainline_card,
        swing=swing_card,
        summary=summary,
        next_step=next_step,
    )


def _combined_summary(mainline: StrategyScorecard, swing: StrategyScorecard) -> tuple:
    main_action = mainline.decision.action
    swing_action = swing.decision.action
    main_tone = mainline.decision.tone
    swing_tone = swing.decision.tone

    if main_tone == "danger":
        return (
            "主线方向层已触发回避/退出优先级，个股买点不应覆盖方向风险。",
            "先处理硬风险、退潮或破位问题；方向未恢复前不按 swing 信号进攻。",
        )
    if swing_tone == "danger":
        return (
            "方向可以继续观察，但个股 swing 结构已经失效。",
            "不硬扛单票破位；若方向仍强，优先换核心或等待重新站回平台。",
        )
    if mainline.status in ("通过", "接近") and swing_action == "波段候选":
        return (
            "主线方向和 swing 买点出现共振，可进入小仓试错计划。",
            "只在触发价、止损位、时间止损和仓位上限写清后执行。",
        )
    if mainline.status in ("通过", "接近") and swing_action in ("趋势持有", "回踩观察", "仅观察"):
        return (
            "方向层具备跟踪价值，但个股买点尚未充分确认。",
            "继续等放量突破或缩量回踩不破；不要因为方向好而追无计划买点。",
        )
    if swing_action == "波段候选":
        return (
            "个股技术结构较强，但主线方向证据不足。",
            "谨慎识别独立消息票或后排补涨；补齐主线评分前只观察。",
        )
    return (
        "主线方向和 swing 买点都未形成强共振。",
        "保持观察，等待方向持续性或个股右侧结构转强。",
    )

# -*- coding: utf-8 -*-
"""Rule-based strategy action layer.

This module converts quote anomalies and technical context into an explainable
report action. It is deliberately conservative: the action describes a setup to
track, not an order instruction.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re
from typing import List, Optional, Sequence

from .types import NewsItem, RiskSignal, StockData, TechnicalAnalysis


ACTION_RISK_AVOID = "风险规避"
ACTION_PULLBACK_WATCH = "回撤观察"
ACTION_COOLDOWN = "高位降温"
ACTION_BREAKOUT_CONFIRM = "突破确认"
ACTION_TREND_HOLD = "趋势持有"
ACTION_LOW_REPAIR = "低位修复"
ACTION_STABLE_TRACK = "平稳跟踪"
HARD_RISK_NEWS_MAX_AGE_DAYS = 120
SWING_STRATEGY_VERSION = "swing-v1"


@dataclass(frozen=True)
class StrategyDecision:
    """Explainable strategy decision for report rendering."""

    action: str
    tone: str
    summary: str
    basis: List[str] = field(default_factory=list)
    confirmation: str = ""
    invalidation: str = ""
    risk_note: str = ""
    profile: str = "neutral"
    profile_label: str = ""
    time_stop: str = ""
    position_note: str = ""
    score: Optional[float] = None
    score_max: Optional[float] = None
    score_factors: List[str] = field(default_factory=list)
    strategy_version: str = ""


def evaluate_strategy_action(
    stock: StockData,
    signals: Sequence[RiskSignal],
    technical: Optional[TechnicalAnalysis] = None,
    news: Optional[Sequence[NewsItem]] = None,
    profile: str = "neutral",
) -> StrategyDecision:
    """Evaluate a report-level strategy action from market and technical data."""
    signals = list(signals or [])
    news = list(news or [])
    max_level = max((int(signal.level or 0) for signal in signals), default=0)
    signal_text = _combined_signal_text(signals)
    active_hard_risk_news = _active_hard_risk_news(stock, news)
    active_hard_risk_text = _combined_news_text(active_hard_risk_news)

    trend = getattr(technical, "trend", None) if technical else None
    macd_alignment = getattr(trend, "macd_alignment", "") or ""
    rsi_trend = getattr(trend, "rsi_trend", "") or ""
    divergence = getattr(trend, "divergence", "") or ""
    rsi_latest = getattr(getattr(technical, "rsi", None), "latest", None) if technical else None
    boll_latest = getattr(getattr(technical, "boll", None), "latest", None) if technical else None
    kdj_latest = getattr(getattr(technical, "kdj", None), "latest", None) if technical else None

    change = stock.change_percent
    vr = stock.volume_ratio
    tr = stock.turnover_rate
    price_position = _boll_position(stock.current_price, boll_latest)
    kdj_j = kdj_latest[2] if kdj_latest else None

    hard_risk = bool(active_hard_risk_news)
    downside = (
        _has_downside_signal(signal_text)
        or _has_downside_signal(active_hard_risk_text)
        or (change <= -3 and vr >= 1.5)
    )
    overheated = (
        (rsi_latest is not None and rsi_latest >= 75)
        or divergence == "bearish"
        or (kdj_j is not None and kdj_j >= 100)
        or (price_position == "above_upper" and change > 0)
    )
    breakout = (
        change >= 2
        and vr >= 1.5
        and macd_alignment != "bearish"
        and not hard_risk
        and not downside
        and not overheated
        and (rsi_latest is None or 45 <= rsi_latest < 75)
    )
    trend_hold = (
        macd_alignment == "bullish"
        and not hard_risk
        and not downside
        and not overheated
        and max_level <= 1
        and (rsi_latest is None or 40 <= rsi_latest < 70)
    )
    low_repair = (
        not hard_risk
        and not downside
        and (
            (rsi_latest is not None and rsi_latest <= 35)
            or rsi_trend == "oversold_bounce"
            or price_position == "near_lower"
            or (kdj_j is not None and kdj_j <= 20)
        )
    )

    if profile == "mainline":
        return _evaluate_mainline_strategy(
            stock=stock,
            signals=signals,
            technical=technical,
            hard_risk=hard_risk,
            downside=downside,
            overheated=overheated,
            macd_alignment=macd_alignment,
            rsi_latest=rsi_latest,
            price_position=price_position,
            kdj_j=kdj_j,
        )
    if profile == "risk_avoid":
        return _evaluate_risk_avoid_strategy(
            stock=stock,
            signals=signals,
            technical=technical,
            hard_risk=hard_risk,
            downside=downside,
            overheated=overheated,
            macd_alignment=macd_alignment,
            rsi_latest=rsi_latest,
            price_position=price_position,
            kdj_j=kdj_j,
        )
    if profile == "swing":
        return _evaluate_swing_strategy(
            stock=stock,
            signals=signals,
            technical=technical,
            hard_risk=hard_risk,
            downside=downside,
            overheated=overheated,
            macd_alignment=macd_alignment,
            rsi_latest=rsi_latest,
            price_position=price_position,
            kdj_j=kdj_j,
            breakout=breakout,
            trend_hold=trend_hold,
            low_repair=low_repair,
        )

    basis = _basis(stock, signals, technical)
    if hard_risk:
        return StrategyDecision(
            action=ACTION_RISK_AVOID,
            tone="danger",
            summary="硬信息或事件风险优先，暂不宜用普通技术反弹逻辑解释。",
            basis=basis,
            confirmation="先确认公告、监管、业绩或股东变动的影响是否消化。",
            invalidation="只有事件风险解除且量价重新稳定，风险优先级才会下降。",
            risk_note="事件风险可能覆盖技术指标信号。",
        )

    if downside and (max_level >= 3 or macd_alignment == "bearish" or change <= -5):
        return StrategyDecision(
            action=ACTION_RISK_AVOID,
            tone="danger",
            summary="下行信号与高等级异动共振，风险控制优先。",
            basis=basis,
            confirmation="观察是否跌破近期支撑，并确认放量下跌是否延续。",
            invalidation="若缩量企稳且 MACD 空头收敛，风险可降为回撤观察。",
            risk_note="放量下跌或破位信号不适合按低位修复处理。",
        )

    if downside:
        return StrategyDecision(
            action=ACTION_PULLBACK_WATCH,
            tone="warning",
            summary="价格方向偏弱，优先等待支撑和量能企稳。",
            basis=basis,
            confirmation="确认回撤是否缩量，并观察 MACD/RSI 是否停止走弱。",
            invalidation="若继续放量下跌或跌破关键区间，升级为风险规避。",
            risk_note="回撤阶段不宜只看单个超卖信号。",
        )

    if overheated:
        return StrategyDecision(
            action=ACTION_COOLDOWN,
            tone="warning",
            summary="短线动能偏热，降低追高冲动，等待指标降温或回踩确认。",
            basis=basis,
            confirmation="确认 RSI/KDJ 是否回落，价格是否仍能站稳强势区间。",
            invalidation="若高换手叠加 MACD 柱收敛或顶背离扩大，过热风险上升。",
            risk_note="强趋势可延续，但高位拥挤会放大回撤波动。",
        )

    if breakout:
        return StrategyDecision(
            action=ACTION_BREAKOUT_CONFIRM,
            tone="watch",
            summary="放量上涨叠加多头动能，出现突破确认型机会。",
            basis=basis,
            confirmation="确认后续是否继续放量，并站稳当前价格区间。",
            invalidation="若量能回落且 MACD 柱体收敛，突破有效性下降。",
            risk_note="突破信号需要后续收盘位置和量能共同确认。",
        )

    if trend_hold:
        return StrategyDecision(
            action=ACTION_TREND_HOLD,
            tone="healthy",
            summary="趋势结构偏多，适合沿既定趋势继续跟踪。",
            basis=basis,
            confirmation="确认上涨量能是否温和延续，避免量价背离。",
            invalidation="若 MACD 转为空头或 RSI 快速跌破中性区间，趋势持有条件失效。",
            risk_note="趋势持有仍需遵守既定止损和仓位纪律。",
        )

    if low_repair:
        return StrategyDecision(
            action=ACTION_LOW_REPAIR,
            tone="watch",
            summary="低位或超卖修复迹象出现，但需要放量和趋势拐点确认。",
            basis=basis,
            confirmation="确认 RSI/KDJ 是否继续回升，并观察价格能否收回关键均衡区。",
            invalidation="若反弹无量或继续跌破下轨，修复假设失效。",
            risk_note="低位修复属于观察型动作，不等同于趋势反转。",
        )

    return StrategyDecision(
        action=ACTION_STABLE_TRACK,
        tone="healthy",
        summary="量价和技术结构暂未出现强方向信号，按既定策略跟踪。",
        basis=basis,
        confirmation="继续观察成交量、价格区间和 MACD/RSI/BOLL/KDJ 是否同步转强或转弱。",
        invalidation="若出现放量破位、极端换手或硬风险信息，平稳跟踪条件失效。",
        risk_note="数据不足时应降低策略判断权重。",
    )


def _evaluate_mainline_strategy(
    *,
    stock: StockData,
    signals: Sequence[RiskSignal],
    technical: Optional[TechnicalAnalysis],
    hard_risk: bool,
    downside: bool,
    overheated: bool,
    macd_alignment: str,
    rsi_latest: Optional[float],
    price_position: str,
    kdj_j: Optional[float],
) -> StrategyDecision:
    """Evaluate the optional A-share mainline first-wave trend profile."""
    max_level = max((int(signal.level or 0) for signal in signals), default=0)
    change = stock.change_percent
    vr = stock.volume_ratio
    tr = stock.turnover_rate
    sector_text, has_sector_context = _sector_context(stock)
    base_basis = _basis(stock, signals, technical)
    profile_label = "A股主线第一波中段趋势策略"
    common_time_stop = "买入后 5–7 个交易日无向上反馈应减仓；10–15 个交易日仍横盘织布或阴跌应退出。"
    common_position = "首笔试仓按账户 5%–8%；单票计划最大 15%–20%；只向盈利且趋势确认方向加仓，不亏损补仓。"

    def decision(
        action: str,
        tone: str,
        summary: str,
        confirmation: str,
        invalidation: str,
        risk_note: str,
        extra_basis: Optional[List[str]] = None,
    ) -> StrategyDecision:
        basis = list(base_basis)
        basis.append(sector_text)
        if extra_basis:
            basis.extend(extra_basis)
        if len(basis) > 8:
            basis = basis[:5] + basis[-3:]
        return StrategyDecision(
            action=action,
            tone=tone,
            summary=summary,
            basis=basis,
            confirmation=confirmation,
            invalidation=invalidation,
            risk_note=risk_note,
            profile="mainline",
            profile_label=profile_label,
            time_stop=common_time_stop,
            position_note=common_position,
        )

    if stock.market not in ("sh", "sz"):
        return decision(
            "仅观察",
            "watch",
            "该 profile 面向 A 股主线趋势，当前标的市场不匹配，保留为普通技术观察。",
            "如需使用该策略，应先确认标的是 A 股且具备板块/概念归属。",
            "市场不匹配时，不按 A 股主线策略给出参与状态。",
            "跨市场交易节奏、涨跌停制度和资金结构不同，不能直接套用。",
        )

    if hard_risk:
        return decision(
            "不适合参与",
            "danger",
            "硬信息或事件风险优先，当前不适合用主线趋势逻辑解释。",
            "先确认公告、监管、业绩、减持或退市风险是否消化。",
            "只有事件风险解除且量价重新稳定后，才恢复策略适配度判断。",
            "基本面和事件风险决定能不能碰，技术面只决定什么时候碰。",
        )

    severe_downside = downside and (
        max_level >= 3
        or change <= -3
        or macd_alignment == "bearish"
    )
    if severe_downside:
        return decision(
            "触发退出",
            "danger",
            "下行信号与风险异动共振，优先退出或回避，不按主线中段处理。",
            "观察是否能缩量止跌并重新收回关键均线或平台。",
            "继续放量下跌、跌回平台内或 MACD 维持空头时，退出条件延续。",
            "主线策略不处理放量破位和趋势转弱后的侥幸持有。",
        )

    if overheated:
        return decision(
            "触发减仓",
            "warning",
            "短线指标过热或背离风险升高，不适合在主线高潮段继续追高。",
            "等待 RSI/KDJ 降温、回踩缩量，并确认板块与中军仍能修复。",
            "高位放量滞涨、顶背离扩大或跌回突破平台内，应降为退出观察。",
            "主线策略只做刚确认且未高潮的中段，不追全网情绪高潮。",
        )

    score = 0
    score_basis: List[str] = []
    if has_sector_context:
        score += 1
        score_basis.append("板块/概念归属可识别")
    else:
        score_basis.append("板块信息不足")
    if change >= 2:
        score += 1
        score_basis.append("涨幅达到右侧强势阈值")
    if vr >= 1.5:
        score += 1
        score_basis.append("量比放大")
    if 2 <= tr <= 15:
        score += 1
        score_basis.append("换手处于可观察活跃区间")
    if macd_alignment == "bullish":
        score += 1
        score_basis.append("MACD 多头结构")
    elif macd_alignment != "bearish":
        score += 1
        score_basis.append("MACD 未明显空头")
    if rsi_latest is not None and 45 <= rsi_latest < 70:
        score += 1
        score_basis.append("RSI 未过热且保持强势区")
    if price_position in ("upper_half", "near_upper") and change >= 0:
        score += 1
        score_basis.append("价格处于偏强轨道")
    if max_level <= 2 and not downside:
        score += 1
        score_basis.append("未见高等级下行风险")

    score_basis.append(f"主线适配度评分 {score}/8")
    if score >= 6 and has_sector_context:
        return decision(
            "可小仓试错",
            "healthy",
            "量价与技术结构满足主线中段试错条件，但结论仅代表该策略适配度。",
            "确认板块持续强于大盘、中军参与、回踩不破或突破后能站稳。",
            "跌回突破平台、板块退潮、个股弱于板块或 5–7 天无反馈，则试错失败。",
            "只允许小仓验证，不因怕错过而一次性重仓。",
            score_basis,
        )
    if score >= 5:
        return decision(
            "进入候选池",
            "watch",
            "个股量价或技术结构接近主线策略要求，但仍缺少足够确认。",
            "继续确认板块共振、中军放量、真实催化和第一次分歧后的修复。",
            "若量能回落、板块不跟、后排补涨特征明显，则移出候选池。",
            "候选池不等于买入信号，缺主线确认时只观察。",
            score_basis,
        )
    return decision(
        "仅观察",
        "watch",
        "当前证据不足以证明处在主线第一波中段，先观察不参与。",
        "等待板块连续走强、多股共振、中军放量和个股右侧买点同时出现。",
        "若继续弱于板块、横盘低效或转为放量下跌，则不再按主线候选处理。",
        "信息不足时降低策略判断权重，避免把普通热点误判为主线。",
        score_basis,
    )


def _evaluate_risk_avoid_strategy(
    *,
    stock: StockData,
    signals: Sequence[RiskSignal],
    technical: Optional[TechnicalAnalysis],
    hard_risk: bool,
    downside: bool,
    overheated: bool,
    macd_alignment: str,
    rsi_latest: Optional[float],
    price_position: str,
    kdj_j: Optional[float],
) -> StrategyDecision:
    """Evaluate a conservative hard-risk screening profile."""
    max_level = max((int(signal.level or 0) for signal in signals), default=0)
    change = stock.change_percent
    vr = stock.volume_ratio
    sector_text, _ = _sector_context(stock)
    base_basis = _basis(stock, signals, technical)
    profile_label = "风险排雷视角"
    common_time_stop = "硬风险未消化时不使用时间换空间；若 3–5 个交易日仍无澄清或量价继续走弱，应维持回避。"
    common_position = "排雷视角不提供进攻仓位；硬风险未解除前不加仓，不用技术反弹抵消公告、监管或退市风险。"

    def decision(
        action: str,
        tone: str,
        summary: str,
        confirmation: str,
        invalidation: str,
        risk_note: str,
        extra_basis: Optional[List[str]] = None,
    ) -> StrategyDecision:
        basis = list(base_basis)
        basis.append(sector_text)
        if extra_basis:
            basis.extend(extra_basis)
        if len(basis) > 8:
            basis = basis[:5] + basis[-3:]
        return StrategyDecision(
            action=action,
            tone=tone,
            summary=summary,
            basis=basis,
            confirmation=confirmation,
            invalidation=invalidation,
            risk_note=risk_note,
            profile="risk_avoid",
            profile_label=profile_label,
            time_stop=common_time_stop,
            position_note=common_position,
        )

    if _is_st_or_delisting_name(stock.name):
        return decision(
            "排雷未通过",
            "danger",
            "名称包含 ST、*ST 或退市线索，先按硬风险标的处理，不用普通趋势信号覆盖。",
            "优先核对交易所风险警示、退市指标、最近一期审计意见和持续经营说明。",
            "只有风险警示解除、退市触发项消除且公告连续验证后，才可重新进入普通观察。",
            "ST 类标的波动弹性不能替代基本排雷，低价或超跌不构成安全边际。",
            ["名称风险标识命中"],
        )

    if hard_risk:
        return decision(
            "不适合参与",
            "danger",
            "近期公告、监管、业绩、减持或退市类硬信息命中，排雷视角优先回避。",
            "先读原始公告，确认事项性质、金额影响、监管进度、股东行为和后续时间表。",
            "硬风险解除、澄清可信且量价恢复稳定前，不把技术修复视为有效信号。",
            "事件风险具有跳空和连续定价风险，不能只靠盘中止损管理。",
            ["硬风险信息命中"],
        )

    severe_break = downside and (
        max_level >= 3
        or change <= -4
        or (change <= -2 and vr >= 2)
        or macd_alignment == "bearish"
    )
    if severe_break:
        return decision(
            "风险规避",
            "danger",
            "放量下跌、破位或技术空头信号共振，排雷视角不参与弱势修复。",
            "确认是否跌破近期平台、均线或 BOLL 中下轨，并追踪成交量是否继续放大。",
            "若缩量止跌、重新收回平台且 MACD 空头收敛，才降级为重点排查。",
            "下跌阶段的高量能通常先解释为筹码松动，而不是安全换手。",
            ["下行结构命中"],
        )

    if downside or macd_alignment == "bearish" or max_level >= 3:
        return decision(
            "重点排查",
            "warning",
            "暂未发现明确硬风险，但量价或技术结构偏弱，需要继续排查公告和盘口承接。",
            "核对近 120 天公告、问询函、减持、质押、业绩预告和异常交易说明。",
            "若后续出现硬风险公告、放量下跌或跌破关键区间，立即降为风险规避。",
            "排雷未完成前，不把单日反弹当作风险解除。",
            ["软风险或弱势结构命中"],
        )

    if overheated:
        return decision(
            "重点排查",
            "warning",
            "短线过热或背离会放大高位兑现风险，即使没有硬风险也不宜放松排雷。",
            "观察 RSI/KDJ 是否降温、是否出现高位放量滞涨，以及公告面是否有减持或澄清。",
            "若顶背离扩大、换手继续极端或出现监管公告，降为风险规避。",
            "排雷视角优先避免高位流动性陷阱。",
            ["过热风险命中"],
        )

    clean_score = 0
    clean_basis: List[str] = []
    if max_level <= 1:
        clean_score += 1
        clean_basis.append("异动等级不高")
    if not downside:
        clean_score += 1
        clean_basis.append("未见放量下跌/破位线索")
    if macd_alignment != "bearish":
        clean_score += 1
        clean_basis.append("MACD 未明显空头")
    if rsi_latest is None or 35 <= rsi_latest <= 70:
        clean_score += 1
        clean_basis.append("RSI 未处于极端区")
    if price_position not in ("below_lower", "above_upper"):
        clean_score += 1
        clean_basis.append("BOLL 位置未极端")
    if kdj_j is None or 10 <= kdj_j <= 95:
        clean_score += 1
        clean_basis.append("KDJ J 值未极端")

    clean_basis.append(f"排雷通过度 {clean_score}/6")
    if clean_score >= 5:
        return decision(
            "排雷通过",
            "healthy",
            "当前未发现硬风险或明显弱势共振，可作为其他策略视角的前置过滤结果。",
            "继续跟踪公告、监管问询、业绩预告、股东减持和异常交易说明是否新增。",
            "一旦出现硬风险、放量下跌或技术破位，排雷通过状态立即失效。",
            "排雷通过不等于买入建议，只说明风险过滤暂未拦截。",
            clean_basis,
        )
    return decision(
        "仅观察",
        "watch",
        "信息不足以给出排雷通过，先保留观察，不把缺信息当成无风险。",
        "补齐公告、行业、概念、业绩和股东变化后再判断是否通过排雷。",
        "若补充信息出现监管、退市、减持、业绩恶化或放量破位，应转为回避。",
        "免费数据可能存在延迟，排雷视角应保守处理信息缺口。",
        clean_basis,
    )


def _evaluate_swing_strategy(
    *,
    stock: StockData,
    signals: Sequence[RiskSignal],
    technical: Optional[TechnicalAnalysis],
    hard_risk: bool,
    downside: bool,
    overheated: bool,
    macd_alignment: str,
    rsi_latest: Optional[float],
    price_position: str,
    kdj_j: Optional[float],
    breakout: bool,
    trend_hold: bool,
    low_repair: bool,
) -> StrategyDecision:
    """Evaluate a general swing-trend profile."""
    max_level = max((int(signal.level or 0) for signal in signals), default=0)
    change = stock.change_percent
    vr = stock.volume_ratio
    tr = stock.turnover_rate
    base_basis = _basis(stock, signals, technical)
    profile_label = "波段趋势视角"
    common_time_stop = "介入后 5–8 个交易日无趋势延续应降仓；跌回平台或跌破回踩低点时退出观察。"
    common_position = "分批参与，单票计划仓位控制在 10%–20%；只在趋势确认后加仓，不亏损补仓。"
    swing_score = 0
    score_basis: List[str] = []
    if change >= 1.5:
        swing_score += 1
        score_basis.append("价格右侧走强")
    if vr >= 1.3:
        swing_score += 1
        score_basis.append("量能放大")
    if 1 <= tr <= 12:
        swing_score += 1
        score_basis.append("换手处于波段可观察区")
    if macd_alignment == "bullish":
        swing_score += 2
        score_basis.append("MACD 多头结构")
    elif macd_alignment != "bearish":
        swing_score += 1
        score_basis.append("MACD 未明显空头")
    if rsi_latest is not None and 45 <= rsi_latest < 70:
        swing_score += 1
        score_basis.append("RSI 处于趋势区且未过热")
    if price_position in ("upper_half", "near_upper") and change >= 0:
        swing_score += 1
        score_basis.append("价格处于 BOLL 偏强区域")
    if kdj_j is not None and 35 <= kdj_j < 95:
        swing_score += 1
        score_basis.append("KDJ 未极端")

    def decision(
        action: str,
        tone: str,
        summary: str,
        confirmation: str,
        invalidation: str,
        risk_note: str,
        extra_basis: Optional[List[str]] = None,
    ) -> StrategyDecision:
        basis = list(base_basis)
        if extra_basis:
            basis.extend(extra_basis)
        if len(basis) > 8:
            basis = basis[:5] + basis[-3:]
        return StrategyDecision(
            action=action,
            tone=tone,
            summary=summary,
            basis=basis,
            confirmation=confirmation,
            invalidation=invalidation,
            risk_note=risk_note,
            profile="swing",
            profile_label=profile_label,
            time_stop=common_time_stop,
            position_note=common_position,
            score=float(swing_score),
            score_max=8.0,
            score_factors=list(score_basis),
            strategy_version=SWING_STRATEGY_VERSION,
        )

    if hard_risk:
        return decision(
            "触发退出",
            "danger",
            "硬风险信息优先于波段结构，当前不按趋势延续处理。",
            "先确认公告、监管、业绩、减持或退市风险是否消化。",
            "硬风险未解除前，波段视角失效。",
            "波段策略的前提是可交易风险可控，事件风险会破坏止损有效性。",
            ["硬风险信息命中"],
        )

    severe_downside = downside and (
        max_level >= 2
        or change <= -3
        or (vr >= 1.5 and change < 0)
        or macd_alignment == "bearish"
        or price_position == "below_lower"
    )
    if severe_downside:
        return decision(
            "触发退出",
            "danger",
            "放量下跌、破位或空头结构命中，波段趋势条件失效。",
            "观察是否能快速收回平台、均线或 BOLL 中轨，并确认量能不再放大下行。",
            "继续放量下跌、MACD 维持空头或反抽无量时，退出状态延续。",
            "趋势失效后不按回踩买点处理。",
            ["破位/下行结构命中"],
        )

    if overheated:
        return decision(
            "高位降温",
            "warning",
            "RSI/KDJ 过热、顶背离或价格贴近上轨，波段视角先降温防追高。",
            "等待指标回落、缩量回踩不破，或放量换手后仍能站稳平台。",
            "若高位放量滞涨、跌回突破平台或背离扩大，转为触发退出。",
            "波段策略可以吃趋势，不吃无确认的高位情绪。",
            ["过热或背离风险命中"],
        )

    score_display_basis = score_basis + [f"波段趋势评分 {swing_score}/8"]
    if breakout or swing_score >= 6:
        return decision(
            "波段候选",
            "healthy",
            "量价和技术结构支持波段趋势候选，但仍需收盘确认和回踩验证。",
            "确认突破后能站稳、回踩缩量不破，并且 MACD/RSI 不转弱。",
            "跌回平台、量能快速萎缩或 MACD 柱体连续收敛，则候选条件失效。",
            "候选不等于立即重仓，先等交易计划中的触发价和止损位明确。",
            score_display_basis,
        )
    if trend_hold or (macd_alignment == "bullish" and not downside):
        return decision(
            "趋势持有",
            "healthy",
            "趋势结构仍偏多，适合按波段计划跟踪持有或等待回踩加分。",
            "确认价格保持在平台或均线上方，量能温和，RSI 不跌破中性区。",
            "跌破平台、MACD 转空或连续放量阴线时，趋势持有失效。",
            "持有条件来自趋势延续，不来自摊低成本。",
            score_display_basis,
        )
    if low_repair or price_position == "near_lower" or (rsi_latest is not None and rsi_latest <= 40):
        return decision(
            "回踩观察",
            "watch",
            "价格或指标接近回踩/修复区，但还缺少重新转强确认。",
            "等待缩量止跌、KDJ/RSI 拐头、价格收回均衡区后再评估。",
            "若回踩继续放量下跌或跌破前低，转为触发退出。",
            "回踩观察只是等待区，不是自动低吸信号。",
            score_display_basis,
        )
    return decision(
        "仅观察",
        "watch",
        "当前趋势强度不足，波段视角缺少清晰右侧或回踩确认。",
        "等待放量突破、缩量回踩不破，或 MACD/RSI 重新同步转强。",
        "若持续横盘低效、量能萎缩或转为下行结构，则不进入波段候选。",
        "没有清晰波段结构时，应让资金保持机动。",
        score_display_basis,
    )


def _sector_context(stock: StockData) -> tuple:
    raw = stock.raw if isinstance(stock.raw, dict) else {}
    industry = str(raw.get("industry") or raw.get("f127") or "").strip()
    concepts_raw = raw.get("concepts") or raw.get("f129") or []
    if isinstance(concepts_raw, str):
        concepts = [part.strip() for part in concepts_raw.split(",") if part.strip()]
    elif isinstance(concepts_raw, (list, tuple)):
        concepts = [str(part).strip() for part in concepts_raw if str(part).strip()]
    else:
        concepts = []

    if industry and concepts:
        return f"行业/概念：{industry} / {'、'.join(concepts[:3])}", True
    if industry:
        return f"行业：{industry}", True
    if concepts:
        return f"概念：{'、'.join(concepts[:3])}", True
    return "板块信息不足：未从行情 raw 字段识别行业/概念", False


def _is_st_or_delisting_name(name: str) -> bool:
    normalized = (name or "").upper().replace(" ", "")
    return "ST" in normalized or "退市" in normalized


def _basis(
    stock: StockData,
    signals: Sequence[RiskSignal],
    technical: Optional[TechnicalAnalysis],
) -> List[str]:
    items = [
        f"涨跌幅 {stock.change_percent:+.2f}%",
        f"量比 {stock.volume_ratio:.2f}" if stock.volume_ratio > 0 else "量比缺失",
        f"换手率 {stock.turnover_rate:.1f}%" if stock.turnover_rate > 0 else "换手率缺失",
    ]
    if signals:
        top = max(signals, key=lambda signal: int(signal.level or 0))
        items.append(f"最高异动 {top.risk_type} L{top.level}")

    trend = getattr(technical, "trend", None) if technical else None
    if trend and getattr(trend, "macd_alignment_desc", ""):
        items.append(trend.macd_alignment_desc)
    rsi_latest = getattr(getattr(technical, "rsi", None), "latest", None) if technical else None
    if rsi_latest is not None:
        items.append(f"RSI {rsi_latest:.1f}")
    if trend and getattr(trend, "divergence_desc", ""):
        items.append(trend.divergence_desc)
    return items[:6]


def _combined_signal_text(signals: Sequence[RiskSignal]) -> str:
    return " ".join(
        f"{signal.risk_type} {signal.description}" for signal in signals
    )


def _combined_news_text(news: Sequence[NewsItem]) -> str:
    return " ".join(
        f"{item.title} {item.source} {item.snippet}" for item in news
    )


def _active_hard_risk_news(stock: StockData, news: Sequence[NewsItem]) -> List[NewsItem]:
    report_date = _parse_reference_date(stock.timestamp)
    active: List[NewsItem] = []
    for item in news:
        text = _news_text(item)
        if not _news_matches_stock(text, stock):
            continue
        if not _has_hard_risk(text):
            continue
        event_date = _extract_news_date(item)
        if event_date is None:
            continue
        age_days = abs((report_date - event_date).days)
        if age_days <= HARD_RISK_NEWS_MAX_AGE_DAYS:
            active.append(item)
    return active


def _news_text(item: NewsItem) -> str:
    return f"{item.title} {item.source} {item.snippet} {item.published_at} {item.url}"


def _news_matches_stock(text: str, stock: StockData) -> bool:
    lowered = text.lower()
    return bool(
        (stock.code and stock.code.lower() in lowered)
        or (stock.name and stock.name.lower() in lowered)
    )


def _parse_reference_date(value: str) -> datetime:
    parsed = _parse_date_text(value)
    return parsed or datetime.now()


def _extract_news_date(item: NewsItem) -> Optional[datetime]:
    return _parse_date_text(_news_text(item))


def _parse_date_text(text: str) -> Optional[datetime]:
    if not text:
        return None

    relative_today = ("刚刚", "分钟前", "小时前", "今天")
    if any(token in text for token in relative_today):
        return datetime.now()
    if "昨天" in text:
        return (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    match = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", text)
    if match:
        year, month, day = (int(part) for part in match.groups())
        return _safe_datetime(year, month, day)

    match = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if match:
        year, month, day = (int(part) for part in match.groups())
        return _safe_datetime(year, month, day)

    match = re.search(r"\b(\d{1,2})[-/](\d{1,2})(?:\s+\d{1,2}:\d{2})?\b", text)
    if match:
        month, day = (int(part) for part in match.groups())
        year = datetime.now().year
        return _safe_datetime(year, month, day)
    return None


def _safe_datetime(year: int, month: int, day: int) -> Optional[datetime]:
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def _has_hard_risk(text: str) -> bool:
    keywords = (
        "风险提示",
        "退市",
        "监管",
        "处罚",
        "立案",
        "预亏",
        "业绩下修",
        "减持",
        "质押",
        "问询函",
    )
    return any(keyword in text for keyword in keywords)


def _has_downside_signal(text: str) -> bool:
    keywords = ("下跌", "跌停", "跑输", "走弱", "回撤", "破位", "顶背离", "死叉")
    return any(keyword in text for keyword in keywords)


def _boll_position(price: float, latest: Optional[tuple]) -> str:
    if not latest:
        return ""
    upper, middle, lower = latest
    if upper <= lower:
        return ""
    band = upper - lower
    if price >= upper:
        return "above_upper"
    if price >= upper - band * 0.15:
        return "near_upper"
    if price <= lower:
        return "below_lower"
    if price <= lower + band * 0.15:
        return "near_lower"
    if price >= middle:
        return "upper_half"
    return "lower_half"

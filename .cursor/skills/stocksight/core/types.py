# -*- coding: utf-8 -*-
"""核心数据类型定义"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class NewsItem:
    """一条新闻条目

    Args:
        title: 新闻标题
        source: 来源名称（如"新浪财经"）
        url: 原文链接（可选）
        published_at: 发布时间（如"2小时前"或"05-17 21:30"）
        snippet: 摘要文本（可选，详细模式使用）
    """
    title: str
    source: str
    url: str = ""
    published_at: str = ""
    snippet: str = ""


@dataclass
class StockData:
    """标准化的股票数据，所有数据源统一输出此格式"""

    code: str
    """股票代码，如 '600570'"""

    name: str
    """股票名称"""

    current_price: float
    """当前价格（元）"""

    prev_close: float
    """昨日收盘价（元）"""

    open_price: float
    """今日开盘价（元）"""

    high: float
    """今日最高价（元）"""

    low: float
    """今日最低价（元）"""

    volume: int
    """成交量（手）"""

    amount: float
    """成交额（万元）"""

    volume_ratio: float
    """量比"""

    change_percent: float
    """涨跌幅（%）"""

    turnover_rate: float
    """换手率（%）"""

    timestamp: str
    """数据时间，格式 'YYYY-MM-DD HH:MM:SS'"""

    market: str = ""
    """市场标记: 'sh' 沪市, 'sz' 深市, 'hk' 港股, 'us' 美股（可选，默认空字符串）"""

    raw: Optional[dict] = field(default=None)
    """原始数据（调试用，可选）"""



@dataclass
class HistoryBar:
    """单日 OHLCV 数据点"""

    date: str
    """日期，格式 'YYYY-MM-DD'"""
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float = 0.0
    """成交额（万元）；数据源不提供时为 0。"""
    turnover_rate: float = 0.0
    """换手率（%）；数据源不提供时为 0。"""
    change_percent: float = 0.0
    """当日涨跌幅（%）；数据源不提供时可由前收盘价推导。"""


@dataclass
class StockHistory:
    """股票历史价格序列，用于技术指标计算"""

    code: str
    """股票代码"""
    bars: List[HistoryBar] = field(default_factory=list)
    """价格序列，按时间升序排列"""


@dataclass
class MACDResult:
    """MACD 指标结果"""

    dif: List[float] = field(default_factory=list)
    """DIF = EMA12 - EMA26"""
    dea: List[float] = field(default_factory=list)
    """DEA = DIF 的 EMA9 信号线"""
    macd: List[float] = field(default_factory=list)
    """MACD 柱 = 2 * (DIF - DEA)"""
    dates: List[str] = field(default_factory=list)
    """对应日期"""


@dataclass
class RSIResult:
    """RSI 指标结果"""

    values: List[float] = field(default_factory=list)
    """RSI 序列"""
    dates: List[str] = field(default_factory=list)
    """对应日期"""
    period: int = 14
    """RSI 周期"""

    @property
    def latest(self) -> Optional[float]:
        """最新可用 RSI 值。"""
        return self.values[-1] if self.values else None


@dataclass
class BOLLResult:
    """BOLL 布林带指标结果"""

    upper: List[float] = field(default_factory=list)
    """上轨"""
    middle: List[float] = field(default_factory=list)
    """中轨"""
    lower: List[float] = field(default_factory=list)
    """下轨"""
    dates: List[str] = field(default_factory=list)
    """对应日期"""
    period: int = 20
    """周期"""

    @property
    def latest(self) -> Optional[tuple]:
        """最新可用的 (upper, middle, lower)。"""
        if not self.upper or not self.middle or not self.lower:
            return None
        return (self.upper[-1], self.middle[-1], self.lower[-1])


@dataclass
class KDJResult:
    """KDJ 指标结果"""

    k: List[float] = field(default_factory=list)
    """K 值"""
    d: List[float] = field(default_factory=list)
    """D 值"""
    j: List[float] = field(default_factory=list)
    """J 值"""
    dates: List[str] = field(default_factory=list)
    """对应日期"""
    period: int = 9
    """RSV 周期"""

    @property
    def latest(self) -> Optional[tuple]:
        """最新可用的 (K, D, J)。"""
        if not self.k or not self.d or not self.j:
            return None
        return (self.k[-1], self.d[-1], self.j[-1])


@dataclass
class TechnicalSignal:
    """技术指标信号，用于辅助判断和转换为风险信号"""

    indicator: str
    signal_type: str
    level: int
    direction: str
    date: str
    value: float
    description: str



@dataclass
class TrendSummary:
    """MACD/RSI 趋势摘要，用于描述指标排列和背离状态。

    所有字段可能为空字符串，表示数据不足以做出判断。
    """

    macd_alignment: str = ""
    """MACD 排列: "bullish" 多头, "bearish" 空头, "turning" 即将交叉, "" 不足"""

    macd_alignment_desc: str = ""
    """MACD 排列中文描述，如“多头排列：DIF > DEA，动能偏多”"""

    macd_histogram_trend: str = ""
    """MACD 柱趋势: "expanding" 扩张, "contracting" 收敛, "flat" 持平"""

    rsi_trend: str = ""
    """RSI 趋势: "overbought_pullback" 超买回落, "oversold_bounce" 超卖反弹,
       "divergence_bearish" RSI 不确认新高, "uptrend" / "downtrend" / """""

    rsi_trend_desc: str = ""
    """RSI 趋势中文描述"""

    divergence: str = ""
    """价格与 MACD 背离: "bearish" 顶背离, "bullish" 底背离, "" 无背离"""

    divergence_desc: str = ""
    """背离中文描述，如“价格创新高但MACD未确认，顶背离风险”"""


@dataclass
class TechnicalAnalysis:
    """完整技术指标分析结果"""

    macd: MACDResult = field(default_factory=MACDResult)
    rsi: RSIResult = field(default_factory=RSIResult)
    boll: BOLLResult = field(default_factory=BOLLResult)
    kdj: KDJResult = field(default_factory=KDJResult)
    signals: List[TechnicalSignal] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    trend: TrendSummary = field(default_factory=TrendSummary)


@dataclass
class RiskSignal:
    """异动信号 — detector 输出给 formatter 的核心数据结构"""

    stock_code: str
    """触发异动的股票代码"""

    risk_type: str
    """风险类型，如 '量比偏离' / '换手率偏高' / '超额收益异动'"""

    level: int
    """风险等级: 1=关注🔸, 2=警告🔶, 3=危险🔴"""

    deviation_value: float
    """偏离度数值"""

    deviation_unit: str
    """偏离度单位: '%' 或 'σ'"""

    description: str
    """可读的描述文本，如 '量比2.15，超过板块均值1.2倍'"""


@dataclass
class ReportData:
    """报告数据 — 传给 formatter 渲染的完整数据包"""

    title: str
    """报告标题"""

    summary: str
    """一句话摘要（模板填空生成）"""

    stocks: List[StockData]
    """参与分析的股票列表"""

    signals: List[RiskSignal]
    """detector 检测到的异动信号"""

    data_source: str
    """数据来源名称"""

    timestamp: str
    """报告生成时间"""

    news: List[NewsItem] = field(default_factory=list)
    """相关新闻列表（可选，由 NewsProvider 搜索填充）"""

    technical: Optional[TechnicalAnalysis] = None
    """技术指标分析（可选，详细单股报告使用）"""

    snapshot_source: str = ""
    """快照来源路径；为空表示本次报告不是从 snapshot 回放。"""

    source_notes: List[str] = field(default_factory=list)
    """数据来源链说明，如实时行情源、历史行情源和 fallback 状态。"""

    strategy_profile: str = "neutral"
    """策略视角标记；默认 neutral 表示通用中立报告口径。"""

    strategy_performance: Optional["StrategyPerformance"] = None
    """与当前策略动作匹配的历史样本外表现；未加载校准文件时为空。"""

    trade_plan: Optional["TradePlan"] = None
    """基于价格结构、ATR 和账户风险预算生成的交易计划。"""

    trade_lifecycle: Optional["TradeLifecycle"] = None
    """候选、触发、持仓、退出和复盘的当前交易生命周期。"""


@dataclass
class StrategyPerformance:
    """当前策略动作对应的历史样本外表现摘要。"""

    profile: str
    strategy_version: str
    horizon_days: int
    probability_positive: float
    sample_size: int
    reliability: str
    mean_return: float = 0.0
    median_return: float = 0.0
    action: str = ""
    score: Optional[float] = None
    score_max: Optional[float] = None
    source: str = ""
    generated_at: str = ""
    match_basis: str = ""
    note: str = ""


@dataclass
class TradePlan:
    """Detailed, risk-budgeted execution plan for one stock."""

    profile: str
    action: str
    status: str
    status_label: str
    entry_style: str
    trigger_price: Optional[float] = None
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    atr: Optional[float] = None
    atr_percent: Optional[float] = None
    structure_support: Optional[float] = None
    recent_resistance: Optional[float] = None
    stop_distance_percent: Optional[float] = None
    reward_risk_1: Optional[float] = None
    reward_risk_2: Optional[float] = None
    risk_per_trade_percent: float = 0.5
    max_position_percent: float = 20.0
    suggested_position_percent: Optional[float] = None
    account_size: Optional[float] = None
    risk_budget_amount: Optional[float] = None
    position_value: Optional[float] = None
    shares: Optional[int] = None
    lot_size: int = 1
    basis: List[str] = field(default_factory=list)
    invalidation: str = ""
    note: str = ""


@dataclass
class TradeLifecycleEvent:
    """One auditable transition in a trade lifecycle."""

    from_state: str
    to_state: str
    timestamp: str
    price: Optional[float] = None
    reason: str = ""
    source: str = "system"


@dataclass
class TradeLifecycle:
    """Persistent candidate-to-review lifecycle for one strategy setup."""

    lifecycle_id: str
    stock_code: str
    stock_name: str
    market: str
    profile: str
    state: str
    state_label: str
    plan_fingerprint: str
    created_at: str
    updated_at: str
    action: str = ""
    trigger_price: Optional[float] = None
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None
    planned_stop: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    triggered_at: str = ""
    triggered_price: Optional[float] = None
    entry_at: str = ""
    entry_price: Optional[float] = None
    shares: Optional[int] = None
    exit_at: str = ""
    exit_price: Optional[float] = None
    exit_reason: str = ""
    review_at: str = ""
    review_note: str = ""
    review_grade: str = ""
    pnl_amount: Optional[float] = None
    pnl_percent: Optional[float] = None
    r_multiple: Optional[float] = None
    holding_days: Optional[int] = None
    events: List[TradeLifecycleEvent] = field(default_factory=list)

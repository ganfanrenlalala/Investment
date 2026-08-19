# -*- coding: utf-8 -*-
"""Small HTML rendering utilities for StockSight reports."""

from html import escape
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from core import ReportData, RiskSignal, StockData

VERSION = "0.6.0"

LEVEL_COLORS = {
    1: "#d79b2b",
    2: "#d36b23",
    3: "#c2412d",
}

TYPE_COLORS = [
    "#2454d6",
    "#16794c",
    "#b7791f",
    "#c2412d",
    "#6b46c1",
    "#0f766e",
    "#be185d",
    "#0891b2",
]

HEADER_GRADIENTS = {
    0: "linear-gradient(135deg, #172033 0%, #1e3a5f 25%, #253858 50%, #1e3a5f 75%, #172033 100%)",
    1: "linear-gradient(135deg, #172033 0%, #3d3a1e 25%, #4a4520 50%, #3d3a1e 75%, #172033 100%)",
    2: "linear-gradient(135deg, #172033 0%, #3d2e1e 25%, #5a3a1a 50%, #3d2e1e 75%, #172033 100%)",
    3: "linear-gradient(135deg, #172033 0%, #3d1e1e 25%, #5a1a1a 50%, #3d1e1e 75%, #172033 100%)",
}


def _html(text: object) -> str:
    return escape(str(text), quote=True)


def _target_stock_and_signals(data: ReportData) -> Tuple[StockData, List[RiskSignal]]:
    if data.signals:
        top_signal = max(data.signals, key=lambda sig: sig.level)
        stock = next(
            (candidate for candidate in data.stocks if candidate.code == top_signal.stock_code),
            data.stocks[0],
        )
        return stock, [sig for sig in data.signals if sig.stock_code == stock.code]
    return data.stocks[0], []


def _metric_card(label: str, value: str, tone: str = "") -> str:
    class_name = f"metric {tone}".strip()
    return (
        f'<div class="{class_name}">'
        f"<span>{_html(label)}</span>"
        f"<strong>{value}</strong>"
        "</div>"
    )


def _change_heat_style(change: float) -> str:
    if change > 5:
        return "background:#16794c;color:white;"
    if change > 2:
        return "background:#22c55e;color:white;"
    if change < -5:
        return "background:#c2412d;color:white;"
    if change < -2:
        return "background:#ef4444;color:white;"
    return ""


def _metric_card_heat(label: str, value: str, change: float) -> str:
    heat = _change_heat_style(change)
    inner_style = f'style="{heat}"' if heat else ""
    return (
        f'<div class="metric heat">'
        f"<span>{_html(label)}</span>"
        f'<strong {inner_style}>{value}</strong>'
        "</div>"
    )


def _pie_gradient(segments: Sequence[Tuple[str, int]]) -> str:
    total = sum(count for _, count in segments)
    if total <= 0:
        return ""

    stops = []
    start = 0.0
    for index, (_, count) in enumerate(segments):
        if count <= 0:
            continue
        color = TYPE_COLORS[index % len(TYPE_COLORS)]
        end = start + count / total * 100
        stops.append(f"{color} {start:.2f}% {end:.2f}%")
        start = end
    return f"background: conic-gradient({', '.join(stops)});"


def _level_pie_gradient(counts: Dict[int, int]) -> str:
    total = sum(counts.values())
    if total <= 0:
        return ""

    stops = []
    start = 0.0
    for level in (1, 2, 3):
        count = counts.get(level, 0)
        if count <= 0:
            continue
        end = start + count / total * 100
        stops.append(f"{LEVEL_COLORS[level]} {start:.2f}% {end:.2f}%")
        start = end
    return f"background: conic-gradient({', '.join(stops)});"


# =============================================================================
# 风险得分计算
# =============================================================================

@dataclass(frozen=True)
class DualRiskScore:
    """Separate unusual-move strength from downside/event risk."""

    anomaly_score: int
    risk_score: int
    anomaly_label: str
    risk_label: str
    risk_range: str
    risk_color: str


def calculate_dual_risk_score(signals: Sequence[RiskSignal]) -> DualRiskScore:
    anomaly = _calculate_anomaly_score(signals)
    risk = _calculate_directional_risk_score(signals)
    risk_label, risk_color, risk_range = _get_risk_status(risk)
    return DualRiskScore(
        anomaly_score=anomaly,
        risk_score=risk,
        anomaly_label=_get_anomaly_status(anomaly),
        risk_label=risk_label,
        risk_range=risk_range,
        risk_color=risk_color,
    )


def _calculate_risk_score(signals: Sequence[RiskSignal]) -> int:
    """Backward-compatible risk score used by older tests/imports."""
    return calculate_dual_risk_score(signals).risk_score


def _calculate_anomaly_score(signals: Sequence[RiskSignal]) -> int:
    if not signals:
        return 12

    score = 15
    technical_only = True
    grouped: Dict[str, List[RiskSignal]] = {}
    for signal in signals:
        grouped.setdefault(signal.risk_type, []).append(signal)
        if not _is_technical_signal(signal.risk_type):
            technical_only = False

    for risk_type, items in grouped.items():
        weight = _anomaly_weight(risk_type)
        levels = sorted((max(0, min(item.level, 3)) for item in items), reverse=True)
        if not levels:
            continue
        score += weight * levels[0]
        for level in levels[1:]:
            score += weight * level * 0.25

    if len(grouped) >= 3:
        score += min((len(grouped) - 2) * 3, 6)

    if technical_only:
        cap = 72
    else:
        cap = 98
    return max(12, min(int(round(score)), cap))


def _calculate_directional_risk_score(signals: Sequence[RiskSignal]) -> int:
    if not signals:
        return 12

    score = 14
    grouped: Dict[str, List[RiskSignal]] = {}
    technical_only = True
    has_downside_or_event = False
    has_market_danger = False

    for signal in signals:
        grouped.setdefault(signal.risk_type, []).append(signal)
        if not _is_technical_signal(signal.risk_type):
            technical_only = False
        if _is_downside_or_event_signal(signal):
            has_downside_or_event = True
        if _is_market_signal(signal.risk_type) and signal.level >= 3:
            has_market_danger = True

    for risk_type, items in grouped.items():
        levels = sorted((max(0, min(item.level, 3)) for item in items), reverse=True)
        if not levels:
            continue
        weight = _risk_weight(risk_type, items)
        score += weight * levels[0]
        for level in levels[1:]:
            score += weight * level * 0.18

    if len(grouped) >= 3:
        score += min((len(grouped) - 2) * 2, 5)
    if has_downside_or_event:
        score += 6
    if has_market_danger and has_downside_or_event:
        score += 5

    if technical_only:
        cap = 60
    elif not has_downside_or_event:
        cap = 68
    elif not any(signal.level >= 3 for signal in signals):
        cap = 74
    else:
        cap = 98
    return max(12, min(int(round(score)), cap))


def _is_technical_signal(risk_type: str) -> bool:
    return any(name in risk_type for name in ("MACD", "RSI", "BOLL", "KDJ"))


def _is_market_signal(risk_type: str) -> bool:
    keywords = ("价格", "涨跌", "量比", "换手", "成交", "振幅", "波动")
    return any(keyword in risk_type for keyword in keywords)


def _anomaly_weight(risk_type: str) -> int:
    if "价格" in risk_type or "涨跌" in risk_type:
        return 18
    if "量比" in risk_type or "换手" in risk_type:
        return 14
    if "成交" in risk_type or "振幅" in risk_type or "波动" in risk_type:
        return 10
    if "MACD" in risk_type:
        return 11
    if "BOLL" in risk_type:
        return 10
    if "KDJ" in risk_type:
        return 9
    if "RSI" in risk_type:
        return 8
    return 9


def _risk_weight(risk_type: str, signals: Sequence[RiskSignal]) -> int:
    if _is_bullish_price_move(signals) and ("收益" in risk_type or "涨跌" in risk_type or "价格" in risk_type):
        return 9
    if "风险提示" in risk_type or "退市" in risk_type or "监管" in risk_type:
        return 20
    if "价格" in risk_type or "涨跌" in risk_type or "收益" in risk_type:
        return 15
    if "换手" in risk_type:
        return 13
    if "量比" in risk_type:
        return 11
    if "MACD" in risk_type or "BOLL" in risk_type:
        return 10
    if "KDJ" in risk_type:
        return 8
    if "RSI" in risk_type:
        return 7
    return 8


def _is_bullish_price_move(signals: Sequence[RiskSignal]) -> bool:
    text = " ".join(
        f"{signal.risk_type} {signal.description} {signal.deviation_value}"
        for signal in signals
    )
    if any(keyword in text for keyword in ("下跌", "跌停", "跑输", "回落", "走弱")):
        return False
    return any(keyword in text for keyword in ("上涨", "涨停", "跑赢", "涨幅"))


def _is_downside_or_event_signal(signal: RiskSignal) -> bool:
    text = f"{signal.risk_type} {signal.description}"
    downside_keywords = (
        "下跌",
        "跌停",
        "跑输",
        "走弱",
        "回撤",
        "顶背离",
        "死叉",
        "风险提示",
        "退市",
        "监管",
        "处罚",
        "预亏",
        "减持",
    )
    return any(keyword in text for keyword in downside_keywords)


def _get_anomaly_status(score: int) -> str:
    if score < 25:
        return "平稳"
    if score < 45:
        return "轻度异动"
    if score < 65:
        return "明显异动"
    if score < 80:
        return "强异动"
    return "极强异动"


def _get_risk_status(score: int) -> Tuple[str, str, str]:
    if score < 25:
        return "低风险", "#16794c", "0-25"
    elif score < 50:
        return "较低风险", "#d79b2b", "25-50"
    elif score < 75:
        return "中等偏高风险", "#d36b23", "50-75"
    elif score < 90:
        return "高风险", "#e64a19", "75-90"
    else:
        return "极高风险", "#c2412d", "90-100"


# =============================================================================
# 风险仪表盘

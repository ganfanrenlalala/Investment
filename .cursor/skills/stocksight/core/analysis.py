# -*- coding: utf-8 -*-
"""Technical analysis indicators for StockSight."""

from __future__ import annotations

from typing import List, Sequence

from .types import (
    BOLLResult,
    KDJResult,
    MACDResult,
    RSIResult,
    RiskSignal,
    StockHistory,
    TechnicalAnalysis,
    TechnicalSignal,
    TrendSummary,
)


DESC_BOLL_BREAK_UPPER = "BOLL 突破上轨：价格处于布林带上沿之外，短线过热风险上升。"
DESC_BOLL_NEAR_UPPER = "BOLL 贴近上轨：价格接近布林带上沿，需观察追高风险。"
DESC_BOLL_BREAK_LOWER = "BOLL 跌破下轨：价格处于布林带下沿之外，可能存在超跌修复需求。"
DESC_BOLL_NEAR_LOWER = "BOLL 贴近下轨：价格接近布林带下沿，短线波动需观察。"
DESC_KDJ_DEATH_CROSS = "KDJ 死叉：K 值下穿 D 值，短线动能转弱风险上升。"
DESC_KDJ_GOLDEN_CROSS = "KDJ 金叉：K 值上穿 D 值，短线动能有修复迹象。"
DESC_KDJ_OVERBOUGHT = "KDJ 超买：K/D 处于高位，需警惕短线回落风险。"
DESC_KDJ_OVERSOLD = "KDJ 超卖：K/D 处于低位，可能出现修复需求。"


def _ema(values: Sequence[float], period: int) -> List[float]:
    """Compute exponential moving average with an SMA seed."""
    if period <= 0 or len(values) < period:
        return [0.0] * len(values)
    multiplier = 2.0 / (period + 1)
    result = [0.0] * len(values)
    result[period - 1] = sum(values[:period]) / period
    for index in range(period, len(values)):
        result[index] = (values[index] - result[index - 1]) * multiplier + result[index - 1]
    return result


def compute_macd(history: StockHistory, fast: int = 12, slow: int = 26, signal: int = 9) -> MACDResult:
    """Calculate MACD from historical price bars."""
    if history is None or not history.bars or len(history.bars) < slow + signal - 1:
        return MACDResult()

    closes = [bar.close for bar in history.bars]
    dates = [bar.date for bar in history.bars]
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    dif = [0.0] * len(closes)
    for index in range(slow - 1, len(closes)):
        if ema_fast[index] and ema_slow[index]:
            dif[index] = ema_fast[index] - ema_slow[index]

    dea = _ema(dif, signal)
    dea_start = slow + signal - 2
    macd_hist = [0.0] * len(closes)
    for index in range(dea_start, len(closes)):
        macd_hist[index] = 2.0 * (dif[index] - dea[index])

    return MACDResult(
        dif=[round(value, 4) for value in dif],
        dea=[round(value, 4) for value in dea],
        macd=[round(value, 4) for value in macd_hist],
        dates=dates,
    )


def compute_rsi(history: StockHistory, period: int = 14) -> RSIResult:
    """Calculate RSI using Wilder smoothing."""
    if history is None or not history.bars or len(history.bars) <= period:
        return RSIResult(period=period)

    closes = [bar.close for bar in history.bars]
    dates = [bar.date for bar in history.bars]
    values = [0.0] * len(closes)
    gains: List[float] = []
    losses: List[float] = []

    for index in range(1, period + 1):
        change = closes[index] - closes[index - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    values[period] = _rsi_from_averages(avg_gain, avg_loss)

    for index in range(period + 1, len(closes)):
        change = closes[index] - closes[index - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        values[index] = _rsi_from_averages(avg_gain, avg_loss)

    return RSIResult(
        values=[round(value, 2) for value in values],
        dates=dates,
        period=period,
    )


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_boll(history: StockHistory, period: int = 20, width: float = 2.0) -> BOLLResult:
    """Calculate BOLL bands from closing prices."""
    if history is None or not history.bars or len(history.bars) < period:
        return BOLLResult(period=period)

    closes = [bar.close for bar in history.bars]
    dates = [bar.date for bar in history.bars]
    upper = [0.0] * len(closes)
    middle = [0.0] * len(closes)
    lower = [0.0] * len(closes)

    for index in range(period - 1, len(closes)):
        window = closes[index - period + 1:index + 1]
        mean = sum(window) / period
        variance = sum((value - mean) ** 2 for value in window) / period
        std = variance ** 0.5
        middle[index] = mean
        upper[index] = mean + width * std
        lower[index] = mean - width * std

    return BOLLResult(
        upper=[round(value, 4) for value in upper],
        middle=[round(value, 4) for value in middle],
        lower=[round(value, 4) for value in lower],
        dates=dates,
        period=period,
    )


def compute_kdj(history: StockHistory, period: int = 9) -> KDJResult:
    """Calculate KDJ with the common 9-day RSV and 1/3 smoothing."""
    if history is None or not history.bars or len(history.bars) < period:
        return KDJResult(period=period)

    bars = history.bars
    dates = [bar.date for bar in bars]
    k_values = [0.0] * len(bars)
    d_values = [0.0] * len(bars)
    j_values = [0.0] * len(bars)
    prev_k = 50.0
    prev_d = 50.0

    for index in range(period - 1, len(bars)):
        window = bars[index - period + 1:index + 1]
        low_n = min(bar.low for bar in window)
        high_n = max(bar.high for bar in window)
        close = bars[index].close
        rsv = 50.0 if high_n == low_n else (close - low_n) / (high_n - low_n) * 100
        k = prev_k * 2 / 3 + rsv / 3
        d = prev_d * 2 / 3 + k / 3
        j = 3 * k - 2 * d
        k_values[index] = k
        d_values[index] = d
        j_values[index] = j
        prev_k = k
        prev_d = d

    return KDJResult(
        k=[round(value, 2) for value in k_values],
        d=[round(value, 2) for value in d_values],
        j=[round(value, 2) for value in j_values],
        dates=dates,
        period=period,
    )


def detect_macd_signals(macd_result: MACDResult, lookback: int = 3) -> List[TechnicalSignal]:
    """Detect recent MACD golden/death crosses."""
    if not macd_result or len(macd_result.dif) < 3:
        return []

    dif = macd_result.dif
    dea = macd_result.dea
    dates = macd_result.dates
    start = max(1, len(dif) - max(1, lookback))
    signals: List[TechnicalSignal] = []

    for index in range(start, len(dif)):
        if dif[index] == 0 or dea[index] == 0 or dif[index - 1] == 0 or dea[index - 1] == 0:
            continue
        if dif[index - 1] <= dea[index - 1] and dif[index] > dea[index]:
            signals.append(TechnicalSignal(
                indicator="MACD",
                signal_type="golden_cross",
                level=0,
                direction="bullish",
                date=dates[index],
                value=dif[index] - dea[index],
                description=DESC_GOLDEN_CROSS,
            ))
        elif dif[index - 1] >= dea[index - 1] and dif[index] < dea[index]:
            signals.append(TechnicalSignal(
                indicator="MACD",
                signal_type="death_cross",
                level=2,
                direction="bearish",
                date=dates[index],
                value=dif[index] - dea[index],
                description=DESC_DEATH_CROSS,
            ))
    return signals


def detect_rsi_signals(rsi_result: RSIResult) -> List[TechnicalSignal]:
    """Detect RSI overbought/oversold states from the latest value."""
    latest = rsi_result.latest if rsi_result else None
    if latest is None or not rsi_result.dates:
        return []

    latest_date = rsi_result.dates[-1]
    if latest >= 80:
        return [_rsi_signal(latest_date, latest, 3, "overbought_extreme", DESC_RSI_OB_EXTREME)]
    if latest >= 70:
        return [_rsi_signal(latest_date, latest, 2, "overbought", DESC_RSI_OB)]
    if latest >= 60:
        return [_rsi_signal(latest_date, latest, 1, "heated", DESC_RSI_HEATED)]
    if latest <= 20:
        return [_rsi_signal(latest_date, latest, 2, "oversold_extreme", DESC_RSI_OS_EXTREME)]
    if latest <= 30:
        return [_rsi_signal(latest_date, latest, 1, "oversold", DESC_RSI_OS)]
    return []


def detect_boll_signals(boll_result: BOLLResult, history: StockHistory) -> List[TechnicalSignal]:
    """Detect price interaction with the latest BOLL bands."""
    latest = boll_result.latest if boll_result else None
    if latest is None or not boll_result.dates or not history or not history.bars:
        return []

    upper, middle, lower = latest
    if upper == 0.0 or middle == 0.0 or lower == 0.0:
        return []

    close = history.bars[-1].close
    latest_date = boll_result.dates[-1]
    band_width = max(upper - lower, 0.0001)
    position = (close - lower) / band_width

    if close > upper:
        return [_technical_signal("BOLL", "break_upper", 2, "bearish", latest_date, position, DESC_BOLL_BREAK_UPPER)]
    if close >= upper - band_width * 0.08:
        return [_technical_signal("BOLL", "near_upper", 1, "bearish", latest_date, position, DESC_BOLL_NEAR_UPPER)]
    if close < lower:
        return [_technical_signal("BOLL", "break_lower", 1, "bullish", latest_date, position, DESC_BOLL_BREAK_LOWER)]
    if close <= lower + band_width * 0.08:
        return [_technical_signal("BOLL", "near_lower", 1, "bullish", latest_date, position, DESC_BOLL_NEAR_LOWER)]
    return []


def detect_kdj_signals(kdj_result: KDJResult, lookback: int = 3) -> List[TechnicalSignal]:
    """Detect KDJ cross and high/low zone signals."""
    latest = kdj_result.latest if kdj_result else None
    if latest is None or len(kdj_result.k) < 2 or not kdj_result.dates:
        return []

    k_values = kdj_result.k
    d_values = kdj_result.d
    dates = kdj_result.dates
    signals: List[TechnicalSignal] = []
    start = max(1, len(k_values) - max(1, lookback))

    for index in range(start, len(k_values)):
        if not k_values[index] or not d_values[index] or not k_values[index - 1] or not d_values[index - 1]:
            continue
        if k_values[index - 1] >= d_values[index - 1] and k_values[index] < d_values[index]:
            signals.append(_technical_signal(
                "KDJ", "death_cross", 2, "bearish", dates[index],
                k_values[index] - d_values[index], DESC_KDJ_DEATH_CROSS,
            ))
        elif k_values[index - 1] <= d_values[index - 1] and k_values[index] > d_values[index]:
            signals.append(_technical_signal(
                "KDJ", "golden_cross", 0, "bullish", dates[index],
                k_values[index] - d_values[index], DESC_KDJ_GOLDEN_CROSS,
            ))

    latest_k, latest_d, latest_j = latest
    latest_date = dates[-1]
    if latest_k >= 80 and latest_d >= 75:
        signals.append(_technical_signal("KDJ", "overbought", 2, "bearish", latest_date, latest_j, DESC_KDJ_OVERBOUGHT))
    elif latest_k <= 20 and latest_d <= 25:
        signals.append(_technical_signal("KDJ", "oversold", 1, "bullish", latest_date, latest_j, DESC_KDJ_OVERSOLD))
    return signals[-3:]


def _rsi_signal(date: str, value: float, level: int, signal_type: str, description: str) -> TechnicalSignal:
    direction = "bullish" if "oversold" in signal_type else "bearish"
    return _technical_signal("RSI", signal_type, level, direction, date, value, description)


def _technical_signal(
    indicator: str,
    signal_type: str,
    level: int,
    direction: str,
    date: str,
    value: float,
    description: str,
) -> TechnicalSignal:
    return TechnicalSignal(
        indicator=indicator,
        signal_type=signal_type,
        level=level,
        direction=direction,
        date=date,
        value=round(value, 2),
        description=description,
    )


# ---------------------------------------------------------------------------
# Trend summary helpers  (MACD alignment, RSI trend, divergence)
# ---------------------------------------------------------------------------

DESC_GOLDEN_CROSS = "MACD \u91d1\u53c9\uff1aDIF \u4e0a\u7a7f DEA\uff0c\u77ed\u7ebf\u504f\u591a\u3002"
DESC_DEATH_CROSS = "MACD \u6b7b\u53c9\uff1aDIF \u4e0b\u7a7f DEA\uff0c\u77ed\u7ebf\u8f6c\u5f31\u98ce\u9669\u5347\u9ad8\u3002"
DESC_RSI_OB_EXTREME = "\u6781\u5ea6\u8d85\u4e70\uff1aRSI \u9ad8\u4e8e 80\uff0c\u77ed\u7ebf\u56de\u64a4\u98ce\u9669\u8f83\u9ad8\u3002"
DESC_RSI_OB = "\u8d85\u4e70\uff1aRSI \u9ad8\u4e8e 70\uff0c\u9700\u8b66\u60d5\u8ffd\u9ad8\u98ce\u9669\u3002"
DESC_RSI_HEATED = "\u504f\u70ed\uff1aRSI \u9ad8\u4e8e 60\uff0c\u52a8\u80fd\u504f\u5f3a\u4f46\u9700\u89c2\u5bdf\u6301\u7eed\u6027\u3002"
DESC_RSI_OS_EXTREME = "\u6781\u5ea6\u8d85\u5356\uff1aRSI \u4f4e\u4e8e 20\uff0c\u8d8b\u52bf\u538b\u529b\u4ecd\u9700\u89c2\u5bdf\u3002"
DESC_RSI_OS = "\u8d85\u5356\u89c2\u5bdf\uff1aRSI \u4f4e\u4e8e 30\uff0c\u53ef\u80fd\u51fa\u73b0\u4fee\u590d\u9700\u6c42\u3002"


def _last_valid(values: List[float], default: float = 0.0) -> float:
    """Get the last non-zero value from a list."""
    for v in reversed(values):
        if v != 0.0:
            return v
    return default


def _macd_trend_summary(macd_result: MACDResult) -> tuple:
    """Judge MACD alignment and histogram trend.

    Returns:
        (alignment, alignment_desc, histogram_trend)
    """
    if not macd_result or len(macd_result.dif) < 3:
        return ("", "", "")

    valid_dif = [v for v in macd_result.dif if v != 0.0]
    valid_dea = [v for v in macd_result.dea if v != 0.0]
    valid_hist = [v for v in macd_result.macd if v != 0.0]

    if len(valid_dif) < 3 or len(valid_dea) < 3 or len(valid_hist) < 3:
        return ("", "", "")

    d0, d1, d2 = valid_dif[-1], valid_dif[-2], valid_dif[-3]
    e0, e1, e2 = valid_dea[-1], valid_dea[-2], valid_dea[-3]
    h0, h1, h2 = valid_hist[-1], valid_hist[-2], valid_hist[-3]

    # --- MACD alignment ---
    bullish_streak = (d0 > e0) and (d1 > e1) and (d2 > e2)
    bearish_streak = (d0 < e0) and (d1 < e1) and (d2 < e2)

    if bullish_streak and d0 > 0 and e0 > 0:
        alignment = "bullish"
        alignment_desc = f"\u591a\u5934\u6392\u5217\uff1aDIF({d0:.4f}) > DEA({e0:.4f}) > 0\uff0c\u52a8\u80fd\u504f\u591a"
    elif bullish_streak:
        alignment = "bullish"
        alignment_desc = f"\u591a\u5934\u6392\u5217\uff1aDIF({d0:.4f}) > DEA({e0:.4f})\uff0c\u77ed\u7ebf\u504f\u591a"
    elif bearish_streak and d0 < 0 and e0 < 0:
        alignment = "bearish"
        alignment_desc = f"\u7a7a\u5934\u6392\u5217\uff1aDIF({d0:.4f}) < DEA({e0:.4f}) < 0\uff0c\u52a8\u80fd\u504f\u7a7a"
    elif bearish_streak:
        alignment = "bearish"
        alignment_desc = f"\u7a7a\u5934\u6392\u5217\uff1aDIF({d0:.4f}) < DEA({e0:.4f})\uff0c\u77ed\u7ebf\u504f\u7a7a"
    else:
        gap_before = abs(d2 - e2)
        gap_now = abs(d0 - e0)
        if gap_now < gap_before * 0.6 and gap_now < 0.002:
            if d0 > e0 and d2 < e2:
                alignment = "turning"
                alignment_desc = "DIF \u4e0a\u7a7f DEA \u9644\u8fd1\uff0c\u5bc6\u5207\u5173\u6ce8\u80fd\u5426\u5f62\u6210\u91d1\u53c9"
            elif d0 < e0 and d2 > e2:
                alignment = "turning"
                alignment_desc = "DIF \u4e0b\u7a7f DEA \u9644\u8fd1\uff0c\u6ce8\u610f\u6b7b\u53c9\u98ce\u9669"
            else:
                alignment = "turning"
                alignment_desc = f"DIF/DEA \u5373\u5c06\u4ea4\u53c9\uff08\u5f53\u524d\u95f4\u8ddd {gap_now:.4f}\uff09\uff0c\u6301\u7eed\u5173\u6ce8"
        else:
            alignment = "neutral"
            alignment_desc = f"DIF({d0:.4f}) / DEA({e0:.4f})\uff0c\u6392\u5217\u4e0d\u660e\u786e"

    # --- Histogram trend ---
    abs_h0, abs_h1, abs_h2 = abs(h0), abs(h1), abs(h2)
    if abs_h2 > 0 and abs_h1 > 0 and abs_h0 > 0:
        if abs_h0 > abs_h1 * 1.05 and abs_h1 > abs_h2 * 1.05:
            histogram_trend = "expanding"
        elif abs_h0 < abs_h1 * 0.95 and abs_h1 < abs_h2 * 0.95:
            histogram_trend = "contracting"
        else:
            histogram_trend = "flat"
    else:
        histogram_trend = "flat"

    return (alignment, alignment_desc, histogram_trend)


def _rsi_trend_summary(rsi_result: RSIResult) -> tuple:
    """Judge RSI trend state.

    Returns:
        (rsi_trend, rsi_trend_desc)
    """
    if not rsi_result or rsi_result.latest is None:
        return ("", "")

    valid = [v for v in rsi_result.values if v != 0.0]
    if len(valid) < 5:
        return ("", "")

    v0, v1, v2, v3, v4 = valid[-1], valid[-2], valid[-3], valid[-4], valid[-5]

    recent_high = max(v4, v3, v2, v1, v0)
    if recent_high >= 70 and v0 < v1 < v2 and v0 <= v1 * 0.97:
        return ("overbought_pullback",
                f"RSI \u8d85\u4e70\u540e\u56de\u843d\uff1a\u4ece {recent_high:.1f} \u56de\u843d\u81f3 {v0:.1f}\uff0c\u77ed\u7ebf\u52a8\u80fd\u51cf\u5f31")

    recent_low = min(v4, v3, v2, v1, v0)
    if recent_low <= 30 and v0 > v1 > v2:
        return ("oversold_bounce",
                f"RSI \u8d85\u5356\u540e\u53cd\u5f39\uff1a\u4ece {recent_low:.1f} \u56de\u5347\u81f3 {v0:.1f}\uff0c\u77ed\u7ebf\u4fee\u590d\u4e2d")

    if v0 > v1 > v2 and v0 > v3 and v0 > v4:
        return ("uptrend",
                f"RSI \u6301\u7eed\u8d70\u9ad8\uff08{v2:.1f} \u2192 {v1:.1f} \u2192 {v0:.1f}\uff09\uff0c\u591a\u5934\u52a8\u80fd\u589e\u5f3a")
    if v0 < v1 < v2 and v0 < v3 and v0 < v4:
        return ("downtrend",
                f"RSI \u6301\u7eed\u8d70\u4f4e\uff08{v2:.1f} \u2192 {v1:.1f} \u2192 {v0:.1f}\uff09\uff0c\u7a7a\u5934\u52a8\u80fd\u589e\u5f3a")

    if v0 > 60:
        return ("heated",
                f"RSI({v0:.1f}) \u5904\u4e8e\u504f\u9ad8\u533a\u57df\uff0c\u9700\u89c2\u5bdf\u662f\u5426\u8d85\u4e70")
    if v0 < 40:
        return ("cooling",
                f"RSI({v0:.1f}) \u5904\u4e8e\u504f\u4f4e\u533a\u57df\uff0c\u9700\u89c2\u5bdf\u662f\u5426\u8d85\u5356")
    return ("neutral",
            f"RSI({v0:.1f}) \u5904\u4e8e\u4e2d\u6027\u533a\u57df\uff0c\u8d8b\u52bf\u4e0d\u660e\u786e")


def _detect_divergence(history: StockHistory, macd_result: MACDResult) -> tuple:
    """Detect price-MACD divergence.

    Scans the last 30 bars for local peaks/troughs.
    Bearish divergence = price higher high, DIF lower high
    Bullish divergence = price lower low, DIF higher low

    Returns:
        (divergence, divergence_desc)
    """
    if not history or not macd_result or len(macd_result.dif) < 15:
        return ("", "")

    closes = [bar.close for bar in history.bars]
    dif = list(macd_result.dif)
    dates = list(macd_result.dates)

    start = 0
    for i, v in enumerate(dif):
        if v != 0.0:
            start = i
            break
    if len(closes) - start < 15:
        return ("", "")

    window = min(30, len(closes) - start)
    closes_look = closes[-window:]
    dif_look = dif[-window:]
    dates_look = dates[-window:]

    peaks = []
    troughs = []
    for i in range(1, len(closes_look) - 1):
        if closes_look[i] > closes_look[i - 1] and closes_look[i] > closes_look[i + 1]:
            if dif_look[i] != 0.0:
                peaks.append((i, closes_look[i], dif_look[i], dates_look[i]))
        if closes_look[i] < closes_look[i - 1] and closes_look[i] < closes_look[i + 1]:
            if dif_look[i] != 0.0:
                troughs.append((i, closes_look[i], dif_look[i], dates_look[i]))

    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if p2[1] > p1[1] and p2[2] < p1[2] and abs(p2[2] - p1[2]) > 0.0001:
            return (
                "bearish",
                f"\u9876\u80cc\u79bb\uff1a\u4ef7\u683c\u521b\u9636\u6bb5\u65b0\u9ad8\uff08{p1[1]:.2f} \u2192 {p2[1]:.2f}\uff09\uff0c"
                f"\u4f46 MACD DIF \u672a\u540c\u6b65\u521b\u65b0\u9ad8\uff08{p1[2]:.4f} \u2192 {p2[2]:.4f}\uff09\uff0c\u89c1\u9876\u98ce\u9669\u9700\u8b66\u60d5"
            )

    if len(troughs) >= 2:
        t1, t2 = troughs[-2], troughs[-1]
        if t2[1] < t1[1] and t2[2] > t1[2] and abs(t2[2] - t1[2]) > 0.0001:
            return (
                "bullish",
                f"\u5e95\u80cc\u79bb\uff1a\u4ef7\u683c\u521b\u9636\u6bb5\u65b0\u4f4e\uff08{t1[1]:.2f} \u2192 {t2[1]:.2f}\uff09\uff0c"
                f"\u4f46 MACD DIF \u672a\u540c\u6b65\u521b\u65b0\u4f4e\uff08{t1[2]:.4f} \u2192 {t2[2]:.4f}\uff09\uff0c\u5e95\u90e8\u4f01\u7a33\u4fe1\u53f7"
            )

    return ("", "")


def _build_trend_summary(macd_result: MACDResult, rsi_result: RSIResult, history: StockHistory) -> TrendSummary:
    """Combine trend detections into a TrendSummary."""
    alignment, alignment_desc, hist_trend = _macd_trend_summary(macd_result)
    rsi_trend, rsi_trend_desc = _rsi_trend_summary(rsi_result)
    divergence, divergence_desc = _detect_divergence(history, macd_result)

    return TrendSummary(
        macd_alignment=alignment,
        macd_alignment_desc=alignment_desc,
        macd_histogram_trend=hist_trend,
        rsi_trend=rsi_trend,
        rsi_trend_desc=rsi_trend_desc,
        divergence=divergence,
        divergence_desc=divergence_desc,
    )


# ---------------------------------------------------------------------------
# Main analysis entry
# ---------------------------------------------------------------------------

def analyze_technical_indicators(history: StockHistory) -> TechnicalAnalysis:
    """Compute technical indicators, trend summary, and technical signals."""
    if history is None or not history.bars:
        return TechnicalAnalysis(notes=["历史数据不足，无法计算 MACD/RSI/BOLL/KDJ。"])

    macd = compute_macd(history)
    rsi = compute_rsi(history)
    boll = compute_boll(history)
    kdj = compute_kdj(history)
    signals = (
        detect_macd_signals(macd, lookback=5)
        + detect_rsi_signals(rsi)
        + detect_boll_signals(boll, history)
        + detect_kdj_signals(kdj, lookback=5)
    )
    notes: List[str] = []
    if not macd.dates:
        notes.append("MACD 历史数据不足。")
    if rsi.latest is None:
        notes.append("RSI 历史数据不足。")
    if boll.latest is None:
        notes.append("BOLL 历史数据不足。")
    if kdj.latest is None:
        notes.append("KDJ 历史数据不足。")

    trend = _build_trend_summary(macd, rsi, history)
    if trend.divergence:
        signals.append(TechnicalSignal(
            indicator="MACD",
            signal_type=f"{trend.divergence}_divergence",
            level=2 if trend.divergence == "bearish" else 1,
            direction="bearish" if trend.divergence == "bearish" else "bullish",
            date=macd.dates[-1] if macd.dates else "",
            value=0.0,
            description=trend.divergence_desc,
        ))

    return TechnicalAnalysis(macd=macd, rsi=rsi, boll=boll, kdj=kdj, signals=signals, notes=notes, trend=trend)


def technical_risk_signals(analysis: TechnicalAnalysis, stock_code: str) -> List[RiskSignal]:
    """Convert risk-bearing technical signals into standard RiskSignal entries."""
    if not analysis or not analysis.signals:
        return []
    signals: List[RiskSignal] = []
    for item in analysis.signals:
        if item.level <= 0 or item.direction == "bullish":
            continue
        signals.append(RiskSignal(
            stock_code=stock_code,
            risk_type=f"{item.indicator}\u6280\u672f\u4fe1\u53f7",
            level=item.level,
            deviation_value=item.value,
            deviation_unit="" if item.indicator == "MACD" else "",
            description=item.description,
        ))
    return signals

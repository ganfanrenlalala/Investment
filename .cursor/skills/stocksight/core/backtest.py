# -*- coding: utf-8 -*-
"""Point-in-time swing backtesting and probability calibration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
from statistics import mean, median
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .analysis import analyze_technical_indicators, technical_risk_signals
from .detector import detect
from .strategy import SWING_STRATEGY_VERSION, StrategyDecision, evaluate_strategy_action
from .types import HistoryBar, StockData, StockHistory, StrategyPerformance


CALIBRATION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class BacktestConfig:
    """Transparent assumptions for the event-style backtest."""

    horizons: Tuple[int, ...] = (5, 10, 20)
    primary_horizon: int = 10
    warmup_bars: int = 60
    total_cost_bps: float = 10.0
    train_fraction: float = 0.70
    minimum_bucket_samples: int = 20


@dataclass(frozen=True)
class BacktestObservation:
    code: str
    signal_date: str
    entry_date: str
    action: str
    tone: str
    score: Optional[float]
    score_max: Optional[float]
    entry_price: float
    returns: Dict[str, float]
    primary_return: float
    maximum_favorable_excursion: float
    maximum_adverse_excursion: float


@dataclass
class BacktestResult:
    config: BacktestConfig
    observations: List[BacktestObservation] = field(default_factory=list)
    calibration: Dict[str, object] = field(default_factory=dict)


def run_swing_backtest(
    histories: Mapping[str, StockHistory],
    config: Optional[BacktestConfig] = None,
) -> BacktestResult:
    """Backtest first transitions into each swing state without lookahead."""
    config = config or BacktestConfig()
    if config.primary_horizon not in config.horizons:
        raise ValueError("primary_horizon must be included in horizons")
    if not 0.5 <= config.train_fraction < 1:
        raise ValueError("train_fraction must be between 0.5 and 1")

    observations: List[BacktestObservation] = []
    for code, history in histories.items():
        observations.extend(_observations_for_history(code, history, config))
    observations.sort(key=lambda item: (item.signal_date, item.code))

    calibration = build_calibration_artifact(observations, config)
    return BacktestResult(
        config=config,
        observations=observations,
        calibration=calibration,
    )


def _observations_for_history(
    code: str,
    history: StockHistory,
    config: BacktestConfig,
) -> List[BacktestObservation]:
    bars = _clean_bars(history.bars)
    max_horizon = max(config.horizons)
    last_signal_index = len(bars) - max_horizon - 1
    if last_signal_index < config.warmup_bars - 1:
        return []

    observations: List[BacktestObservation] = []
    previous_action: Optional[str] = None
    for index in range(config.warmup_bars - 1, last_signal_index + 1):
        prefix = StockHistory(code=code, bars=bars[: index + 1])
        technical = analyze_technical_indicators(prefix)
        stock = _stock_from_bar(code, bars, index)
        signals = detect([stock])
        signals.extend(technical_risk_signals(technical, code))
        decision = evaluate_strategy_action(
            stock,
            signals,
            technical,
            news=[],
            profile="swing",
        )

        if previous_action is None:
            previous_action = decision.action
            continue
        is_transition = decision.action != previous_action
        previous_action = decision.action
        if not is_transition:
            continue

        observation = _build_observation(code, bars, index, decision, config)
        if observation is not None:
            observations.append(observation)
    return observations


def _clean_bars(bars: Iterable[HistoryBar]) -> List[HistoryBar]:
    by_date: Dict[str, HistoryBar] = {}
    for bar in bars or []:
        if not bar.date or bar.close <= 0:
            continue
        by_date[bar.date] = bar
    return [by_date[key] for key in sorted(by_date)]


def _stock_from_bar(code: str, bars: Sequence[HistoryBar], index: int) -> StockData:
    bar = bars[index]
    previous_close = bars[index - 1].close if index > 0 else bar.open
    change_percent = bar.change_percent
    if not change_percent and previous_close > 0:
        change_percent = (bar.close / previous_close - 1) * 100

    prior_volumes = [
        item.volume
        for item in bars[max(0, index - 5) : index]
        if item.volume > 0
    ]
    average_volume = mean(prior_volumes) if prior_volumes else 0.0
    volume_ratio = bar.volume / average_volume if average_volume > 0 else 0.0

    return StockData(
        code=code,
        name=code,
        current_price=bar.close,
        prev_close=previous_close,
        open_price=bar.open,
        high=bar.high,
        low=bar.low,
        volume=bar.volume,
        amount=bar.amount,
        volume_ratio=volume_ratio,
        change_percent=change_percent,
        turnover_rate=bar.turnover_rate,
        timestamp=f"{bar.date} 15:00:00",
        market=_market_for_code(code),
        raw={"historical_reconstruction": True},
    )


def _market_for_code(code: str) -> str:
    normalized = code.strip().upper()
    if normalized.isalpha():
        return "us"
    if normalized.startswith("6"):
        return "sh"
    if len(normalized) == 6:
        return "sz"
    return ""


def _build_observation(
    code: str,
    bars: Sequence[HistoryBar],
    signal_index: int,
    decision: StrategyDecision,
    config: BacktestConfig,
) -> Optional[BacktestObservation]:
    entry_index = signal_index + 1
    entry = bars[entry_index]
    entry_price = entry.open if entry.open > 0 else entry.close
    if entry_price <= 0:
        return None

    cost_rate = config.total_cost_bps / 10000.0
    returns: Dict[str, float] = {}
    for horizon in config.horizons:
        exit_index = entry_index + horizon - 1
        exit_price = bars[exit_index].close
        returns[str(horizon)] = (exit_price / entry_price - 1 - cost_rate) * 100

    primary_exit = entry_index + config.primary_horizon - 1
    holding_bars = bars[entry_index : primary_exit + 1]
    mfe = (max(item.high for item in holding_bars) / entry_price - 1) * 100
    mae = (min(item.low for item in holding_bars) / entry_price - 1) * 100

    return BacktestObservation(
        code=code,
        signal_date=bars[signal_index].date,
        entry_date=entry.date,
        action=decision.action,
        tone=decision.tone,
        score=decision.score,
        score_max=decision.score_max,
        entry_price=entry_price,
        returns=returns,
        primary_return=returns[str(config.primary_horizon)],
        maximum_favorable_excursion=mfe,
        maximum_adverse_excursion=mae,
    )


def build_calibration_artifact(
    observations: Sequence[BacktestObservation],
    config: BacktestConfig,
) -> Dict[str, object]:
    """Create a deployment mapping with chronological holdout diagnostics."""
    ordered = sorted(observations, key=lambda item: (item.signal_date, item.code))
    split_index = max(1, min(len(ordered) - 1, int(len(ordered) * config.train_fraction))) if len(ordered) > 1 else len(ordered)
    train = ordered[:split_index]
    test = ordered[split_index:]
    evaluation_mapping = _build_mapping(train, config.minimum_bucket_samples)

    predictions: List[float] = []
    labels: List[int] = []
    for item in test:
        estimate = _lookup_mapping(evaluation_mapping, item.action, item.score)
        predictions.append(float(estimate["probability_positive"]))
        labels.append(1 if item.primary_return > 0 else 0)
    train_labels = [1 if item.primary_return > 0 else 0 for item in train]
    baseline_probability = (
        (sum(train_labels) + 1) / (len(train_labels) + 2)
        if train_labels
        else 0.5
    )
    baseline_predictions = [baseline_probability] * len(labels)
    model_brier = _brier_score(predictions, labels)
    baseline_brier = _brier_score(baseline_predictions, labels)
    brier_skill = (
        1 - model_brier / baseline_brier
        if model_brier is not None and baseline_brier not in (None, 0)
        else None
    )

    deploy_mapping = _build_mapping(ordered, config.minimum_bucket_samples)
    return {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "profile": "swing",
        "strategy_version": SWING_STRATEGY_VERSION,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "primary_horizon_days": config.primary_horizon,
        "horizons": list(config.horizons),
        "total_cost_bps": config.total_cost_bps,
        "signal_policy": "first_state_transition",
        "entry_policy": "next_trading_day_open",
        "exit_policy": "fixed_horizon_close",
        "historical_volume_ratio_policy": "daily_volume_divided_by_prior_5_day_average",
        "sample_size": len(ordered),
        "symbols": sorted({item.code for item in ordered}),
        "date_range": {
            "start": ordered[0].signal_date if ordered else "",
            "end": ordered[-1].signal_date if ordered else "",
        },
        "holdout": {
            "train_size": len(train),
            "test_size": len(test),
            "brier_score": model_brier,
            "baseline_brier_score": baseline_brier,
            "brier_skill_score": brier_skill,
            "expected_calibration_error": _expected_calibration_error(predictions, labels),
            "positive_rate": mean(labels) if labels else None,
        },
        "mapping": deploy_mapping,
        "action_summary": _group_summary(ordered, lambda item: item.action),
        "score_summary": _group_summary(
            [item for item in ordered if item.score is not None],
            lambda item: _score_key(item.score),
        ),
    }


def _build_mapping(
    observations: Sequence[BacktestObservation],
    minimum_bucket_samples: int,
) -> Dict[str, object]:
    exact: Dict[str, List[BacktestObservation]] = {}
    actions: Dict[str, List[BacktestObservation]] = {}
    scores: Dict[str, List[BacktestObservation]] = {}
    for item in observations:
        action_key = item.action
        score_key = _score_key(item.score)
        exact.setdefault(f"{action_key}|{score_key}", []).append(item)
        actions.setdefault(action_key, []).append(item)
        scores.setdefault(score_key, []).append(item)

    return {
        "minimum_bucket_samples": minimum_bucket_samples,
        "exact": {key: _stats(items) for key, items in exact.items()},
        "actions": {key: _stats(items) for key, items in actions.items()},
        "scores": {key: _stats(items) for key, items in scores.items()},
        "global": _stats(list(observations)),
    }


def _lookup_mapping(
    mapping: Mapping[str, object],
    action: str,
    score: Optional[float],
) -> Dict[str, object]:
    minimum = int(mapping.get("minimum_bucket_samples", 20))
    score_key = _score_key(score)
    candidates = [
        ("动作 + 评分", f"{action}|{score_key}", (mapping.get("exact") or {}).get(f"{action}|{score_key}")),
        ("动作", action, (mapping.get("actions") or {}).get(action)),
        ("评分", score_key, (mapping.get("scores") or {}).get(score_key)),
        ("全局基准", "global", mapping.get("global")),
    ]
    for basis, key, candidate in candidates:
        if candidate and int(candidate.get("sample_size", 0)) >= minimum:
            result = dict(candidate)
            result["match_basis"] = basis
            result["match_key"] = key
            return result
    for basis, key, candidate in candidates:
        if candidate:
            result = dict(candidate)
            result["match_basis"] = basis
            result["match_key"] = key
            return result
    result = _stats([])
    result["match_basis"] = "无匹配"
    result["match_key"] = ""
    return result


def _score_key(score: Optional[float]) -> str:
    return "unknown" if score is None else str(int(round(score)))


def _stats(items: Sequence[BacktestObservation]) -> Dict[str, object]:
    values = [item.primary_return for item in items]
    wins = sum(value > 0 for value in values)
    sample_size = len(values)
    probability = (wins + 1) / (sample_size + 2)
    return {
        "sample_size": sample_size,
        "positive_count": wins,
        "probability_positive": probability,
        "mean_return": mean(values) if values else 0.0,
        "median_return": median(values) if values else 0.0,
        "mean_mfe": mean(item.maximum_favorable_excursion for item in items) if items else 0.0,
        "mean_mae": mean(item.maximum_adverse_excursion for item in items) if items else 0.0,
    }


def _group_summary(items, key_fn) -> Dict[str, Dict[str, object]]:
    grouped: Dict[str, List[BacktestObservation]] = {}
    for item in items:
        grouped.setdefault(str(key_fn(item)), []).append(item)
    return {key: _stats(group) for key, group in sorted(grouped.items())}


def _brier_score(predictions: Sequence[float], labels: Sequence[int]) -> Optional[float]:
    if not predictions:
        return None
    return mean((prediction - label) ** 2 for prediction, label in zip(predictions, labels))


def _expected_calibration_error(
    predictions: Sequence[float],
    labels: Sequence[int],
) -> Optional[float]:
    if not predictions:
        return None
    bins: Dict[int, List[Tuple[float, int]]] = {}
    for prediction, label in zip(predictions, labels):
        bin_index = min(9, int(prediction * 10))
        bins.setdefault(bin_index, []).append((prediction, label))
    total = len(predictions)
    return sum(
        len(items) / total
        * abs(mean(item[0] for item in items) - mean(item[1] for item in items))
        for items in bins.values()
    )


def estimate_strategy_performance(
    artifact: Mapping[str, object],
    decision: StrategyDecision,
    source: str = "",
) -> StrategyPerformance:
    """Match a live decision to a calibration bucket."""
    profile = str(artifact.get("profile", ""))
    version = str(artifact.get("strategy_version", ""))
    if profile != "swing":
        raise ValueError("calibration profile must be swing")
    if version != SWING_STRATEGY_VERSION:
        raise ValueError(
            f"incompatible strategy version: expected {SWING_STRATEGY_VERSION}, got {version or 'missing'}"
        )
    mapping = artifact.get("mapping")
    if not isinstance(mapping, Mapping):
        raise ValueError("calibration mapping is missing")
    stats = _lookup_mapping(mapping, decision.action, decision.score)
    sample_size = int(stats.get("sample_size", 0))
    match_basis = str(stats.get("match_basis", ""))
    reliability = "基准" if match_basis == "全局基准" else _reliability(sample_size)
    note = "样本外验证通过时间切分完成；当前概率映射在验证后使用全样本重估。"
    if match_basis == "全局基准":
        note = "当前动作/评分样本不足，概率已回退到全局基准，不应视为该动作的专属胜率。"
    if reliability == "不足":
        note = "匹配样本过少，仅展示基准概率，不应据此扩大仓位。"
    return StrategyPerformance(
        profile=profile,
        strategy_version=version,
        horizon_days=int(artifact.get("primary_horizon_days", 10)),
        probability_positive=float(stats.get("probability_positive", 0.5)),
        sample_size=sample_size,
        reliability=reliability,
        mean_return=float(stats.get("mean_return", 0.0)),
        median_return=float(stats.get("median_return", 0.0)),
        action=decision.action,
        score=decision.score,
        score_max=decision.score_max,
        source=source,
        generated_at=str(artifact.get("generated_at", "")),
        match_basis=match_basis,
        note=note,
    )


def _reliability(sample_size: int) -> str:
    if sample_size >= 100:
        return "较高"
    if sample_size >= 30:
        return "中等"
    if sample_size >= 10:
        return "较低"
    return "不足"


def load_calibration(path: Path) -> Dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read calibration file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid calibration JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("calibration file must contain a JSON object")
    if payload.get("schema_version") != CALIBRATION_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported calibration schema: {payload.get('schema_version', 'missing')}"
        )
    return payload


def save_calibration(path: Path, artifact: Mapping[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path.resolve()


def render_backtest_markdown(result: BacktestResult) -> str:
    artifact = result.calibration
    holdout = artifact.get("holdout") or {}
    lines = [
        "# StockSight Swing 策略回测与校准",
        "",
        "> 信号在收盘形成，次交易日开盘进入；仅记录策略状态首次切换，避免连续信号重复计样本。",
        "",
        "## 回测口径",
        "",
        f"- 策略版本：`{artifact.get('strategy_version', '')}`",
        f"- 样本数：{artifact.get('sample_size', 0)}",
        f"- 标的数：{len(artifact.get('symbols') or [])}",
        f"- 日期范围：{(artifact.get('date_range') or {}).get('start', '—')} 至 {(artifact.get('date_range') or {}).get('end', '—')}",
        f"- 主要观察周期：{artifact.get('primary_horizon_days', 10)} 个交易日",
        f"- 往返成本假设：{artifact.get('total_cost_bps', 0):.1f} bps",
        "",
        "## 样本外校准",
        "",
        "| 训练样本 | 测试样本 | Brier | 基准Brier | Brier Skill | ECE | 测试集上涨率 |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {holdout.get('train_size', 0)} | {holdout.get('test_size', 0)} | "
            f"{_fmt_optional(holdout.get('brier_score'))} | "
            f"{_fmt_optional(holdout.get('baseline_brier_score'))} | "
            f"{_fmt_optional(holdout.get('brier_skill_score'))} | "
            f"{_fmt_optional(holdout.get('expected_calibration_error'))} | "
            f"{_fmt_percent(holdout.get('positive_rate'))} |"
        ),
        "",
        "## 动作表现",
        "",
        "| 动作 | 样本 | 10日上涨概率 | 平均净收益 | 中位净收益 | 平均MFE | 平均MAE |",
        "|:---|---:|---:|---:|---:|---:|---:|",
    ]
    for action, stats in (artifact.get("action_summary") or {}).items():
        lines.append(
            f"| {action} | {stats['sample_size']} | "
            f"{float(stats['probability_positive']) * 100:.1f}% | "
            f"{float(stats['mean_return']):+.2f}% | "
            f"{float(stats['median_return']):+.2f}% | "
            f"{float(stats['mean_mfe']):+.2f}% | "
            f"{float(stats['mean_mae']):+.2f}% |"
        )
    lines.extend(
        [
            "",
            "## 评分表现",
            "",
            "| Swing评分 | 样本 | 10日上涨概率 | 平均净收益 | 中位净收益 |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for score, stats in (artifact.get("score_summary") or {}).items():
        lines.append(
            f"| {score} | {stats['sample_size']} | "
            f"{float(stats['probability_positive']) * 100:.1f}% | "
            f"{float(stats['mean_return']):+.2f}% | "
            f"{float(stats['median_return']):+.2f}% |"
        )
    lines.extend(
        [
            "",
            "> 概率采用 Beta(1,1) 平滑。校准文件只与相同策略版本兼容；样本表现不代表未来收益。",
        ]
    )
    return "\n".join(lines)


def _fmt_optional(value: object) -> str:
    return "—" if value is None else f"{float(value):.4f}"


def _fmt_percent(value: object) -> str:
    return "—" if value is None else f"{float(value) * 100:.1f}%"


def observations_as_dicts(
    observations: Sequence[BacktestObservation],
) -> List[Dict[str, object]]:
    return [asdict(item) for item in observations]

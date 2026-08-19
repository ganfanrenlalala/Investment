#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run reproducible StockSight swing backtests and create calibration files."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, fields
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import (  # noqa: E402
    BacktestConfig,
    HistoryBar,
    StockHistory,
    render_backtest_markdown,
    run_swing_backtest,
    save_calibration,
)
from providers import (  # noqa: E402
    AShareHistoryDataSource,
    EastMoneyDataSource,
    YahooFinanceDataSource,
)


CACHE_SCHEMA_VERSION = 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backtest and calibrate the StockSight swing strategy.",
    )
    parser.add_argument("codes", nargs="*", help="Stock codes or US tickers.")
    parser.add_argument(
        "--codes-file",
        type=Path,
        help="Optional UTF-8 text file containing codes separated by commas or newlines.",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "eastmoney", "yahoo"],
        default="auto",
        help="Historical data provider. auto selects Yahoo for alphabetic tickers and EastMoney for A-shares.",
    )
    parser.add_argument("--days", type=int, default=800, help="Requested trading-day history per symbol.")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("backtest-cache"),
        help="Versioned local history cache directory.",
    )
    parser.add_argument("--refresh", action="store_true", help="Ignore cache and refetch history.")
    parser.add_argument(
        "--cost-bps",
        type=float,
        default=10.0,
        help="Total round-trip transaction cost in basis points.",
    )
    parser.add_argument(
        "--train-fraction",
        type=float,
        default=0.70,
        help="Chronological fraction used to fit holdout calibration.",
    )
    parser.add_argument(
        "--minimum-bucket-samples",
        type=int,
        default=20,
        help="Minimum samples before using an action/score calibration bucket.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/backtests/swing-backtest.md"),
        help="Markdown backtest report path.",
    )
    parser.add_argument(
        "--calibration-out",
        type=Path,
        default=Path("outputs/backtests/swing-calibration.json"),
        help="Calibration JSON consumed by scripts/report.py.",
    )
    parser.add_argument(
        "--trades-out",
        type=Path,
        default=Path("outputs/backtests/swing-observations.csv"),
        help="CSV event ledger path.",
    )
    return parser


def _normalize_codes(values: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        for token in value.replace(",", " ").split():
            code = token.strip().upper()
            if code and code not in seen:
                seen.add(code)
                result.append(code)
    return result


def _codes_from_args(args) -> List[str]:
    values = list(args.codes)
    if args.codes_file:
        values.append(args.codes_file.read_text(encoding="utf-8"))
    return _normalize_codes(values)


def _provider_name(code: str, requested: str) -> str:
    if requested != "auto":
        return requested
    return "yahoo" if any(character.isalpha() for character in code) else "eastmoney"


def _cache_path(cache_dir: Path, provider: str, code: str) -> Path:
    safe_code = "".join(character for character in code if character.isalnum() or character in "._-")
    return cache_dir / provider / f"{safe_code}.json"


def _load_cached_history(path: Path, code: str, requested_days: int) -> Optional[StockHistory]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None
    if int(payload.get("requested_days", 0)) < requested_days:
        return None
    allowed = {item.name for item in fields(HistoryBar)}
    bars = [
        HistoryBar(**{key: value for key, value in item.items() if key in allowed})
        for item in payload.get("bars", [])
        if isinstance(item, dict)
    ]
    return StockHistory(code=code, bars=bars)


def _save_cached_history(
    path: Path,
    history: StockHistory,
    provider: str,
    requested_days: int,
) -> None:
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "provider": provider,
        "code": history.code,
        "requested_days": requested_days,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bars": [asdict(bar) for bar in history.bars],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_history(code: str, provider: str, days: int) -> StockHistory:
    if provider == "yahoo":
        return YahooFinanceDataSource().fetch_history(code, days=days)
    history = EastMoneyDataSource().fetch_history(code, days=days)
    if history.bars:
        return history
    return AShareHistoryDataSource().fetch_history(code, days=days)


def _load_histories(args, codes: Sequence[str]) -> tuple[Dict[str, StockHistory], List[str]]:
    histories: Dict[str, StockHistory] = {}
    failed: List[str] = []
    for code in codes:
        provider = _provider_name(code, args.provider)
        cache_path = _cache_path(args.cache_dir, provider, code)
        history = None if args.refresh else _load_cached_history(cache_path, code, args.days)
        if history is None:
            history = _fetch_history(code, provider, args.days)
            if history.bars:
                _save_cached_history(cache_path, history, provider, args.days)
        if history.bars:
            histories[code] = history
        else:
            failed.append(code)
    return histories, failed


def _write_observations(path: Path, observations) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "code",
        "signal_date",
        "entry_date",
        "action",
        "tone",
        "score",
        "score_max",
        "entry_price",
        "return_5d",
        "return_10d",
        "return_20d",
        "primary_return",
        "maximum_favorable_excursion",
        "maximum_adverse_excursion",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in observations:
            writer.writerow(
                {
                    "code": item.code,
                    "signal_date": item.signal_date,
                    "entry_date": item.entry_date,
                    "action": item.action,
                    "tone": item.tone,
                    "score": item.score,
                    "score_max": item.score_max,
                    "entry_price": item.entry_price,
                    "return_5d": item.returns.get("5"),
                    "return_10d": item.returns.get("10"),
                    "return_20d": item.returns.get("20"),
                    "primary_return": item.primary_return,
                    "maximum_favorable_excursion": item.maximum_favorable_excursion,
                    "maximum_adverse_excursion": item.maximum_adverse_excursion,
                }
            )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    codes = _codes_from_args(args)
    if not codes:
        parser.error("provide at least one code or --codes-file")
    if args.days < 100:
        parser.error("--days must be at least 100")
    if args.cost_bps < 0:
        parser.error("--cost-bps cannot be negative")

    histories, failed = _load_histories(args, codes)
    if not histories:
        print("No historical data available for backtest.", file=sys.stderr)
        return 1

    config = BacktestConfig(
        total_cost_bps=args.cost_bps,
        train_fraction=args.train_fraction,
        minimum_bucket_samples=max(1, args.minimum_bucket_samples),
    )
    result = run_swing_backtest(histories, config)
    if not result.observations:
        print("Historical data is insufficient to create backtest observations.", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_backtest_markdown(result), encoding="utf-8")
    calibration_path = save_calibration(args.calibration_out, result.calibration)
    _write_observations(args.trades_out, result.observations)

    print(f"Backtest report: {args.out.resolve()}")
    print(f"Calibration: {calibration_path}")
    print(f"Observation ledger: {args.trades_out.resolve()}")
    print(f"Observations: {len(result.observations)}")
    if failed:
        print(f"Skipped failed codes: {', '.join(failed)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

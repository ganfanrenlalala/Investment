#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate an A-share mainline radar report."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import DataSourceError  # noqa: E402
from core.mainline_radar import evaluate_sector_rows, render_mainline_radar_markdown  # noqa: E402
from providers import AkShareDataSource, EastMoneyDataSource  # noqa: E402


def default_output_path() -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    return ROOT / "outputs" / "mainline-radar" / f"{today}.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="扫描行业/概念板块，生成 StockSight 主线雷达报告。"
    )
    parser.add_argument(
        "--board",
        choices=["industry", "concept", "all"],
        default="all",
        help="扫描行业、概念或两者。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="输出前 N 个板块。",
    )
    parser.add_argument(
        "--market-change",
        type=float,
        default=0.0,
        help="大盘参考涨跌幅；暂不自动抓指数时可手动传入。",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "akshare", "eastmoney"],
        default="auto",
        help="板块数据源。auto 优先 AkShare/新浪，避免云端 IP 被东财拒绝。",
    )
    parser.add_argument(
        "--out",
        default=str(default_output_path()),
        help="Markdown 输出路径。",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="请求超时时间，单位秒。",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="同时在终端打印 Markdown。",
    )
    return parser.parse_args()


def _fetch_rows(provider, board: str) -> list:
    board_types = ["industry", "concept"] if board == "all" else [board]
    rows = []
    for board_type in board_types:
        rows.extend(provider.get_sector_list(board_type=board_type))
    return rows


def _try_provider(name: str, factory, board: str, errors: list) -> tuple[list, str]:
    try:
        rows = _fetch_rows(factory(), board)
        if rows:
            return rows, name
        errors.append(f"{name}: empty")
    except DataSourceError as exc:
        errors.append(f"{name}: {exc}")
    except Exception as exc:
        errors.append(f"{name}: {exc}")
    return [], name


def fetch_sector_rows(provider: str, board: str, timeout: int) -> tuple[list, str]:
    errors: list[str] = []
    if provider in ("auto", "akshare"):
        rows, used = _try_provider("akshare", AkShareDataSource, board, errors)
        if rows:
            return rows, used
        if provider == "akshare":
            raise DataSourceError("; ".join(errors) or "akshare returned no sector rows")

    rows, used = _try_provider(
        "eastmoney",
        lambda: EastMoneyDataSource(timeout=timeout),
        board,
        errors,
    )
    if rows:
        return rows, used
    raise DataSourceError("; ".join(errors) or "no sector rows")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    try:
        rows, source = fetch_sector_rows(args.provider, args.board, args.timeout)
    except DataSourceError as exc:
        print(f"未获取到板块数据：{exc}", file=sys.stderr)
        return 1

    results = evaluate_sector_rows(
        rows,
        market_change=args.market_change,
        limit=max(1, args.limit),
    )
    markdown = render_mainline_radar_markdown(
        results,
        market_change=args.market_change,
        data_source=source,
    )

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"主线雷达报告已保存：{output_path}（数据源: {source}）")
    if args.print:
        print()
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

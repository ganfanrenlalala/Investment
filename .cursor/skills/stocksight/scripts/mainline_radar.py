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

from core.mainline_radar import evaluate_sector_rows, render_mainline_radar_markdown  # noqa: E402
from providers import EastMoneyDataSource  # noqa: E402


def default_output_path() -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    return ROOT / "outputs" / "mainline-radar" / f"{today}.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="扫描东方财富行业/概念板块，生成 StockSight 主线雷达报告。"
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


def _fetch_rows(provider: EastMoneyDataSource, board: str) -> list:
    board_types = ["industry", "concept"] if board == "all" else [board]
    rows = []
    for board_type in board_types:
        rows.extend(provider.get_sector_list(board_type=board_type))
    return rows


def main() -> int:
    args = parse_args()
    provider = EastMoneyDataSource(timeout=args.timeout)
    rows = _fetch_rows(provider, args.board)
    if not rows:
        print("未获取到板块数据；可能是网络或东方财富接口临时限制。", file=sys.stderr)
        return 1

    results = evaluate_sector_rows(
        rows,
        market_change=args.market_change,
        limit=max(1, args.limit),
    )
    markdown = render_mainline_radar_markdown(
        results,
        market_change=args.market_change,
    )

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"主线雷达报告已保存：{output_path}")
    if args.print:
        print()
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render fixed example snapshots for formatter visual comparison."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from formatter import render_detailed_report, render_html_report, render_standard_report  # noqa: E402
from scripts.report import _load_snapshot  # noqa: E402

DEFAULT_EXAMPLES = [
    "a-share-detailed.json",
    "us-detailed.json",
    "no-technical.json",
    "high-risk.json",
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render fixed StockSight example snapshots to HTML/Markdown.",
    )
    parser.add_argument(
        "--examples-dir",
        type=Path,
        default=ROOT / "examples",
        help="Directory containing example snapshot JSON files.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "reports" / "examples",
        help="Directory for rendered HTML files.",
    )
    parser.add_argument(
        "--markdown-dir",
        type=Path,
        default=ROOT / "outputs" / "examples",
        help="Directory for rendered Markdown files.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Render every JSON file in examples-dir instead of the fixed visual set.",
    )
    return parser


def render_examples(
    examples_dir: Path = ROOT / "examples",
    out_dir: Path = ROOT / "reports" / "examples",
    markdown_dir: Path = ROOT / "outputs" / "examples",
    render_all: bool = False,
) -> list[Path]:
    examples_dir = examples_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir.mkdir(parents=True, exist_ok=True)

    snapshot_paths = (
        sorted(examples_dir.glob("*.json"))
        if render_all
        else [examples_dir / name for name in DEFAULT_EXAMPLES]
    )

    rendered: list[Path] = []
    for snapshot_path in snapshot_paths:
        data, meta = _load_snapshot(snapshot_path)
        mode = str(meta.get("mode") or "detailed")
        if mode == "standard":
            markdown = render_standard_report(data)
        else:
            markdown = render_detailed_report(data)
        html = render_html_report(data, mode=mode)

        stem = snapshot_path.stem
        html_path = out_dir / f"{stem}.html"
        markdown_path = markdown_dir / f"{stem}.md"
        html_path.write_text(html, encoding="utf-8")
        markdown_path.write_text(markdown, encoding="utf-8")
        rendered.append(html_path)

    return rendered


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    rendered = render_examples(
        examples_dir=args.examples_dir,
        out_dir=args.out_dir,
        markdown_dir=args.markdown_dir,
        render_all=args.all,
    )
    for path in rendered:
        print(f"Rendered: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

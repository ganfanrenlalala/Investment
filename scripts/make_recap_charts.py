#!/usr/bin/env python3
"""Render daily recap charts from a JSON file. Do not invent values.

Usage (from repo root):

    python3 scripts/make_recap_charts.py reports/YYYY-MM-DD/charts/data.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

UP = "#c0392b"
DOWN = "#1e8449"
NEUTRAL = "#333333"
MUTED = "#7f8c8d"


def pick_font() -> str:
    candidates = [
        "Microsoft YaHei",
        "Microsoft YaHei UI",
        "SimHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
        "Source Han Sans SC",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    return "sans-serif"


plt.rcParams["font.sans-serif"] = [pick_font(), "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def color(value: float) -> str:
    if value > 0:
        return UP
    if value < 0:
        return DOWN
    return MUTED


def label_bars(ax, bars, vals, fmt: str, dx: float) -> None:
    for bar, val in zip(bars, vals):
        y = bar.get_y() + bar.get_height() / 2
        width = bar.get_width()
        ax.text(
            width + (dx if width >= 0 else -dx),
            y,
            fmt.format(val),
            va="center",
            ha="left" if width >= 0 else "right",
            fontsize=9,
            color=NEUTRAL,
        )


def padded_lim(values: list[float], pad_ratio: float = 0.18) -> tuple[float, float]:
    lo, hi = min(values), max(values)
    if lo == hi:
        lo -= 1
        hi += 1
    span = max(abs(lo), abs(hi), hi - lo, 1.0)
    pad = span * pad_ratio
    left = min(lo, 0) - pad
    right = max(hi, 0) + pad
    return left, right


def save(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def draw_indices(out: Path, date: str, items: list[dict]) -> None:
    names = [row["name"] for row in items]
    vals = [float(row["value"]) for row in items]
    # weakest at bottom so the worst name is closest to the axis label
    names, vals = names[::-1], vals[::-1]
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    bars = ax.barh(names, vals, color=[color(v) for v in vals], height=0.62)
    ax.axvline(0, color=NEUTRAL, lw=0.8)
    ax.set_xlabel("涨跌幅（%）")
    weakest = min(items, key=lambda row: float(row["value"]))
    ax.set_title(f"{date} 主要指数（最弱：{weakest['name']} {float(weakest['value']):+.2f}%）")
    ax.set_xlim(*padded_lim(vals))
    ax.grid(axis="x", linestyle=":", color="#ddd")
    label_bars(ax, bars, vals, "{:+.2f}%", 0.06)
    save(fig, out / "01_indices.png")


def draw_limits(out: Path, date: str, limits: dict) -> None:
    up = int(limits.get("up") or 0)
    down = int(limits.get("down") or 0)
    if up <= 0 and down <= 0:
        return
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    cats, vals, colors = [], [], []
    if up > 0:
        cats.append("涨停")
        vals.append(up)
        colors.append(UP)
    if down > 0:
        cats.append("跌停")
        vals.append(down)
        colors.append(DOWN)
    bars = ax.bar(cats, vals, color=colors, width=0.45)
    ax.set_ylabel("家数")
    if up > 0 and down > 0:
        ax.set_title(f"{date} 涨停 {up}  vs  跌停 {down}")
        ax.text(
            0.5,
            -0.18,
            f"涨停约为跌停的 {up / down:.1f} 倍",
            transform=ax.transAxes,
            ha="center",
            color="#555",
        )
    elif up > 0:
        ax.set_title(f"{date} 涨停 {up} 家（跌停 0，不画 0 扇区）")
    else:
        ax.set_title(f"{date} 跌停 {down} 家（涨停 0）")
    for bar, val, col in zip(bars, vals, colors):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + max(vals) * 0.03,
            str(val),
            ha="center",
            fontsize=13,
            fontweight="bold",
            color=col,
        )
    ax.set_ylim(0, max(vals) * 1.25)
    save(fig, out / "02_limit.png")


def draw_watch(out: Path, date: str, groups: list[dict]) -> None:
    groups = [g for g in groups if g.get("items")]
    if not groups:
        return
    n = len(groups)
    rows = 2 if n > 2 else 1
    cols = 2 if n > 1 else 1
    fig, axes = plt.subplots(rows, cols, figsize=(10.5, 3.2 * rows), squeeze=False)
    all_vals = [float(item["value"]) for g in groups for item in g["items"]]
    xlim = padded_lim(all_vals, 0.22)
    for idx, ax in enumerate(axes.ravel()):
        if idx >= n:
            ax.axis("off")
            continue
        group = groups[idx]
        labels = [item["name"] for item in group["items"]][::-1]
        vals = [float(item["value"]) for item in group["items"]][::-1]
        bars = ax.barh(labels, vals, color=[color(v) for v in vals], height=0.55)
        ax.axvline(0, color=NEUTRAL, lw=0.8)
        ax.set_title(group.get("title") or f"观察组 {idx + 1}", fontsize=11)
        ax.set_xlim(*xlim)
        ax.grid(axis="x", linestyle=":", color="#ddd")
        label_bars(ax, bars, vals, "{:+.2f}%", 0.08)
    fig.suptitle(f"{date} 四个观察对象（涨红跌绿）", fontsize=13, y=1.02)
    save(fig, out / "03_watch.png")


def draw_flow(out: Path, date: str, items: list[dict]) -> None:
    names = [row["name"] for row in items]
    vals = [float(row["value"]) for row in items]
    names, vals = names[::-1], vals[::-1]
    fig, ax = plt.subplots(figsize=(9.2, max(4.2, 0.42 * len(names) + 1.6)))
    bars = ax.barh(names, vals, color=[color(v) for v in vals], height=0.62)
    ax.axvline(0, color=NEUTRAL, lw=0.9)
    ax.set_xlabel("净流入（亿元）")
    ax.set_title(f"{date} 行业资金（流入与流出同一坐标）")
    ax.set_xlim(*padded_lim(vals, 0.15))
    ax.grid(axis="x", linestyle=":", color="#ddd")
    label_bars(ax, bars, vals, "{:+.2f}", max(abs(v) for v in vals) * 0.02 or 0.2)
    save(fig, out / "04_flow.png")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render recap PNG charts from data.json")
    parser.add_argument("data_json", help="Path to reports/YYYY-MM-DD/charts/data.json")
    args = parser.parse_args()
    path = Path(args.data_json)
    if not path.is_file():
        print(f"missing {path}", file=sys.stderr)
        return 1

    payload = json.loads(path.read_text(encoding="utf-8"))
    out = path.parent
    out.mkdir(parents=True, exist_ok=True)
    date = str(payload.get("date") or out.parent.name)

    written = []
    if payload.get("indices"):
        draw_indices(out, date, payload["indices"])
        written.append("01_indices.png")
    if payload.get("limits"):
        draw_limits(out, date, payload["limits"])
        if (out / "02_limit.png").exists():
            written.append("02_limit.png")
    if payload.get("watch_groups"):
        draw_watch(out, date, payload["watch_groups"])
        written.append("03_watch.png")
    if payload.get("fund_flow"):
        draw_flow(out, date, payload["fund_flow"])
        written.append("04_flow.png")

    if not written:
        print("data.json has no drawable sections", file=sys.stderr)
        return 1
    print("wrote", ", ".join(str(out / name) for name in written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

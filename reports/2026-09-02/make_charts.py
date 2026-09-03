#!/usr/bin/env python3
"""Generate 2026-09-02 recap charts. Values come from 复盘.md — do not invent."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

UP = "#c0392b"
DOWN = "#1e8449"
NEUTRAL = "#333333"


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

OUT = Path(__file__).resolve().parent / "charts"
OUT.mkdir(parents=True, exist_ok=True)


def color(v: float) -> str:
    if v > 0:
        return UP
    if v < 0:
        return DOWN
    return "#7f8c8d"


def label_bars(ax, bars, vals, fmt="{:+.2f}", dx_zero=0.08):
    for bar, val in zip(bars, vals):
        y = bar.get_y() + bar.get_height() / 2
        x = bar.get_width()
        ax.text(
            x + (dx_zero if x >= 0 else -dx_zero),
            y,
            fmt.format(val),
            va="center",
            ha="left" if x >= 0 else "right",
            fontsize=9,
            color=NEUTRAL,
        )


# 1) 指数：横条，弱到强，一眼看到创业板最差
fig, ax = plt.subplots(figsize=(8.2, 4.2))
names = ["创业板", "深成指", "科创50", "沪深300", "上证"]
vals = [-2.39, -1.88, -1.82, -1.38, -0.97]
bars = ax.barh(names, vals, color=[color(v) for v in vals], height=0.62)
ax.axvline(0, color=NEUTRAL, lw=0.8)
ax.set_xlabel("涨跌幅（%）")
ax.set_title("2026-09-02 主要指数：全线收跌，创业板最弱")
ax.set_xlim(-3.1, 0.4)
ax.grid(axis="x", linestyle=":", color="#ddd")
label_bars(ax, bars, vals, fmt="{:+.2f}%", dx_zero=0.06)
fig.tight_layout()
fig.savefig(OUT / "01_indices.png", dpi=150)
plt.close()

# 2) 涨跌停：并排柱 + 文字比例
fig, ax = plt.subplots(figsize=(6.4, 3.8))
cats = ["涨停", "跌停"]
vals = [52, 8]
bars = ax.bar(cats, vals, color=[UP, DOWN], width=0.45)
ax.set_ylabel("家数")
ax.set_title("涨停 52  vs  跌停 8（情绪偏弱，但未冰点）")
for bar, val in zip(bars, vals):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        val + 1.2,
        str(val),
        ha="center",
        fontsize=13,
        fontweight="bold",
        color=UP if val == 52 else DOWN,
    )
ax.set_ylim(0, 64)
ax.text(0.5, -0.18, "涨停约为跌停的 6.5 倍", transform=ax.transAxes, ha="center", color="#555")
fig.tight_layout()
fig.savefig(OUT / "02_limit.png", dpi=150)
plt.close()

# 3) 四观察对象：按主题分组的横条
fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.4), sharex=False)
groups = [
    ("黄金：现货/ETF 跌，个股分化", ["Au99.99", "黄金ETF", "山东黄金"], [-2.13, -2.37, 2.71]),
    ("半导体：内外共振偏弱", ["半导体板块", "中芯国际"], [-1.34, -2.82]),
    ("外盘（09-01 收盘）", ["纳指", "NVDA"], [-1.03, -1.51]),
    ("医药：板块弱、龙头抗跌", ["化学制药", "药明康德"], [-1.10, 1.03]),
]
for ax, (title, labels, data) in zip(axes.ravel(), groups):
    bars = ax.barh(labels[::-1], data[::-1], color=[color(v) for v in data[::-1]], height=0.55)
    ax.axvline(0, color=NEUTRAL, lw=0.8)
    ax.set_title(title, fontsize=11)
    ax.set_xlim(-3.6, 3.6)
    ax.grid(axis="x", linestyle=":", color="#ddd")
    label_bars(ax, bars, data[::-1], fmt="{:+.2f}%", dx_zero=0.08)
fig.suptitle("四个观察对象（涨红跌绿）", fontsize=13, y=1.01)
fig.tight_layout()
fig.savefig(OUT / "03_watch.png", dpi=150, bbox_inches="tight")
plt.close()

# 4) 资金：同一把尺子，流入 vs 流出一眼能比
fig, ax = plt.subplots(figsize=(9.2, 5.2))
flow_names = [
    "军工装备",
    "军工电子",
    "医疗服务",
    "互联网电商",
    "建筑材料",
    "化学制药",
    "半导体",
    "通信设备",
    "证券",
]
flow_vals = [7.48, 3.56, 3.43, 1.36, 1.12, -35.65, -48.95, -52.31, -54.25]
bars = ax.barh(flow_names[::-1], flow_vals[::-1], color=[color(v) for v in flow_vals[::-1]], height=0.62)
ax.axvline(0, color=NEUTRAL, lw=0.9)
ax.set_xlabel("净流入（亿元）")
ax.set_title("资金画像：军工小流入 vs 半导体/医药大流出（同一坐标）")
ax.set_xlim(-62, 14)
ax.grid(axis="x", linestyle=":", color="#ddd")
label_bars(ax, bars, flow_vals[::-1], fmt="{:+.2f}", dx_zero=0.8)
fig.tight_layout()
fig.savefig(OUT / "04_flow.png", dpi=150, bbox_inches="tight")
plt.close()

print("wrote", sorted(p.name for p in OUT.glob("*.png")))

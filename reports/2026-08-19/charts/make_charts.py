#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 2026-08-19 盘后复盘可视化图表。

数据来源：当日 akshare 收盘查询（sources/akshare-close.txt）、stocksight 个股报告、
firecrawl 检索（AP/Reuters，美股为 8/18 收盘）。全部为真实采集数据，无估算值。
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")
plt.rcParams["font.family"] = "WenQuanYi Micro Hei"
plt.rcParams["axes.unicode_minus"] = False

OUT = os.path.dirname(os.path.abspath(__file__))
UP, DOWN = "#c0392b", "#1e8449"  # A股惯例：红涨绿跌
GRID = dict(axis="x", color="#dddddd", linewidth=0.8)


def bar_colors(vals):
    return [UP if v >= 0 else DOWN for v in vals]


def hbar(ax, names, vals, title):
    colors = bar_colors(vals)
    bars = ax.barh(range(len(names)), vals, color=colors, height=0.62)
    ax.set_yticks(range(len(names)), names)
    ax.invert_yaxis()
    ax.grid(**GRID)
    ax.set_axisbelow(True)
    ax.axvline(0, color="#555555", linewidth=0.9)
    ax.set_title(title, fontsize=13, pad=10)
    for b, v in zip(bars, vals):
        off = 0.08 if v >= 0 else -0.08
        ax.text(v + off, b.get_y() + b.get_height() / 2, f"{v:+.2f}%",
                va="center", ha="left" if v >= 0 else "right", fontsize=9.5)
    lo, hi = min(vals), max(vals)
    ax.set_xlim(lo - (hi - lo) * 0.18 - 0.6, hi + (hi - lo) * 0.18 + 0.6)


# ── 图1：核心指数涨跌幅 ────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5.4))
names = ["上证50", "上证指数", "沪深300", "深证成指", "创业板指",
         "道琼斯*", "标普500*", "纳斯达克*", "费城半导体*"]
vals = [-1.88, -2.51, -3.02, -5.00, -6.23, -0.22, -0.69, -1.33, -5.0]
hbar(ax, names, vals, "核心指数涨跌幅 · A股 2026-08-19 收盘 / 美股(*) 8-18 收盘")
ax.text(0.99, -0.11, "数据：akshare 收盘、AP、Reuters（SOX）",
        transform=ax.transAxes, ha="right", fontsize=8.5, color="#888888")
fig.tight_layout()
fig.savefig(f"{OUT}/01_indexes.png", dpi=150)
plt.close(fig)

# ── 图2：行业与概念板块涨跌 ──────────────────────────────────────
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 5.6))
ind_names = ["金融行业", "公路桥梁", "酿酒行业", "煤炭行业", "交通运输",
             "生物制药", "电子信息", "机械行业", "玻璃行业", "电子器件", "次新股"]
ind_vals = [-0.08, -0.44, -0.62, -0.99, -1.21, -1.97, -6.03, -6.45, -6.60, -7.15, -8.36]
hbar(a1, ind_names, ind_vals, "行业板块（跌幅最小→最大，医药抗跌、电子领跌）")
con_names = ["超大盘", "生物燃料", "黄金概念", "华为概念", "宽带提速",
             "BC电池", "TOPCon", "HIT电池"]
con_vals = [1.11, 0.02, -0.31, -8.69, -8.72, -9.00, -9.07, -9.65]
hbar(a2, con_names, con_vals, "概念板块（涨幅前3 与 跌幅前5）")
fig.suptitle("板块涨跌全景 · 2026-08-19 收盘（akshare）", fontsize=14)
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig(f"{OUT}/02_sectors.png", dpi=150)
plt.close(fig)

# ── 图3：四条主线龙头异动 ────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8.6, 4.6))
names = ["山东黄金\n(600547·黄金)", "恒瑞医药\n(600276·医药)",
         "中芯国际\n(688981·半导体)", "寒武纪\n(688256·半导体)"]
vals = [6.5, 0.6, -5.2, -9.6]
bars = ax.bar(range(len(names)), vals, color=bar_colors(vals), width=0.55)
ax.set_xticks(range(len(names)), names, fontsize=10.5)
ax.axhline(0, color="#555555", linewidth=0.9)
ax.grid(axis="y", color="#dddddd", linewidth=0.8)
ax.set_axisbelow(True)
ax.set_ylabel("涨跌幅 (%)")
ax.set_title("四条主线龙头当日表现 · 2026-08-19 收盘（stocksight·腾讯源）", fontsize=13, pad=10)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + (0.35 if v >= 0 else -0.35),
            f"{v:+.1f}%", ha="center", va="bottom" if v >= 0 else "top",
            fontsize=11, fontweight="bold")
ax.set_ylim(-11.5, 8.5)
fig.tight_layout()
fig.savefig(f"{OUT}/03_leaders.png", dpi=150)
plt.close(fig)

# ── 图4：市场情绪（涨跌停 + 近5日主力资金） ──────────────────────
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.6), width_ratios=[1, 1.5])
bars = a1.bar(["涨停", "跌停"], [36, 122], color=[UP, DOWN], width=0.5)
for b, v in zip(bars, [36, 122]):
    a1.text(b.get_x() + b.get_width() / 2, v + 2, f"{v} 家", ha="center", fontsize=12,
            fontweight="bold")
a1.set_ylim(0, 140)
a1.grid(axis="y", color="#dddddd", linewidth=0.8)
a1.set_axisbelow(True)
a1.set_title("涨停 vs 跌停 · 8-19", fontsize=12.5)

days = ["08-12", "08-13", "08-14", "08-17", "08-18*"]
flows = [247.17, -449.64, -129.88, 494.70, -669.33]
bars = a2.bar(days, flows, color=bar_colors(flows), width=0.55)
for b, v in zip(bars, flows):
    a2.text(b.get_x() + b.get_width() / 2, v + (18 if v >= 0 else -18),
            f"{v:+.0f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=10)
a2.axhline(0, color="#555555", linewidth=0.9)
a2.grid(axis="y", color="#dddddd", linewidth=0.8)
a2.set_axisbelow(True)
a2.set_ylabel("主力净流入（亿元）")
a2.set_title("近5日全市场主力资金净流入（* 接口仅更新至 T-1，8-19 当日不可用）", fontsize=11.5)
a2.set_ylim(-820, 640)
fig.suptitle("市场情绪面 · 数据：akshare", fontsize=14)
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(f"{OUT}/04_sentiment.png", dpi=150)
plt.close(fig)

print("charts done")

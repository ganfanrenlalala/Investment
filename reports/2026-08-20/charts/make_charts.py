#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-08-20 盘后复盘图表。数据硬编码自当日 akshare / stocksight / SGE 真实采集值。"""
import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager, pyplot as plt

font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")
plt.rcParams["font.family"] = "WenQuanYi Micro Hei"
plt.rcParams["axes.unicode_minus"] = False

RED, GREEN = "#c9302c", "#1a8f3c"  # A股惯例：红涨绿跌


def colors(vals):
    return [RED if v >= 0 else GREEN for v in vals]


def bar_label(ax, bars, vals, fmt="{:+.2f}%"):
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2,
                v + (0.06 if v >= 0 else -0.06),
                fmt.format(v), ha="center",
                va="bottom" if v >= 0 else "top", fontsize=9)


# 01 核心指数涨跌（纳指为美东 8/19 收盘*）
names = ["上证指数", "深证成指", "创业板指", "沪深300", "上证50", "纳指*"]
vals = [0.24, 0.59, 0.64, 0.09, -0.49, 0.16]
fig, ax = plt.subplots(figsize=(8, 4.5))
bars = ax.bar(names, vals, color=colors(vals))
bar_label(ax, bars, vals)
ax.axhline(0, color="#888", lw=0.8)
ax.set_ylabel("涨跌幅 %")
ax.set_title("2026-08-20 核心指数涨跌幅（纳指*为美东 8/19 收盘）")
fig.tight_layout()
fig.savefig("01_核心指数涨跌.png", dpi=150)

# 02 行业/概念板块双栏
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.8))
ind_n = ["生物制药", "物资外贸", "医疗器械", "酒店旅游", "纺织机械",
         "次新股", "煤炭行业", "酿酒行业", "陶瓷行业", "飞机制造"]
ind_v = [3.13, 2.74, 2.73, 2.48, 1.62, -0.18, -0.57, -0.65, -1.33, -1.77]
b = a1.barh(ind_n[::-1], ind_v[::-1], color=colors(ind_v[::-1]))
a1.axvline(0, color="#888", lw=0.8)
a1.set_title("行业板块涨跌前5")
for r, v in zip(b, ind_v[::-1]):
    a1.text(v + (0.05 if v >= 0 else -0.05), r.get_y() + r.get_height() / 2,
            f"{v:+.2f}%", va="center", ha="left" if v >= 0 else "right", fontsize=8)
con_n = ["CXO概念", "CRO概念", "创新药", "免疫治疗", "基因测序",
         "奢侈品", "央企50", "草甘膦", "卫星导航", "电解液"]
con_v = [6.68, 5.74, 5.47, 5.03, 4.66, -0.91, -1.14, -1.19, -1.71, -2.05]
b = a2.barh(con_n[::-1], con_v[::-1], color=colors(con_v[::-1]))
a2.axvline(0, color="#888", lw=0.8)
a2.set_title("概念板块涨跌前5")
for r, v in zip(b, con_v[::-1]):
    a2.text(v + (0.08 if v >= 0 else -0.08), r.get_y() + r.get_height() / 2,
            f"{v:+.2f}%", va="center", ha="left" if v >= 0 else "right", fontsize=8)
fig.suptitle("2026-08-20 板块涨跌（akshare）")
fig.tight_layout()
fig.savefig("02_板块涨跌.png", dpi=150)

# 03 关键标的（stocksight 腾讯源收盘）
s_n = ["山东黄金", "药明康德", "中芯国际", "寒武纪", "恒瑞医药"]
s_v = [8.6, 2.4, -2.0, -3.8, -6.0]
fig, ax = plt.subplots(figsize=(8, 4.5))
bars = ax.bar(s_n, s_v, color=colors(s_v))
bar_label(ax, bars, s_v, fmt="{:+.1f}%")
ax.axhline(0, color="#888", lw=0.8)
ax.set_ylabel("涨跌幅 %")
ax.set_title("2026-08-20 关键标的涨跌（stocksight·腾讯源）")
fig.tight_layout()
fig.savefig("03_关键标的涨跌.png", dpi=150)

# 04 涨跌停对比 + 四观察对象相关涨跌
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.8))
a1.bar(["涨停", "跌停"], [80, 12], color=[RED, GREEN])
for x, v in zip([0, 1], [80, 12]):
    a1.text(x, v + 1.5, str(v), ha="center", fontsize=12)
a1.set_title("涨停 vs 跌停家数")
o_n = ["CXO概念", "创新药", "生物制药", "医疗器械", "Au99.99\n(上金所)", "电子信息", "电子器件", "纳指*"]
o_v = [6.68, 5.47, 3.13, 2.73, 2.46, 0.79, 0.05, 0.16]
bars = a2.bar(o_n, o_v, color=colors(o_v))
for b_, v in zip(bars, o_v):
    a2.text(b_.get_x() + b_.get_width() / 2, v + 0.08, f"+{v:.2f}%", ha="center", fontsize=8)
a2.axhline(0, color="#888", lw=0.8)
a2.set_title("四观察对象相关涨跌（纳指*为 8/19 收盘）")
a2.tick_params(axis="x", labelsize=8)
fig.suptitle("2026-08-20 涨跌停与观察对象")
fig.tight_layout()
fig.savefig("04_涨跌停与观察对象.png", dpi=150)
print("charts done")

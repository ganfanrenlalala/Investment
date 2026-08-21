#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-08-21 盘后复盘图表。数据硬编码自当日 akshare / stocksight 真实采集值。"""
import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt

font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")
plt.rcParams["font.family"] = "WenQuanYi Micro Hei"
plt.rcParams["axes.unicode_minus"] = False

UP, DOWN = "#d62728", "#2ca02c"  # 红涨绿跌


def colors(vals):
    return [UP if v >= 0 else DOWN for v in vals]


def bar_label(ax, bars, vals):
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (0.08 if v >= 0 else -0.22),
                f"{v:+.2f}%", ha="center", fontsize=9)


# 01 核心指数（纳指为美股上一交易日 8/20 收盘）
names = ["上证指数", "深证成指", "创业板指", "沪深300", "上证50", "纳指*8/20"]
vals = [0.04, 0.87, 1.43, 0.57, 0.07, -1.00]
fig, ax = plt.subplots(figsize=(8, 4.2))
bar_label(ax, ax.bar(names, vals, color=colors(vals)), vals)
ax.set_title("核心指数涨跌幅 · 2026-08-21（*纳指为 8/20 美股收盘）")
ax.set_ylabel("%"); ax.axhline(0, color="#999", lw=0.8)
fig.tight_layout(); fig.savefig("01_核心指数.png", dpi=140); plt.close(fig)

# 02 行业 / 概念板块双栏
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6))
ind_n = ["陶瓷", "有色金属", "电子器件", "食品", "医疗器械", "农林牧渔", "生物制药"]
ind_v = [3.22, 2.36, 1.90, -1.53, -2.12, -2.37, -3.95]
b1 = a1.barh(ind_n[::-1], ind_v[::-1], color=colors(ind_v[::-1]))
a1.set_title("新浪行业板块涨跌幅 (%)"); a1.axvline(0, color="#999", lw=0.8)
a1.set_xlim(-5.4, 4.4)
for b, v in zip(b1, ind_v[::-1]):
    a1.text(v + (0.1 if v >= 0 else -0.1), b.get_y() + b.get_height() / 2,
            f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=9)
con_n = ["黄金概念", "宽带提速", "锂矿", "仿制药", "超级细菌", "CRO概念", "CXO概念"]
con_v = [3.52, 3.09, 3.05, -4.58, -4.78, -5.11, -5.50]
b2 = a2.barh(con_n[::-1], con_v[::-1], color=colors(con_v[::-1]))
a2.set_title("概念板块涨跌幅 (%)"); a2.axvline(0, color="#999", lw=0.8)
a2.set_xlim(-7.2, 4.8)
for b, v in zip(b2, con_v[::-1]):
    a2.text(v + (0.12 if v >= 0 else -0.12), b.get_y() + b.get_height() / 2,
            f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=9)
fig.suptitle("行业 / 概念板块 · 2026-08-21")
fig.tight_layout(); fig.savefig("02_板块涨跌.png", dpi=140); plt.close(fig)

# 03 关键标的
kn = ["山东黄金", "寒武纪", "中芯国际", "药明康德", "恒瑞医药"]
kv = [5.0, 2.4, -0.6, -3.0, -3.6]
fig, ax = plt.subplots(figsize=(8, 4.2))
bar_label(ax, ax.bar(kn, kv, color=colors(kv)), kv)
ax.set_title("关键标的涨跌幅 · 2026-08-21")
ax.set_ylabel("%"); ax.axhline(0, color="#999", lw=0.8)
fig.tight_layout(); fig.savefig("03_关键标的.png", dpi=140); plt.close(fig)

# 04 涨跌停 + 四观察对象
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6))
a1.pie([54, 13], labels=["涨停 54 家", "跌停 13 家"], colors=[UP, DOWN],
       autopct="%1.0f%%", startangle=90)
a1.set_title("涨停 vs 跌停")
on = ["黄金\nSGE Au99.99", "半导体\n电子器件", "纳指*\n8/20收盘", "医药\n生物制药"]
ov = [1.67, 1.90, -1.00, -3.95]
bar_label(a2, a2.bar(on, ov, color=colors(ov)), ov)
a2.set_title("四观察对象涨跌 (%)"); a2.axhline(0, color="#999", lw=0.8)
fig.suptitle("涨跌停与观察对象 · 2026-08-21")
fig.tight_layout(); fig.savefig("04_涨跌停与观察对象.png", dpi=140); plt.close(fig)

print("4 charts done")

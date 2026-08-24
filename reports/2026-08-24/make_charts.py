#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-08-24 盘后复盘图表。数据硬编码自当日 akshare / stocksight / firecrawl 真实采集值。"""
import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager, pyplot as plt

font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")
plt.rcParams["font.family"] = "WenQuanYi Micro Hei"
plt.rcParams["axes.unicode_minus"] = False

RED, GREEN = "#d64541", "#1e824c"  # 红涨绿跌
OUT = "charts"


def bar_colors(vals):
    return [RED if v >= 0 else GREEN for v in vals]


def annotate(ax, bars, vals, fmt="{:+.2f}%"):
    for b, v in zip(bars, vals):
        ax.annotate(fmt.format(v), xy=(b.get_x() + b.get_width() / 2, v),
                    xytext=(0, 6 if v >= 0 else -14), textcoords="offset points",
                    ha="center", fontsize=10, fontweight="bold",
                    color=RED if v >= 0 else GREEN)


# 01 核心指数
names = ["上证指数", "深证成指", "创业板指", "沪深300", "上证50", "纳斯达克*"]
vals = [-0.59, -2.13, -3.21, -1.21, -0.44, 0.43]
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(names, vals, color=bar_colors(vals), width=0.6)
annotate(ax, bars, vals)
ax.axhline(0, color="#888", lw=0.8)
ax.set_ylim(-4.2, 1.4)
ax.set_ylabel("涨跌幅 %")
ax.set_title("核心指数涨跌幅 · 2026-08-24（*纳指为 8/21 美股收盘）", fontsize=13)
fig.tight_layout()
fig.savefig(f"{OUT}/01_核心指数.png", dpi=150)
plt.close(fig)

# 02 行业 / 概念板块双栏
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))
ind_n = ["煤炭行业", "公路桥梁", "开发区", "酿酒行业", "金融行业",
         "电子器件", "生物制药", "机械行业", "医疗器械", "玻璃行业"]
ind_v = [2.07, 2.00, 1.87, 1.65, 1.08, -2.68, -2.89, -3.15, -3.40, -3.41]
y = range(len(ind_n))[::-1]
ax1.barh(list(y), ind_v, color=bar_colors(ind_v))
ax1.set_yticks(list(y), ind_n)
ax1.set_xlim(-5.6, 3.6)
ax1.axvline(0, color="#888", lw=0.8)
for yi, v in zip(y, ind_v):
    ax1.text(v + (0.12 if v >= 0 else -0.12), yi, f"{v:+.2f}%", va="center",
             ha="left" if v >= 0 else "right", fontsize=9,
             color=RED if v >= 0 else GREEN)
ax1.set_title("行业板块涨跌幅前/后五（新浪口径）")

con_n = ["生物育种", "未股改", "奢侈品", "白酒概念", "超大盘",
         "创新药", "黄河三角", "超级细菌", "CRO概念", "CXO概念"]
con_v = [2.41, 2.13, 2.03, 1.59, 1.10, -4.08, -4.59, -4.68, -5.32, -5.48]
y = range(len(con_n))[::-1]
ax2.barh(list(y), con_v, color=bar_colors(con_v))
ax2.set_yticks(list(y), con_n)
ax2.set_xlim(-8.2, 4.2)
ax2.axvline(0, color="#888", lw=0.8)
for yi, v in zip(y, con_v):
    ax2.text(v + (0.15 if v >= 0 else -0.15), yi, f"{v:+.2f}%", va="center",
             ha="left" if v >= 0 else "right", fontsize=9,
             color=RED if v >= 0 else GREEN)
ax2.set_title("概念板块涨跌幅前/后五")
fig.suptitle("板块涨跌 · 2026-08-24", fontsize=13)
fig.tight_layout()
fig.savefig(f"{OUT}/02_板块涨跌.png", dpi=150)
plt.close(fig)

# 03 四观察对象及关键标的
names = ["Au99.99\n(上金所)", "国际金价*\n(COMEX现货)", "山东黄金", "中芯国际",
         "寒武纪", "纳斯达克*", "英伟达*", "恒瑞医药", "药明康德"]
vals = [2.07, 0.81, -1.50, -3.40, -6.40, 0.43, -0.98, -2.00, -4.30]
fig, ax = plt.subplots(figsize=(11, 5.2))
bars = ax.bar(names, vals, color=bar_colors(vals), width=0.62)
annotate(ax, bars, vals)
ax.axhline(0, color="#888", lw=0.8)
ax.set_ylim(-8.2, 3.4)
ax.set_ylabel("涨跌幅 %")
ax.set_title("四观察对象及关键标的 · 2026-08-24（*为最近可用境外数据，纳指/英伟达为 8/21 收盘）", fontsize=12)
fig.tight_layout()
fig.savefig(f"{OUT}/03_观察对象.png", dpi=150)
plt.close(fig)

# 04 涨跌停对比 + 情绪
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))
ax1.pie([46, 11], labels=["涨停 46 家", "跌停 11 家"], colors=[RED, GREEN],
        autopct="%1.0f%%", startangle=90, textprops={"fontsize": 12})
ax1.set_title("涨停 vs 跌停家数")
sect = ["贵金属", "白银", "黄金", "煤炭", "种子", "CXO概念", "创新药"]
sv = [4.41, 7.44, 3.40, 2.80, 4.04, -5.48, -4.08]
bars = ax2.bar(sect, sv, color=bar_colors(sv), width=0.6)
annotate(ax2, bars, sv)
ax2.axhline(0, color="#888", lw=0.8)
ax2.set_ylim(-8.2, 9.6)
ax2.set_title("当日强弱板块对照（东财/新浪口径）")
fig.suptitle("市场情绪 · 2026-08-24", fontsize=13)
fig.tight_layout()
fig.savefig(f"{OUT}/04_情绪与强弱板块.png", dpi=150)
plt.close(fig)

print("charts done")

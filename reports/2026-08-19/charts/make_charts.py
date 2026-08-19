#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-08-19 盘后复盘图表。数据硬编码自当日 akshare / stocksight / firecrawl 真实采集值。"""
import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager, pyplot as plt

font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")
plt.rcParams["font.family"] = "WenQuanYi Micro Hei"
plt.rcParams["axes.unicode_minus"] = False

RED, GREEN = "#c0392b", "#1e8449"


def colors(vals):
    return [RED if v >= 0 else GREEN for v in vals]


def barh(ax, names, vals, title):
    ax.barh(range(len(names)), vals, color=colors(vals))
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.axvline(0, color="#555", lw=0.8)
    ax.set_title(title)
    for i, v in enumerate(vals):
        ax.text(v, i, f" {v:+.2f}%" if abs(v) < 50 else f" {v:.0f}",
                va="center", ha="left" if v >= 0 else "right", fontsize=9)


# 01 核心指数涨跌（A股收盘 + 美股上一交易日*）
idx = [("上证指数", -2.40), ("深证成指", -5.01), ("创业板指", -6.26),
       ("沪深300", -2.90), ("上证50", -1.53),
       ("纳斯达克*", -1.33), ("标普500*", -0.69), ("道琼斯*", -0.22)]
fig, ax = plt.subplots(figsize=(9, 5))
barh(ax, [n for n, _ in idx], [v for _, v in idx], "核心指数涨跌幅（2026-08-19 A股收盘；* 为美股 08-18 收盘）")
fig.tight_layout(); fig.savefig("01_核心指数涨跌.png", dpi=150); plt.close(fig)

# 02 行业 / 概念板块双栏（新浪源）
ind = [("金融行业", 0.05), ("酿酒行业", -0.31), ("公路桥梁", -0.39), ("煤炭行业", -0.92),
       ("电子信息", -6.05), ("机械行业", -6.45), ("玻璃行业", -6.60), ("电子器件", -7.15), ("次新股", -8.39)]
con = [("超大盘", 1.31), ("奢侈品", 0.21), ("生物燃料", 0.04), ("黄金概念", -0.24),
       ("华为概念", -8.69), ("宽带提速", -8.74), ("BC电池", -9.06), ("TOPCon", -9.08), ("HIT电池", -9.69)]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.5))
barh(a1, [n for n, _ in ind], [v for _, v in ind], "行业板块涨跌幅前后五")
barh(a2, [n for n, _ in con], [v for _, v in con], "概念板块涨跌幅前后五")
fig.suptitle("2026-08-19 板块涨跌（akshare · 新浪源）")
fig.tight_layout(); fig.savefig("02_行业概念板块.png", dpi=150); plt.close(fig)

# 03 四大观察龙头（stocksight · 腾讯源）
stk = [("山东黄金\n600547", 6.5), ("恒瑞医药\n600276", 0.6), ("中芯国际\n688981", -5.2), ("寒武纪\n688256", -9.6)]
fig, ax = plt.subplots(figsize=(8, 5))
vals = [v for _, v in stk]
ax.bar(range(4), vals, color=colors(vals), width=0.55)
ax.set_xticks(range(4)); ax.set_xticklabels([n for n, _ in stk])
ax.axhline(0, color="#555", lw=0.8)
ax.set_ylabel("涨跌幅 %")
ax.set_title("四大观察龙头收盘涨跌（2026-08-19，StockSight）")
for i, v in enumerate(vals):
    ax.text(i, v, f"{v:+.1f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=11)
fig.tight_layout(); fig.savefig("03_四龙头涨跌.png", dpi=150); plt.close(fig)

# 04 涨跌停对比 + 观察对象相关板块
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
a1.bar(["涨停", "跌停"], [36, 117], color=[RED, GREEN], width=0.5)
for i, v in enumerate([36, 117]):
    a1.text(i, v, str(v), ha="center", va="bottom", fontsize=13)
a1.set_title("涨停 / 跌停家数")
rel = [("黄金概念", -0.24), ("生物制药", -2.00), ("医疗器械", -3.38),
       ("有色金属", -4.49), ("电子信息", -6.05), ("电子器件", -7.15)]
barh(a2, [n for n, _ in rel], [v for _, v in rel], "四大观察对象相关板块涨跌")
fig.suptitle("2026-08-19 市场情绪与观察板块（akshare）")
fig.tight_layout(); fig.savefig("04_涨跌停与观察板块.png", dpi=150); plt.close(fig)

print("charts done")

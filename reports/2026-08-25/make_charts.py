#!/usr/bin/env python3
"""Generate 2026-08-25 review charts from collected close data. Do not invent values."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
fm.fontManager.addfont(font_path)
plt.rcParams["font.family"] = "WenQuanYi Micro Hei"
plt.rcParams["axes.unicode_minus"] = False

out = Path(__file__).resolve().parent / "charts"
out.mkdir(parents=True, exist_ok=True)

# 01 indices
fig, ax = plt.subplots(figsize=(9, 5))
names = ["上证", "深成指", "创业板", "沪深300", "纳指*"]
vals = [0.19, -0.35, -1.00, -0.24, -0.765]
colors = ["#c0392b" if v >= 0 else "#27ae60" for v in vals]
bars = ax.bar(names, vals, color=colors, width=0.6)
ax.axhline(0, color="#333", lw=0.8)
ax.set_ylabel("涨跌幅 %")
ax.set_title("2026-08-25 核心指数涨跌幅（纳指*为美东08-24收盘）")
for b, v in zip(bars, vals):
    ax.text(
        b.get_x() + b.get_width() / 2,
        v + (0.05 if v >= 0 else -0.12),
        f"{v:+.2f}%",
        ha="center",
        va="bottom" if v >= 0 else "top",
        fontsize=10,
    )
ax.set_ylim(-1.4, 0.6)
fig.tight_layout()
fig.savefig(out / "01_indices.png", dpi=140)
plt.close()

# 02 sectors
fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))
ind_names = ["陶瓷", "外贸", "纺织", "农林", "造纸", "生物制药", "电子信息", "电子器件", "有色"]
ind_vals = [4.83, 2.44, 2.44, 2.42, 2.42, 2.35, 1.42, 0.07, -2.13]
colors = ["#c0392b" if v >= 0 else "#27ae60" for v in ind_vals]
axes[0].barh(ind_names[::-1], ind_vals[::-1], color=colors[::-1])
axes[0].axvline(0, color="#333", lw=0.8)
axes[0].set_xlim(-3, 6)
axes[0].set_title("相关/强弱行业涨跌%")
axes[0].set_xlabel("%")

con_names = ["生物育种", "CRO", "CXO", "民营医院", "黄金概念", "锂矿"]
con_vals = [5.43, 5.02, 4.60, 3.88, -3.16, -2.82]
colors = ["#c0392b" if v >= 0 else "#27ae60" for v in con_vals]
axes[1].barh(con_names[::-1], con_vals[::-1], color=colors[::-1])
axes[1].axvline(0, color="#333", lw=0.8)
axes[1].set_xlim(-4, 7)
axes[1].set_title("关键概念涨跌%")
axes[1].set_xlabel("%")
fig.suptitle("2026-08-25 行业/概念强弱（新浪/主线雷达）", y=1.02)
fig.tight_layout()
fig.savefig(out / "02_sectors.png", dpi=140, bbox_inches="tight")
plt.close()

# 03 key names
fig, ax = plt.subplots(figsize=(10, 5))
names = ["凯莱英", "药明康德", "康龙化成", "寒武纪", "中芯国际", "恒瑞医药", "黄金ETF", "山东黄金", "NVDA*"]
vals = [10.00, 3.31, 3.48, 4.28, -0.48, -0.58, -0.32, -4.19, -2.91]
colors = ["#c0392b" if v >= 0 else "#27ae60" for v in vals]
bars = ax.bar(names, vals, color=colors)
ax.axhline(0, color="#333", lw=0.8)
ax.set_title("关键标的涨跌幅（NVDA*为美东08-24）")
ax.set_ylabel("%")
plt.xticks(rotation=25, ha="right")
for b, v in zip(bars, vals):
    ax.text(
        b.get_x() + b.get_width() / 2,
        v + (0.25 if v >= 0 else -0.45),
        f"{v:+.2f}",
        ha="center",
        fontsize=9,
    )
fig.tight_layout()
fig.savefig(out / "03_names.png", dpi=140)
plt.close()

# 04 limit up/down + strength
fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
axes[0].pie([65, 2], labels=["涨停 65", "跌停 2"], colors=["#c0392b", "#27ae60"], autopct="%1.1f%%", startangle=90)
axes[0].set_title("涨跌停家数对比")
board = ["CRO概念", "CXO概念", "生物制药", "电子器件", "黄金概念", "有色金属"]
bval = [5.02, 4.60, 2.35, 0.07, -3.16, -2.13]
colors = ["#c0392b" if v >= 0 else "#27ae60" for v in bval]
axes[1].barh(board[::-1], bval[::-1], color=colors[::-1])
axes[1].axvline(0, color="#333", lw=0.8)
axes[1].set_title("四观察相关强弱")
axes[1].set_xlabel("%")
fig.tight_layout()
fig.savefig(out / "04_limit_strength.png", dpi=140)
plt.close()

print("wrote", list(out.glob("*.png")))

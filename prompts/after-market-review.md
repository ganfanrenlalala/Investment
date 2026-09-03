# 交易日收盘复盘

在每个 A 股交易日 15:30 执行。必须依次调用三个 skill：`akshare-stock`、`stocksight`、`firecrawl-cli`。不要跳过其中任何一个。数据缺失时写明原因，不要编造行情或结论。

## 1. 交易日判断

先用 `akshare-stock` 查询「A股大盘」和「今日涨停统计」。

- 若确认是中国法定节假日或数据明确显示非交易日：跳过 A 股深复盘，仍用 `firecrawl-cli` 补充黄金、纳指、半导体、医药的跨境资讯，并在报告开头写明「今日非 A 股交易日」。
- 若是交易日：继续下面全部步骤。

## 2. 调用 akshare-stock

用 skill 入口执行以下查询，保留原始输出：

1. `A股大盘`
2. `今日涨停统计`
3. `市场资金流向`（默认沪深港通 + 同花顺行业资金；东财大盘主力 push2his 云端不可用，不要空转重试）
4. `行业资金流向`
5. `行业板块涨跌`
6. `概念板块涨跌`
7. `半导体板块` 或 `半导体股票推荐`
8. `医药板块` 或 `医药股票推荐`
9. `纳指行情` 或 `美股纳斯达克`
10. `黄金期货`（若接口失败，在报告中标注，改由 firecrawl 补黄金行情）

从仓库根目录调用：

```text
python3 .cursor/skills/akshare-stock/main.py --query "A股大盘"
```

## 3. 调用 stocksight

用 StockSight 做市场异动与主线扫描，策略默认 `neutral`：

1. 运行主线雷达，扫描行业和概念板块异动（默认走 AkShare/新浪板块，不要依赖东方财富 push2；云端 IP 已被东财拒绝）。
2. 对当日最值得关注的 3 到 5 只异动股（优先半导体、医药，以及涨跌停/放量异常标的）生成详细报告。
3. 若雷达或 akshare 给出明确龙头，再补 1 到 2 份个股详细报告。

从仓库根目录调用：

```text
python3 .cursor/skills/stocksight/scripts/mainline_radar.py --board all --limit 30 --out reports/YYYY-MM-DD/主线雷达.md --print
```

## 4. 调用 firecrawl-cli

检索当日资讯与外盘点评，原始检索结果写入当天文件夹的 `sources/`，不要整文件读入上下文，只抽取标题、关键数据和结论：

1. 黄金现货/期货当日行情与驱动因素
2. 全球半导体与芯片股当日表现
3. 纳斯达克指数当日或最近一晚表现（15:30 北京时间通常仍是上一交易日收盘，必须标明时点）
4. 医药/生物科技板块当日新闻与政策

命令示例：

```text
firecrawl search "黄金 现货 期货 今日行情" --scrape --limit 5 -o reports/YYYY-MM-DD/sources/gold.json --json
firecrawl search "Nasdaq semiconductor stocks today" --scrape --limit 5 -o reports/YYYY-MM-DD/sources/nasdaq-semi.json --json
firecrawl search "医药 生物 板块 今日行情" --scrape --limit 5 -o reports/YYYY-MM-DD/sources/pharma.json --json
```

## 5. 输出报告

所有当日文件都放进 Investment 项目下的日期文件夹，不要把多天内容写在同一个文件里：

```text
reports/YYYY-MM-DD/
  复盘.md
  主线雷达.md
  charts/
    data.json
    01_indices.png
    02_limit.png
    03_watch.png
    04_flow.png
  sources/
```

主报告写成 `reports/YYYY-MM-DD/复盘.md`，结构如下：

1. **今日结论**：3 到 5 条要点
2. **A 股异动**：涨跌停、资金流、主线雷达、值得跟踪的标的
3. **数据可视化**（每天必须做完下面「第 6 节」再写这一章；缺数据就跳过对应图并写明原因，禁止编造）
4. **黄金 / 半导体 / 纳指 / 医药**：各自给出行情摘要、关键数据、投资建议（观察 / 逢低关注 / 回避）
5. **次日观察点**
6. **风险提示**：数据仅供研究，不构成投资建议
7. **数据时点与来源**：akshare-stock、stocksight、firecrawl-cli

纳指、美股半导体在 15:30 通常尚未开盘，使用最近可用收盘或盘前数据，并写明时点。

写完后把当天的 `reports/YYYY-MM-DD/` 文件夹（含 `charts/`）提交并推送到仓库。

## 6. 每日可视化（强制）

表格只负责精确数字。可视化负责让人**不看表也能读懂**涨跌方向和资金量级。每天都要出图，不要只贴 Mermaid。

### 6.1 顺序

1. 正文与表格数字定稿（图中数字必须与表格一致）。
2. 把当日数字写入 `reports/YYYY-MM-DD/charts/data.json`（字段见 6.3，缺哪块就删哪块，禁止用 0 凑数）。
3. 在仓库根目录运行：

```text
python3 scripts/make_recap_charts.py reports/YYYY-MM-DD/charts/data.json
```

4. 在 `复盘.md` 的「数据可视化」里先写 3～5 条**读图要点**，再按序嵌入 PNG：

```markdown
![主要指数](charts/01_indices.png)
![涨跌停](charts/02_limit.png)
![观察对象](charts/03_watch.png)
![行业资金](charts/04_flow.png)
```

5. `charts/data.json` 和 PNG 必须随报告一起提交。

脚本已处理：涨红跌绿、横条图、柱旁数值、资金流入/流出同一坐标、中文字体（Windows YaHei / 云端 Noto 或文泉驿）。不要手写 matplotlib，不要另起一套图。

### 6.2 硬性规则

- **涨红跌绿**（A 股习惯）。柱旁必须标出数值。
- 指数、观察对象、资金一律**横条图**；涨跌停用红绿柱（跌停为 0 时不要画 0 扇区，脚本会自动省略）。
- 观察对象必须分成最多 4 组：黄金、半导体、纳指/外盘、医药。每组标题写一句人话结论，不要把 9 个名字挤在一张无分组图里。
- **资金图禁止只画净流入前 5**。至少包含：净流入前 3～5 名，以及半导体、医药（或化学制药/生物制药）若在流出前列则必须入图；用同一横轴，避免 +7 亿的柱看起来比 -49 亿还长。
- 禁止 Mermaid `pie`。不要把 Mermaid `xychart-beta` 当主图（同色、无数值、预览常坏）。GitHub 纯文本环境才允许用带双引号标题的 `xychart-beta` 作兜底，且不能替代 PNG。
- 禁止编造。某张图缺数据：`data.json` 不写该字段，报告里写「省略：原因」。

### 6.3 `data.json` 字段（用当日真实数字替换）

完整示例见 `scripts/recap_charts.example.json` 和 `reports/2026-09-02/charts/data.json`。最小结构：

```json
{
  "date": "YYYY-MM-DD",
  "indices": [
    {"name": "上证", "value": 0.19},
    {"name": "深成指", "value": -0.35},
    {"name": "创业板", "value": -1.00},
    {"name": "沪深300", "value": -0.24}
  ],
  "limits": {"up": 52, "down": 8},
  "watch_groups": [
    {"title": "黄金：现货跌、个股分化", "items": [
      {"name": "Au99.99", "value": -2.13},
      {"name": "黄金ETF", "value": -2.37},
      {"name": "山东黄金", "value": 2.71}
    ]},
    {"title": "半导体：内外偏弱", "items": [
      {"name": "半导体板块", "value": -1.34},
      {"name": "中芯国际", "value": -2.82}
    ]},
    {"title": "外盘（须标注收盘日）", "items": [
      {"name": "纳指", "value": -1.03},
      {"name": "NVDA", "value": -1.51}
    ]},
    {"title": "医药：板块弱、龙头抗跌", "items": [
      {"name": "化学制药", "value": -1.10},
      {"name": "药明康德", "value": 1.03}
    ]}
  ],
  "fund_flow": [
    {"name": "净流入第一", "value": 7.48},
    {"name": "半导体", "value": -48.95},
    {"name": "化学制药", "value": -35.65}
  ]
}
```

`value` 一律用数字：指数/个股为涨跌幅（%），资金为亿元（流出为负数）。上面的数字只是格式示范，当天必须换成采集到的真实值。

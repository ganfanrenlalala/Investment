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
3. `市场资金流向`
4. `行业板块涨跌`
5. `概念板块涨跌`
6. `半导体板块` 或 `半导体股票推荐`
7. `医药板块` 或 `医药股票推荐`
8. `纳指行情` 或 `美股纳斯达克`
9. `黄金期货`（若接口失败，在报告中标注，改由 firecrawl 补黄金行情）

从仓库根目录调用：

```text
python3 .cursor/skills/akshare-stock/main.py --query "A股大盘"
```

## 3. 调用 stocksight

用 StockSight 做市场异动与主线扫描，策略默认 `neutral`：

1. 运行主线雷达，扫描行业和概念板块异动。
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
  sources/
```

主报告写成 `reports/YYYY-MM-DD/复盘.md`，结构如下：

1. **今日结论**：3 到 5 条要点
2. **A 股异动**：涨跌停、资金流、主线雷达、值得跟踪的标的
3. **黄金 / 半导体 / 纳指 / 医药**：各自给出行情摘要、关键数据、投资建议（观察 / 逢低关注 / 回避）
4. **次日观察点**
5. **风险提示**：数据仅供研究，不构成投资建议
6. **数据时点与来源**：akshare-stock、stocksight、firecrawl-cli

纳指、美股半导体在 15:30 通常尚未开盘，使用最近可用收盘或盘前数据，并写明时点。

写完后把当天的 `reports/YYYY-MM-DD/` 文件夹提交并推送到仓库，这样本地 Investment 目录在拉取后能看到完整当日材料。

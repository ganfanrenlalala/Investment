# Investment 仓库说明

本仓库用于 A 股交易日收盘复盘。Agent 必须按 `prompts/after-market-review.md` 执行，并调用仓库内三个 skill：`akshare-stock`、`stocksight`、`firecrawl-cli`。

## Cursor Cloud specific instructions

- Skills 在 `.cursor/skills/`。不要使用 `C:\Users\...` 这类本机路径。
- Python 入口：
  - `python3 .cursor/skills/akshare-stock/main.py --query "..."`（资金流：市场资金走沪深港通+同花顺行业，不要依赖东财 push2his 大盘主力） 
  - `python3 .cursor/skills/stocksight/scripts/mainline_radar.py ...`（默认 `--provider auto`，优先 AkShare/新浪板块，不要先打东财 push2）
  - `python3 .cursor/skills/stocksight/scripts/report.py ...`
- Firecrawl：`firecrawl search ...`。密钥来自 Secrets 中的 `FIRECRAWL_API_KEY`，不要走浏览器登录。
- 报告写入 `reports/YYYY-MM-DD/`，主文件为 `复盘.md`。
- 终稿必须含 Mermaid 可视化：指数涨跌、涨跌停对比、四观察对象/关键标的涨跌；缺数据就省略该图并注明，不要编造。
- 不要编造行情。某个 skill 失败时写明原因，用其余来源继续。
- 内容仅供研究，不构成投资建议。

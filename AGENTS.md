# Investment 仓库说明

本仓库用于 A 股交易日收盘复盘。Agent 必须按 `prompts/after-market-review.md` 执行，并调用仓库内三个 skill：`akshare-stock`、`stocksight`、`firecrawl-cli`。Cursor Automation 定时任务提示词见 `prompts/cursor-automation.md`（触发后先 `git fetch origin master` 再读最新文件）。

## Cursor Cloud specific instructions

- Skills 在 `.cursor/skills/`。不要使用 `C:\Users\...` 这类本机路径。
- Python 入口：
  - `python3 .cursor/skills/akshare-stock/main.py --query "..."`（资金流：市场资金走沪深港通+同花顺行业，不要依赖东财 push2his 大盘主力） 
  - `python3 .cursor/skills/stocksight/scripts/mainline_radar.py ...`（默认 `--provider auto`，优先 AkShare/新浪板块，不要先打东财 push2）
  - `python3 .cursor/skills/stocksight/scripts/report.py ...`
- Firecrawl：`firecrawl search ...`。密钥来自 Secrets 中的 `FIRECRAWL_API_KEY`，不要走浏览器登录。
- 报告写入 `reports/YYYY-MM-DD/`，主文件为 `复盘.md`。
- 终稿必须含可视化：按 `prompts/after-market-review.md` 第 6 节，写 `charts/data.json` 后运行 `python3 scripts/make_recap_charts.py reports/YYYY-MM-DD/charts/data.json`，把 PNG 嵌入 `复盘.md`。缺数据就省略并注明，不要编造。不要用 Mermaid `pie` 当主图。
- 不要编造行情。某个 skill 失败时写明原因，用其余来源继续。
- **交付到 master**：写完当日 `reports/YYYY-MM-DD/`（含 `charts/`）后必须 `git push`，并用 `open_git_pr` 开到 `master` 的 PR，再合并进 `master`（可本地 merge 后 `git push origin master`，或启用 PR auto-merge）。不要只停在临时 agent 分支。
- 内容仅供研究，不构成投资建议。

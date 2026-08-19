# 仓库内 Skills

定时任务跑在 Cursor Cloud，读不到本机 `~/.cursor/skills`。这三个 skill 已迁到仓库，提交并推送后，绑定本仓库的 Cloud Agent / Automation 才能调用。

| Skill | 调用 | 作用 |
| --- | --- | --- |
| `akshare-stock` | `/akshare-stock` | A 股行情、涨跌停、资金流、板块、纳指等 |
| `stocksight` | `/stocksight` | 异动扫描、主线雷达、个股详细报告 |
| `firecrawl-cli` | `/firecrawl-cli` | 检索/抓取黄金、半导体、纳指、医药资讯 |

从仓库根目录调用，不要使用本机绝对路径。依赖见根目录 `requirements.txt`。Firecrawl 需要环境变量 `FIRECRAWL_API_KEY`。

# Investment

个人投资研究与交易日收盘复盘工作区。

## 基本信息

| 项目 | 内容 |
|------|------|
| 仓库 | Investment |
| 作者 | ganfanrenlalala |
| 用途 | A 股交易日收盘后自动复盘，并跟踪黄金、半导体、纳指、医药 |
| 运行时间 | 周一到周五 15:30（北京时间，A 股收盘后约 30 分钟） |
| 报告目录 | `reports/YYYY-MM-DD/`，每天一个文件夹 |
| 复盘说明 | `prompts/after-market-review.md` |

## 每日做什么

1. 判断当天是否为 A 股交易日
2. 用 **akshare-stock** 拉取大盘、涨跌停、资金流、半导体/医药板块和纳指行情
3. 用 **stocksight** 扫描市场异动和主线
4. 用 **firecrawl-cli** 检索黄金、半导体、纳指、医药的当日资讯
5. 汇总投资建议，写入 `reports/YYYY-MM-DD/`（每天一个文件夹，主报告为 `复盘.md`）

纳指和美股半导体在 15:30 通常尚未开盘，报告会使用最近可用数据并标明时点。内容仅供研究，不构成投资建议。

## Skills（已迁入本仓库）

Cloud 定时任务只能使用仓库内 skill，不能使用本机 `~/.cursor/skills`。

| Skill | 路径 |
| --- | --- |
| akshare-stock | `.cursor/skills/akshare-stock` |
| stocksight | `.cursor/skills/stocksight` |
| firecrawl-cli | `.cursor/skills/firecrawl-cli` |

依赖：`python3 -m pip install -r requirements.txt`，并全局安装 `firecrawl-cli`。Firecrawl 需要环境变量 `FIRECRAWL_API_KEY`（Cloud Agents 控制台 Secrets）。

迁移后请 **commit 并 push**，再在 Automations 里绑定本仓库；否则云端仍然找不到这些 skill。

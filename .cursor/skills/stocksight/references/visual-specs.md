# StockSight Visual Specs

Use this reference when exact report formatting matters. Keep generated reports compact, scannable, and consistent. The default style is premium Markdown with a small amount of GitHub-compatible HTML.

## Report Order

Every report uses this order:

1. H1 report title
2. One-line summary blockquote
3. Top metric strip: `市场脉冲` for standard reports or `核心看板` for detailed reports
4. Risk visualization: risk distribution and signal composition
5. Optional data-quality notes
6. Core data section
7. Optional detailed analysis section
8. Risk section
9. Optional action suggestions
10. Optional company announcements / hard information and related market news in `<details>`
11. Data source line

## Premium Markdown Elements

Use only lightweight, portable HTML:

| Element | Purpose | Example |
|------|------|------|
| `<kbd>...</kbd>` | Compact badges for risk type, market state, and labels | `<kbd>量比偏离</kbd>` |
| `<details><summary>...</summary>` | Collapsible context section | `<summary>🗞️ 公司信息与资讯</summary>` |
| `▰▱` bars | Signal/risk intensity | `▰▰▰▱▱` |

Avoid CSS, scripts, external images, and complex HTML tables.

Markdown reports may include Unicode-only visual summaries:

- Risk distribution table: `关注 / 警告 / 危险` counts with `▰▱` bars.
- Signal composition table: risk type, count, highest level, and distribution bar.
- Data-quality notes when a metric is unavailable or clearly outside normal bounds.

HTML reports rendered by `render_html_report(data, mode)` may use built-in CSS only:

- CSS bar charts for risk counts and signal composition.
- CSS `conic-gradient` pie charts for risk-level and signal-type proportions.
- No JavaScript, external images, web fonts, or external stylesheets.

Detailed reports should also include:

- A report context section near the top with quote timestamp, historical indicator cutoff date, and snapshot replay status.
- The report context should include a compact source chain when available: live quote provider, historical provider, fallback status, and historical bar count.
- A final judgment section with stance, primary risk, and next confirmation point.
- A data credibility section that marks fields as confirmed, derived, unavailable, or history-computed.
- Unavailable or derived fields must be shown transparently and should not create direct risk signals by themselves.

## Emoji Semantics

| Symbol | Meaning |
|------|------|
| 📰 | report title or summary |
| 📋 | list/table section |
| 🔍 | detailed analysis |
| ⚠️ | risk section |
| 🎯 | conclusion or action suggestions |
| 🗞️ | related news |
| 📡 | data source |
| 🕐 | timestamp |
| 📈 / 📉 / ➡️ | up / down / flat |
| 💰 | price |
| 📊 | volume or amount |
| 📐 | change percent |
| ⚡ | volume ratio |
| 🔄 | turnover rate |
| 🔥 | anomaly signal |
| 🔸 / 🔶 / 🔴 | watch / warning / danger |
| 🟢 / 🟡 / 🔴 | positive / hold or watch / avoid |
| ▰ / ▱ | filled / empty signal intensity units |

## Table Rules

- Keep tables at 3 to 5 columns.
- Standard anomaly tables may use 5 columns: `股票 | 现价 | 涨跌幅 | 量比 | 异动信号`.
- Standard risk tables may use 4 columns: `股票 | 风险类型 | 偏离说明 | 等级`.
- Use `—` for unavailable values instead of dropping a row.
- Put key identity columns on the left and numeric metrics to the right.

## Number Formatting

| Metric | Format |
|------|------|
| A-share price | `RMB x.xx` |
| Hong Kong price | `HKD x.xx` |
| US price | `USD x.xxxx` |
| Change percent | signed percent plus trend emoji, such as `+3.2% 📈` |
| Volume ratio | two decimals, or `—` when unavailable |
| Turnover rate | one decimal percent |
| Amount | integer in ten-thousand units, with currency prefix when known |

For unavailable or suspicious metrics, render `—` and add a data-quality note. Treat turnover rate values `<= 0` or `> 100` as unavailable unless a provider-specific implementation proves they are reliable.

## Cross-Market Rules

| Market | Code | Tag | Currency |
|------|------|------|------|
| Shanghai A-share | `sh` | `[A]` | RMB |
| Shenzhen A-share | `sz` | `[A]` | RMB |
| Hong Kong | `hk` | `[H]` | HKD |
| US | `us` | `[U]` | USD |

Place market tags after the stock name with a space: `600570 恒生电子 [A]`.

When a report mixes markets, sort rows as A-share, Hong Kong, then US. Hong Kong and US rows usually have no volume ratio or turnover rate; show `—` and skip unavailable detection dimensions.

## News Section

Render news only when `ReportData.news` is non-empty. Split items by category:

- Company announcements and hard information: announcements, filings, earnings previews, risk notices, major events, shareholder changes, investor Q&A.
- Market news and sentiment: generic financial news, anomaly commentary, topic context.

Search-backed hard information must label source credibility in the snippet or source. Prefer exchange, CnInfo, Eastmoney announcements, company sites, and investor-relations sources ahead of generic market media.

Standard reports:

```markdown
<details>
<summary>🗞️ 公司信息与资讯</summary>

| 来源 | 标题 | 时间 |
|:---|:---|:---|
| 新浪财经 | 恒生电子成交活跃 | 05-18 10:00 |

</details>
```

Detailed reports:

```markdown
<details>
<summary>🗞️ 公司信息与资讯</summary>

[新浪财经] 恒生电子成交活跃（05-18 10:00）
  盘中成交显著放大，资金关注度提升

</details>
```

## Failure Handling

- Missing news API key: skip context/news.
- News provider error: skip context/news and keep the core report.
- Empty news results: skip context/news.
- Missing market metric: show `—`.
- Suspicious market metric: show `—` and add a data-quality note.
- No usable quote data: return a short unavailable-data message.

## Disclaimer

Operation suggestions, target prices, and stop-loss values are technical references only and do not constitute investment advice.

## MACD / RSI / BOLL / KDJ Technical Indicators

- Detailed single-stock HTML reports may include a static MACD SVG chart plus RSI/BOLL/KDJ range panels.
- Detailed Markdown reports may include a compact "技术指标辅助" table.
- MACD/RSI/BOLL/KDJ are computed only when A-share or US historical bars are available. A-share history should use EastMoney first and may fall back to Sina/Tencent daily K-lines.
- BOLL highlights upper/lower band pressure; KDJ highlights short-term overbought/oversold and cross signals.
- Bearish technical signals may be converted into `RiskSignal` entries for risk distribution and signal composition.
- Bullish technical signals are displayed as auxiliary context and must not reduce existing risk scores.
- Snapshot replay must use the saved `ReportData.technical` payload instead of refetching history or recomputing indicators.

## Risk Model Notes

- Separate anomaly strength from risk severity.
- A-share limit-up moves default to strong anomaly / warning, not danger.
- Upgrade upward moves to danger only when extreme volume ratio, high turnover, bearish divergence, or similar weakening evidence confirms overheating.
- Limit-down or sharp falling moves may remain danger by direction.

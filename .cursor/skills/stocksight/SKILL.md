---
name: stocksight
description: Agent-ready stock anomaly analyst for A-share, Hong Kong, and US equities. Use when Codex needs to fetch quotes, clean suspicious market fields, search free A-share announcement sources, detect unusual volume/turnover/return/MACD/RSI/BOLL/KDJ signals, choose neutral/mainline/risk_avoid/swing operation-suggestion views, render premium Markdown/HTML stock reports, replay deterministic snapshots, or validate StockSight report formatting.
---

# StockSight

Use this skill to produce StockSight stock anomaly reports from market data. Keep the workflow data-first: fetch quotes, clean fields, detect signals, optionally add MACD/RSI/BOLL/KDJ technical analysis for detailed A-share or US reports, optionally add news, render Markdown or self-contained HTML, then validate Markdown before returning it.

Recommended setup for downloaded agents: ask the user which operation-suggestion view they want by default (`neutral`, `mainline`, `risk_avoid`, or `swing`), and use `neutral` when they do not choose. `--news` works without paid keys by searching free public A-share announcement sources first; configure Tavily or SerpAPI only when broader market-news context is desired. When the user wants a shareable visual artifact, generate HTML first and then use `scripts/screenshot_report.py` to create a long PNG screenshot.

## Environment

This skill lives in the Investment repo. Run commands from the **repository root**. Cloud Agents already install `requirements.txt` during environment setup.

```bash
python3 .cursor/skills/stocksight/scripts/report.py 002346 --mode detailed
python3 .cursor/skills/stocksight/scripts/mainline_radar.py --board all --limit 30 --out reports/YYYY-MM-DD/主线雷达.md --print
```

If dependencies are missing:

```bash
python3 -m pip install -r requirements.txt
```

If dependency installation is unavailable, still use this skill for report formatting when the user provides structured `StockData`-like inputs. Do not use machine-specific Windows venv paths.

The remaining `python scripts/...` examples in this file assume the working directory is `.cursor/skills/stocksight`. From the repository root, prefix paths with `.cursor/skills/stocksight/`.

## Workflow

1. Build one or more `StockData` records from provider data.
2. Run `normalize_quote_data(stocks)` before detection.
3. Run `detect(stocks)` or `detect_anomalies(stocks)` to produce `RiskSignal` entries.
4. For detailed single-stock A-share or US reports, compute MACD/RSI/BOLL/KDJ with `analyze_technical_indicators(history)` and set `ReportData.technical`. A-share history should try EastMoney first, optional AkShare next, then the Sina/Tencent fallback history provider when bars are missing or insufficient.
5. Optionally search company context with `--news`. For A-shares, use the free public hard-information sources first: announcements, filings, earnings previews, risk notices, major events, and shareholder changes. Tavily/SerpAPI are optional fallback providers when configured. If lookup fails or returns no results, skip the section and continue.
6. Create `ReportData` with title, summary, stocks, signals, data source, timestamp, optional `news`, optional `technical`, and optional `strategy_profile`.
7. Render Markdown with `render_standard_report(data)` for multi-stock reports, or `render_detailed_report(data)` for single-stock deep dives.
8. Render browser-ready HTML with `render_html_report(data, mode="standard"|"detailed")` when the user wants a polished report page.
9. Prefer `scripts/screenshot_report.py` after HTML generation when the user wants an image, README screenshot, social preview, or shareable long report.
10. Run `validate_report(report_text, data)` for Markdown output and fix formatting issues before presenting the report.

For a one-command live report:

```bash
python scripts/report.py 002346 --mode detailed --html --out reports/002346.html
```

For a strategy-specific detailed report:

```bash
python scripts/report.py 002346 --mode detailed --strategy risk_avoid --news --html --out reports/002346-risk.html --markdown-out outputs/002346-risk.md
python scripts/report.py 002346 --mode detailed --strategy swing --html --out reports/002346-swing.html --markdown-out outputs/002346-swing.md
```

Strategy profiles affect only the operation-suggestion card:

| Profile | Use |
|:---|:---|
| `neutral` | Default neutral report posture |
| `mainline` | A-share mainline first-wave middle segment fit |
| `risk_avoid` | Hard-risk screening before participation |
| `swing` | General swing-trend tracking |

With `--strategy mainline`, detailed reports separate "mainline direction" from "Swing buy point". Use the mainline score to decide whether the direction belongs in the candidate flow, and use the swing score to decide whether the single stock has a breakout, pullback, hold, cooldown, or exit setup.

For a market-wide A-share mainline radar scan:

```bash
python scripts/mainline_radar.py --board all --limit 30 --out outputs/mainline-radar/today.md
```

The radar reports automatic observable heat separately from the user's full 10-item mainline score. Unknown items are listed as pending; do not count them as zero or as passed. Use the radar to find directions, then use detailed reports with `--strategy mainline` or `--strategy swing` for single-stock fit and timing.

To capture a long PNG screenshot from an HTML report:

```bash
python scripts/screenshot_report.py reports/002346.html --out docs/images/002346-full.png --engine cdp --timeout 60
```

Cloud Linux agents should not call snap Chromium's raw `--screenshot` command
for StockSight reports. On Ubuntu 24.04, snap Chromium commonly captures only a
tall viewport instead of the full document, producing a mostly blank long PNG
with fixed navigation/watermark elements floating in the middle or bottom. Use
`scripts/screenshot_report.py` instead; it disables report animations and uses
Playwright or Chrome DevTools Protocol for true full-page capture.

Recommended Hermes/Linux setup:

```bash
source ~/.hermes/hermes-agent/venv/bin/activate
python -m pip install -U pip
python -m pip install playwright
python -m playwright install --with-deps chromium
python scripts/screenshot_report.py reports/002346.html --out reports/002346-full.png --engine playwright --timeout 60
```

If Playwright installation is interrupted or unavailable, install non-snap
Chrome and force the dependency-free CDP path:

```bash
wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt-get update
sudo apt-get install -y /tmp/google-chrome.deb
export STOCKSIGHT_BROWSER=/usr/bin/google-chrome
python scripts/screenshot_report.py reports/002346.html --out reports/002346-full.png --engine cdp --timeout 60
```

For reproducible cross-agent output, save a snapshot once and render from it later:

```bash
python scripts/report.py 002346 --provider tencent --mode detailed --save-snapshot snapshots/002346.json --html --out reports/002346.html
python scripts/report.py --from-snapshot snapshots/002346.json --html --out reports/002346-replay.html --markdown-out outputs/002346-replay.md
```

When rendering from `--from-snapshot`, do not fetch live quotes, re-run news search, re-detect signals, or recompute MACD/RSI/BOLL/KDJ. The snapshot is the source of truth.

If the user needs PDF, generate HTML first and let the user export it from their own browser or system PDF tools.

## Provider Guidance

- Use `TencentDataSource` for A-share and Hong Kong quote data when available.
- Use `YahooFinanceDataSource` for US tickers when no paid market-data key is available.
- Use `SinaDataSource` as a fallback quote provider when Yahoo or Tencent cannot return data.
- Use `EastMoneyDataSource` for A-share quotes and optional sector benchmark support.
- Use `AShareHistoryDataSource` only as an A-share historical K-line fallback for technical indicators.
- Prefer `DataSourceFactory` or `scripts/report.py --provider auto` when chaining providers.

## Configuration

Read `.sightconfig.json` from the current directory, this skill directory, or the user home directory. The top-level key is `stock_sight`; see `config.example.json`.

News providers are optional. Supported API key sources:

- `stock_sight.tavily.api_key` or `TAVILY_API_KEY`
- `stock_sight.serpapi.api_key` or `SERPAPI_API_KEY`

## Output Rules

- Follow `references/visual-specs.md` when exact formatting matters.
- Use `references/examples.md` for full standard, detailed, cross-market, and news-enabled examples.
- Use lightweight GitHub-compatible HTML (`<kbd>` and `<details>`) plus Unicode signal bars for Markdown polish.
- Use `render_html_report` for a full browser-ready page with built-in CSS charts; do not hand-write one-off HTML reports as the core output path.
- Use `scripts/screenshot_report.py` when the user wants a shareable long screenshot of a generated HTML report; prefer it over PDF export for visual sharing.
- Put a data source line at the end of every report.
- Do not block the core report on missing news API keys, news provider failures, or empty news results.
- Treat announcement/filing items as context, not as deterministic trading signals unless the detector or technical analysis also supports the conclusion.
- Use `—` for unavailable market metrics such as Hong Kong or US volume ratio.
- In detailed reports, include the generated final judgment and data credibility sections; do not invent a separate conclusion outside the rendered report.
- Keep the generated report context visible near the top: quote timestamp, historical indicator cutoff date, and whether the output was rendered from a snapshot.
- Include the data-source chain when available: live quote provider, historical provider, fallback status, and historical bar count.
- Show data-quality notes when a metric is unavailable or clearly outside normal bounds.
- Treat A-share limit-up moves as strong anomalies by default, not automatic danger signals; only escalate upward moves to danger when volume/turnover or technical evidence confirms overheating.
- Treat MACD/RSI/BOLL/KDJ as technical references. Bearish technical signals may raise risk, but bullish signals do not lower existing risk.
- Include a brief investment-risk disclaimer when giving target or stop-loss style reference values.

## Error Handling

- Missing dependency: tell the user to install `requirements.txt`, or continue with formatting only if structured data is already available.
- Missing or invalid quote data: return a short unavailable-data message instead of fabricating values.
- Missing news API key, request failure, or empty news results: skip the news section.
- Invalid stock code: ask for a market-qualified code or a recognizable A-share, Hong Kong, or US ticker.

## File Map

```text
stocksight/
|-- SKILL.md
|-- core/          # types, config, data-source abstraction, detection
|-- formatter/     # standard/detailed/html rendering and validation
|-- news/          # optional news provider abstraction and implementations
|-- providers/     # quote providers
|-- scripts/       # one-command report generation
`-- references/    # visual contract and examples
```

## Development Notes

- Keep public API names stable: `DataSourceFactory.fetch`, `detect`, `detect_anomalies`, `render_standard_report`, `render_detailed_report`, `render_html_report`, and `validate_report`.
- Keep snapshot compatibility stable for `schema_version: 1` unless a migration path is added.
- Install runtime dependencies from `requirements.txt` before importing network providers.

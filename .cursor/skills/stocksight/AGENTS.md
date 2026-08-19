# AGENTS.md - StockSight Usage Guide for AI Agents

This guide is for agents such as Hermes, Cursor, Codex, Copilot, and other automation systems that need to invoke StockSight to produce stock anomaly reports.

## What StockSight Does

StockSight fetches quotes, cleans suspicious fields, detects unusual volume, turnover, return, MACD, RSI, BOLL, and KDJ signals, then renders polished Markdown or self-contained HTML reports.

## Quick Invocation

Recommended after installation:

- `--news` searches free public announcement sources first, currently CNINFO and EastMoney notices. Configure Tavily or SerpAPI when possible to add broader market news, filings context, earnings previews, and risk notices.
- Ask the user which operation-suggestion strategy view they prefer by default: `neutral`, `mainline`, `risk_avoid`, or `swing`. If they do not choose one, use `neutral`.
- Generate HTML first, then use `scripts/screenshot_report.py` when the user wants a shareable long PNG report.

Generate a live detailed A-share report:

```bash
python scripts/report.py 002346 --mode detailed --html --out reports/002346.html --markdown-out outputs/002346.md
python scripts/screenshot_report.py reports/002346.html --out reports/002346-full.png
```

Use an optional strategy profile:

```bash
python scripts/report.py 002346 --mode detailed --strategy mainline --html --out reports/002346-mainline.html --markdown-out outputs/002346-mainline.md
python scripts/report.py 002346 --mode detailed --strategy risk_avoid --html --out reports/002346-risk.html --markdown-out outputs/002346-risk.md
python scripts/report.py 002346 --mode detailed --strategy swing --html --out reports/002346-swing.html --markdown-out outputs/002346-swing.md
```

`--strategy` changes only the operation-suggestion perspective and does not turn StockSight into a buy/sell recommendation engine. Omit the flag, or use `--strategy neutral`, to keep the default neutral report posture.
When `--strategy mainline` is used, detailed reports also separate the mainline direction score from the swing buy-point score: the mainline layer answers whether the direction is worth doing, while the swing layer answers whether the single stock has a timing/hold setup.

| Strategy | Perspective | Use when |
|:---|:---|:---|
| `neutral` | Default neutral report posture | The user has not chosen a personal strategy view |
| `mainline` | A-share mainline first-wave middle segment | Checking whether the current stock fits the mainline trend setup |
| `risk_avoid` | Risk-screening / risk-avoidance view | Screening ST, delisting, regulatory, earnings, reduction, pledge, or breakdown risks first |
| `swing` | Swing-trend view | Tracking breakout, pullback, trend-hold, cooldown, and exit conditions |

Backtest and calibrate the Swing profile before presenting historical strategy performance:

```bash
python scripts/backtest.py 002346 600570 300750 --days 800 \
  --out outputs/backtests/swing-backtest.md \
  --calibration-out outputs/backtests/swing-calibration.json \
  --trades-out outputs/backtests/swing-observations.csv

python scripts/report.py 002346 --mode detailed --strategy swing \
  --calibration-file outputs/backtests/swing-calibration.json \
  --html --out reports/002346-swing.html
```

The backtest is point-in-time: a state is evaluated after the daily close, entry uses the next trading day's open, and only the first transition into a new strategy state is counted. Historical volume ratio is reconstructed as daily volume divided by the prior five-day average, not as a provider intraday volume-ratio field. The primary label is positive net return after 10 trading days, with 5-day and 20-day statistics also retained. Default round-trip cost is 10 bps and is configurable with `--cost-bps`.

Use multiple symbols for calibration. Treat fewer than 10 matching observations as insufficient, 10-29 as low reliability, 30-99 as medium, and 100+ as higher reliability. Calibration JSON is accepted only when its strategy version matches the current Swing implementation.

Generate a price- and volatility-based execution plan:

```bash
python scripts/report.py 002346 --mode detailed --strategy swing \
  --account-size 100000 \
  --risk-per-trade 0.5 \
  --max-position 20 \
  --atr-period 14 \
  --max-stop-percent 8 \
  --html --out reports/002346-plan.html
```

The plan uses ATR(14), recent structural support, 20-day resistance, and an account risk budget. It outputs an entry trigger/range, structural stop, two R-based targets, stop distance, and position size. A-share quantities are rounded down to 100-share lots. Do not replace unavailable history with fixed `-5%` / `+5.6%` levels. When stop distance exceeds the configured maximum, price has already run beyond the entry zone, or the strategy is in exit/risk-avoid mode, preserve the wait/zero-position result.

Persist the candidate-to-review lifecycle:

```bash
python scripts/report.py 002346 --mode detailed --strategy swing \
  --account-size 100000 --lifecycle-file portfolios/trades.json \
  --html --out reports/002346-live.html

python scripts/report.py 002346 --mode detailed --strategy swing \
  --lifecycle-file portfolios/trades.json \
  --fill-price 16.82 --fill-shares 500

python scripts/report.py 002346 --mode detailed --strategy swing \
  --lifecycle-file portfolios/trades.json \
  --exit-price 18.36 --exit-reason "target reached"

python scripts/report.py 002346 --mode detailed --strategy swing \
  --lifecycle-file portfolios/trades.json \
  --review-grade B --review-note "correct direction, early add"
```

Lifecycle rules:

- Candidate and triggered states can advance automatically from the live daily price range.
- Holding requires an actual fill confirmation through `--fill-price`; do not treat a signal as a fill.
- A holding can exit automatically when the daily range hits the planned stop or second target, or when the strategy becomes invalid. A manual `--exit-price` records the actual exit instead.
- Review is allowed only after exit and stores the note, optional A-D grade, P&L, R multiple, holding days, and the full transition audit trail.
- Snapshot replay may display a lifecycle from `--lifecycle-file`, but it must not mutate the ledger.

Scan A-share industry/concept mainline radar:

```bash
python scripts/mainline_radar.py --board all --limit 30 --out outputs/mainline-radar/today.md
```

The mainline radar is a market-direction scanner, not a single-stock buy/sell engine. It outputs an automatic radar score plus a pending checklist for the user's 10-item mainline score. Only treat a direction as entering the observation/candidate flow after the full 10-item score reaches 6; unknown items must remain pending instead of being counted as zero.

Generate a US equity report:

```bash
python scripts/report.py TSLA --provider yahoo --mode detailed --html --out reports/TSLA.html
```

Provider selection:

| Provider | Use for | Flag |
|:---|:---|:---|
| Tencent | A-share, Hong Kong | `--provider tencent` |
| Yahoo | US equities | `--provider yahoo` |
| Sina | Fallback for A/HK/US | `--provider sina` |
| EastMoney | A-share plus sector benchmark | `--provider eastmoney` |
| AkShare | Optional A-share quote and daily K-line fallback | `--provider akshare` |
| Auto | Chains providers | `--provider auto` |

If a provider call fails, `--provider auto` tries the next available provider.
AkShare is optional and not required for the default install. To use `--provider akshare`, install it separately with `pip install akshare`; if it is missing, `--provider auto` will continue to the other providers.

For detailed A-share reports, technical history uses EastMoney first and then falls back to public Sina/Tencent daily K-lines when EastMoney does not return enough bars.
Reports should expose the data-source chain near the top so another agent can see the live quote provider, historical provider, fallback status, and historical K-line bar count.
When `--news` is enabled, StockSight searches A-share hard information first through free public announcement sources: announcements, filings, earnings previews, risk notices, major events, and shareholder changes. Tavily or SerpAPI results are optional fallback context when configured. Generic market news is only fallback context.

## Snapshot Workflow

Snapshots lock report inputs and output context for consistent cross-agent behavior.

Save a snapshot:

```bash
python scripts/report.py 002346 --provider tencent --mode detailed --save-snapshot snapshots/002346.json --html --out reports/002346.html
```

Replay from a snapshot:

```bash
python scripts/report.py --from-snapshot snapshots/002346.json --html --out reports/002346-replay.html --markdown-out outputs/002346-replay.md
```

Offline demo:

```bash
python scripts/report.py --from-snapshot examples/a-share-detailed.json --html --out reports/sample.html --markdown-out outputs/sample.md
```

Render fixed formatter comparison examples:

```bash
python scripts/render_examples.py
```

Capture a long PNG screenshot from a generated HTML report:

```bash
python scripts/screenshot_report.py reports/002346.html --out docs/images/002346-full.png --engine cdp --timeout 60
```

If Chrome / Edge is installed in a custom location, set `STOCKSIGHT_BROWSER` to the executable path.

Cloud Linux screenshot note:

- Do not use snap Chromium's raw `--screenshot` command for long StockSight reports. On Ubuntu 24.04 it often captures only a tall viewport, leaving a mostly blank PNG with fixed side navigation and watermark elements in the middle/bottom.
- Prefer Playwright when it is installed:

```bash
source ~/.hermes/hermes-agent/venv/bin/activate
python -m pip install -U pip
python -m pip install playwright
python -m playwright install --with-deps chromium
python scripts/screenshot_report.py reports/002346.html --out reports/002346-full.png --engine playwright --timeout 60
```

- If Playwright installation is interrupted, install non-snap Chrome and force the dependency-free CDP path:

```bash
wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt-get update
sudo apt-get install -y /tmp/google-chrome.deb
export STOCKSIGHT_BROWSER=/usr/bin/google-chrome
python scripts/screenshot_report.py reports/002346.html --out reports/002346-full.png --engine cdp --timeout 60
```

When rendering from `--from-snapshot`, do not fetch live quotes, re-run news search, re-detect signals, or recompute MACD/RSI/BOLL/KDJ. The snapshot is the source of truth.

## Python API

```python
from core import (
    ReportData,
    StockHistory,
    analyze_technical_indicators,
    detect,
    normalize_quote_data,
)
from formatter import render_detailed_report, render_html_report, validate_report
from providers import TencentDataSource

provider = TencentDataSource()
stocks = normalize_quote_data(provider.fetch(["002346"]))
signals = detect(stocks)
history = provider.fetch_history("002346", days=80)
technical = analyze_technical_indicators(history)

data = ReportData(
    title="StockSight Report",
    summary="Generated by StockSight",
    stocks=stocks,
    signals=signals,
    data_source=provider.name,
    timestamp=stocks[0].timestamp,
    technical=technical,
)

markdown = render_detailed_report(data)
html = render_html_report(data)
result = validate_report(markdown, data)
```

## Report Shape

Standard reports cover market pulse, risk visualization, stock table, risk warnings, operation suggestions, optional company announcements/hard information, optional market news, and data source.

Detailed reports cover report context, final judgment, core dashboard, risk visualization, data credibility, price overview, volume/price metrics, MACD/RSI/BOLL/KDJ trend summary, anomaly analysis, risk warnings, operation suggestions, optional company announcements/hard information, optional market news, and data source.

Risk model note: A-share limit-up moves are strong anomalies, not automatic danger signals. Escalate upward moves to danger only when extreme volume ratio, high turnover, bearish divergence, or other weakening evidence confirms overheating. Limit-down or sharp falling moves remain higher-risk by direction.

## Key Files

| File | Purpose |
|:---|:---|
| `scripts/report.py` | One-command report CLI |
| `scripts/screenshot_report.py` | Long PNG screenshot helper for HTML reports |
| `core/analysis.py` | MACD, RSI, BOLL, KDJ, trend summary, divergence |
| `core/detector.py` | Volume, turnover, return anomaly detection |
| `formatter/detailed.py` | Markdown detailed renderer |
| `formatter/html.py` | HTML report renderer |
| `formatter/html_charts.py` | Gauge, radar, MACD/RSI/BOLL/KDJ, trend panels |
| `formatter/base.py` | Shared formatting, data credibility, final judgment |

## Error Handling

- Missing `requests`: ask the user to run `pip install -r requirements.txt`, or use `--from-snapshot`.
- Invalid stock code: ask for a market-qualified code or recognizable ticker.
- Network failure: retry once with another provider, preferably `--provider auto`.
- No news API key: skip news; the core report still renders.
- Missing or invalid quote fields: StockSight displays `—` and labels data credibility.

## Dependencies

Runtime dependency:

```text
requests>=2.25.0
```

HTML reports are self-contained. PDF export is intentionally not maintained because system fonts made Chinese output unreliable.

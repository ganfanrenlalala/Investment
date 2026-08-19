# Changelog

## v0.6.0 - 2026-06-11

Strategy research and execution lifecycle release. StockSight now connects historical validation, calibrated live context, volatility-based execution plans, and persistent post-trade review.

### Added
- Added a point-in-time Swing backtest CLI with versioned local history caching, next-open entry assumptions, 5/10/20-day net returns, MFE/MAE, and CSV event ledgers.
- Added chronological holdout probability calibration with Brier Score and expected calibration error diagnostics.
- Added optional `--calibration-file` support so detailed Swing reports can display matched historical probability, return, sample-size, and reliability context.
- Added ATR- and structure-based trade plans with entry triggers, stop levels, two R-based targets, account risk budgets, and lot-aware position sizing.
- Added a persistent candidate → triggered → holding → exited → reviewed lifecycle ledger with audited transitions, actual fill/exit confirmation, automatic stop/target handling, P&L, R multiple, holding days, and post-trade review.

### Changed
- Exposed Swing score, score maximum, score factors, and strategy version as structured `StrategyDecision` fields.
- Expanded EastMoney daily history bars with optional amount, change-percent, and turnover fields for historical reconstruction.
- Replaced fixed `-5%` stop and `+5.6%` target copy with snapshot-safe volatility plans; missing history now renders the plan as unavailable.
- Updated the README report screenshots and bumped the README badge and HTML footer version to `v0.6.0`.

## v0.5.0 - 2026-06-09

Mainline radar and separated strategy execution release. StockSight can now scan market directions before evaluating single-stock timing, keeping mainline fit and swing buy-point structure distinct.

### Added
- Added A-share mainline radar CLI for scanning EastMoney industry/concept boards with automatic radar scores and pending 10-item mainline checks.
- Added separated mainline-direction and Swing buy-point scorecards to detailed `--strategy mainline` reports.

### Changed
- Expanded EastMoney board parsing with concept-board support, breadth, leader, turnover, and main-net-inflow fields for radar scoring.
- Updated AGENTS/README/SKILL guidance for the mainline radar flow and separated mainline/swing report sections.
- Bumped the README badge and HTML footer version to `v0.5.0`.

## v0.4.0 - 2026-06-03

Strategy profiles and free A-share hard-information release. StockSight now keeps the default neutral posture while allowing agents to render operation suggestions from mainline, risk-screening, or swing-trend views.

### Added
- Added `--strategy risk_avoid` for a conservative risk-screening view that prioritizes ST/delisting, regulatory, earnings, reduction, pledge, hard-risk news, and breakdown signals.
- Added `--strategy swing` for a swing-trend view covering breakout candidates, trend hold, pullback watch, cooldown, and exit conditions.
- Added optional AkShare quote/history provider support for A-share fallback usage.
- Added free CNINFO and EastMoney announcement providers to the `--news` chain before optional Tavily/SerpAPI market-news providers.
- Added tests for strategy-profile rendering, snapshot compatibility, provider fallbacks, and free announcement parsing.

### Changed
- Expanded `--strategy` choices to `neutral`, `mainline`, `risk_avoid`, and `swing`; neutral remains the default report posture.
- Updated AGENTS/README/SKILL guidance so agents ask users which strategy view they prefer after installation.
- A-share history and quote chains now expose optional AkShare fallback behavior without requiring AkShare in the default install.
- Bumped the README badge and HTML footer version to `v0.4.0`.

### Fixed
- Corrected EastMoney A-share change-percent field parsing and sector benchmark turnover/change mapping.
- Prevented Tencent quote parsing from misclassifying unsupported US tickers in auto-provider mode.

## v0.3.3 - 2026-06-03

Cloud screenshot fallback guidance release. Agent installations now document the reliable Playwright/CDP paths for long report screenshots on Ubuntu cloud hosts.

### Changed
- Documented `scripts/screenshot_report.py --engine cdp --timeout 60` as the recommended long screenshot fallback for cloud agents.
- Added Hermes/Linux setup guidance for Playwright screenshots and non-snap Chrome CDP screenshots.
- Warned agents away from snap Chromium's raw `--screenshot` path, which can capture a tall viewport instead of the full StockSight report.
- Bumped the README badge and HTML footer version to `v0.3.3`.

## v0.3.2 - 2026-05-28

Strategy-action release. Reports now distinguish risk detection from strategy posture, so medium technical moves no longer collapse into generic watch/hold copy.

### Added
- Rule-based strategy action layer with `趋势持有`, `突破确认`, `高位降温`, `回撤观察`, `低位修复`, `平稳跟踪`, and `风险规避`.
- Strategy explanations in Markdown and HTML reports, including trigger basis, confirmation conditions, invalidation conditions, and risk notes.

### Changed
- Detailed report operation advice now uses the strategy action layer instead of mapping `max_level >= 2` directly to `持有/观望`.
- Hard-risk news only upgrades strategy risk when it is stock-relevant, date-parsable, and recent enough to affect the current report.
- Bumped the README badge and HTML footer version to `v0.3.2`.

### Fixed
- Long screenshot capture now disables report animations before capture, preventing blank-looking gaps in exported PNGs.
- Historical 2015/2016 risk notices can remain visible as context without overriding 2026 real-time technical judgment.

## v0.3.1 - 2026-05-22

README presentation refresh release.

### Changed
- Replaced the previous split README screenshots with one full AAPL report screenshot that shows the report flow end to end.
- Bumped the README badge and HTML footer version to `v0.3.1`.

## v0.3.0 - 2026-05-21

Source-chain reproducibility and risk-model clarity release. Reports now separate unusual-move strength from downside risk and can prioritize A-share announcements, filings, and other hard information ahead of generic news.

### Added
- **Data source chain** in report context: live quote source, historical K-line source, fallback status, historical bar count, technical cutoff date, and snapshot state.
- **Hard-information-first news aggregation**: A-share query templates for announcements, filings, earnings previews, risk notices, major events, and shareholder changes.
- **Source/category labeling for context items**: exchange, CnInfo, Eastmoney announcement, company site, investor relations, financial media, and generic search results are ranked and labeled.
- **Company information sections** in Markdown and HTML reports, split into "公司公告与硬信息" and "市场资讯与舆情".
- **Dual risk scoring**: `anomaly_score` explains how unusual the move is, while `risk_score` estimates downside/event risk.
- **Anomaly strength breakdown** in Markdown and HTML: price movement, trading activity, turnover, technical confluence, and event-driven contribution.
- **Snapshot source notes** via `ReportData.source_notes`, preserved by `--save-snapshot` and `--from-snapshot`.

### Changed
- HTML risk gauge now centers on downside risk and explains anomaly strength separately.
- Header metrics now show both "异动强度" and "下行风险".
- A-share limit-up and strong upward moves remain high anomaly events but no longer automatically imply high downside risk.
- Optional news is now treated as company context; missing API keys still skip the section without blocking core reports.
- HTML footer version now follows the project release version.

### Fixed
- Snapshot replay remains compatible with older snapshots that do not contain source-chain notes.
- Local `snapshots/` are ignored to keep generated replay artifacts out of commits.

## v0.2.0 - 2026-05-20

Technical indicator convergence release. MACD/RSI now produce trend summaries and divergence detection.

### Added
- **Trend summary analysis**: MACD alignment (bullish/bearish/turning/neutral), histogram trend (expanding/contracting/flat), and RSI trend state (overbought pullback, oversold bounce, sustained directional moves).
- **Price-MACD divergence detection**: Bearish divergence (price higher high, DIF lower high) and bullish divergence (price lower low, DIF higher low) across the last 30-bar window.
- **TrendSummary dataclass** in core/types.py, integrated into TechnicalAnalysis.
- **Hero judgment banner** in HTML reports: color-coded status badge (偏强/过热/转弱/观察), main risk summary, trend indicators, and next-action guidance. Final judgment now incorporates trend summary data.
- **Data credibility panel** in detailed reports: per-field trust labels (可确认/推导/不可用/历史计算) with confidence summary.
- Four-status final judgment labels in `final_judgment()`: 偏强, 过热, 转弱, 观察.
- Multi-scenario test reports for the hero judgment banner (outputs/judgment-*.html).
- Trend summary CSS cards and responsive hero banner styles.
- Installation and agent usage documentation: AGENTS.md, RELEASE.md, updated README.

### Changed
- `analyze_technical_indicators()` now populates `TechnicalAnalysis.trend` with a `TrendSummary`.
- Divergence signals are auto-injected into the technical signal list for risk display.
- _render_technical_section() in detailed formatter now includes a trend summary table.
- _technical_indicators_html() in HTML charts now includes trend summary cards.
- `final_judgment()` enhanced to use trend data for better status classification.

### Fixed
- Report signal duplication when technical risk signals were added both to data.signals and by _combined_signals().


## v0.1.2 - 2026-05-19

Engineering hygiene and test coverage release.

- Added `.gitattributes` and `# -*- coding: utf-8 -*-` headers to all Python source files to fix garbled Chinese text on Windows GBK systems.
- Renamed Chinese identifier names in `detector.py` (`DetectorThresholds` fields, `_level_from_threshold` params) to English with full backward compat via legacy map.
- Added GitHub Actions CI workflow (Python 3.9/3.10/3.11/3.12 matrix, runs on push/PR).
- Relaxed `urllib3<2` pin to Python 3.9 only via environment marker.
- Added 31 new tests covering Tencent (A-share/HK parsing, fetch mock), Sina (A/HK/US field extraction), EastMoney (secid encoding, single-stock parsing), and news module (aggregator dedup, Tavily/SerpAPI response parsing).
- Test suite grows from 28 to 60 tests.

## v0.1.1 - 2026-05-19

Public GitHub-ready release.

- Added reproducible report snapshots with `--save-snapshot` and `--from-snapshot`.
- Added `examples/snapshot-sample.json` for offline rendering demos.
- Added MIT `LICENSE`, `CONTRIBUTING.md`, issue templates, and README badges.
- Removed the built-in PDF exporter because system font differences made Chinese PDF output unreliable.
- Pinned `urllib3<2` for Python 3.9 compatibility.

## v0.1.0 - 2026-05-18

First public skill release.

- Added the standard `SKILL.md` entrypoint for agent discovery.
- Added A-share, Hong Kong, and US quote provider support.
- Added Markdown and self-contained HTML report rendering.
- Added risk gauge, signal radar, signal composition, risk distribution, and data-quality panels.
- Added optional Tavily and SerpAPI news aggregation.

# RELEASE.md - StockSight Release Process

This checklist keeps StockSight releases repeatable.

## Versioning

StockSight follows [Semantic Versioning](https://semver.org/):

- **MAJOR** `x.0.0`: breaking changes to public APIs, snapshot format, or report structure.
- **MINOR** `0.x.0`: backward-compatible features such as indicators, providers, or report sections.
- **PATCH** `0.0.x`: bug fixes, tests, and documentation updates.

Current version: **0.5.0**

## Release Checklist

### 1. Verify Tests

```bash
py -3 -m unittest discover -s tests -v
```

Also run:

```bash
py -3 -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8-sig'), filename=str(p)) for p in pathlib.Path('.').rglob('*.py') if '.git' not in p.parts]; print('AST ok')"
git diff --check
```

### 2. Update Version

- Update the README version badge.
- Add the new top entry in `CHANGELOG.md`.
- Keep `SKILL.md` frontmatter limited to `name` and `description`.

### 3. Update Changelog

Use this format:

```markdown
## vX.Y.Z - YYYY-MM-DD

One-line summary of the release theme.

### Added
- New feature

### Changed
- Changed behavior

### Fixed
- Bug fix
```

### 4. Check Public API Stability

| Interface | Expected |
|:---|:---|
| `DataSourceFactory.fetch` | Accepts stock codes, returns `FetchResult` |
| `detect(stocks)` | Accepts `StockData` list, returns `RiskSignal` list |
| `analyze_technical_indicators(history)` | Accepts `StockHistory`, returns `TechnicalAnalysis` |
| `render_standard_report(data)` | Returns Markdown string |
| `render_detailed_report(data)` | Returns Markdown string |
| `render_html_report(data)` | Returns self-contained HTML string |
| `validate_report(text, data)` | Returns validation result |
| `scripts/report.py` | Preserves CLI flags and snapshot behavior |

### 5. Snapshot Compatibility

Current snapshot schema version: **1**

If the snapshot format changes:

1. Bump `SNAPSHOT_SCHEMA_VERSION` in `scripts/report.py`.
2. Add migration logic for old snapshots.
3. Document the migration in `CHANGELOG.md`.

### 6. Documentation Sync

Check:

- `AGENTS.md`
- `README.md`
- `SKILL.md`
- `references/visual-specs.md`
- `references/examples.md`
- `CHANGELOG.md`

### 7. Screenshots

For visual releases, generate a fresh HTML report and update README screenshots when the UI changed materially.

Suggested flow:

```bash
py -3 scripts/render_examples.py
py -3 scripts/screenshot_report.py reports/examples/us-detailed.html --out docs/images/stocksight-report-full.png
```

Review the rendered files in `reports/examples/`, then capture a long screenshot into `docs/images/` when the README screenshots need to change.

### 8. Commit, Tag, Push

```bash
git add README.md CHANGELOG.md AGENTS.md RELEASE.md
git commit -m "chore: bump to vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

### 9. GitHub Release

Create a GitHub Release:

- Tag: `vX.Y.Z`
- Title: `vX.Y.Z - Release Theme`
- Description: copy the matching `CHANGELOG.md` section.

## Post-Release

- Verify the release page is visible.
- Confirm the README badge points to the new tag.
- Test a fresh clone from the tag:

```bash
git clone --branch vX.Y.Z https://github.com/GearVoid/StockSight-Skill.git /tmp/stocksight-test
cd /tmp/stocksight-test
pip install -r requirements.txt
python scripts/report.py --from-snapshot examples/a-share-detailed.json --html --out /tmp/test.html
```

## Release History

| Version | Date | Theme |
|:---|:---|:---|
| v0.5.0 | 2026-06-09 | Mainline radar and separated mainline/swing scorecards |
| v0.4.0 | 2026-06-03 | Strategy profiles, free announcements, optional AkShare fallback |
| v0.3.3 | 2026-06-03 | Cloud screenshot fallback guidance |
| v0.3.2 | 2026-05-28 | Strategy actions, screenshot stability, stale hard-risk news filtering |
| v0.3.1 | 2026-05-22 | README full-report screenshot refresh |
| v0.3.0 | 2026-05-21 | Source-chain reproducibility, hard information, dual risk scoring |
| v0.2.0 | 2026-05-20 | Technical indicator convergence |
| v0.1.2 | 2026-05-19 | Engineering hygiene, CI, test coverage |
| v0.1.1 | 2026-05-19 | Public release: snapshots, license, MIT |
| v0.1.0 | 2026-05-18 | First skill release |

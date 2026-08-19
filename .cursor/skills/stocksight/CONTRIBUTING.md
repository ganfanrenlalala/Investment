# Contributing

Thanks for helping improve StockSight-Skill.

## Setup

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

If your local Python environment does not have `requests`, install the requirements first.

## Development Notes

- Keep `SKILL.md` short and procedural. Put long visual rules or examples in `references/`.
- Keep public API names stable unless there is a migration path.
- Prefer adding tests for formatter, provider parsing, data quality, and snapshot behavior.
- Do not commit `.sightconfig.json`, API keys, generated reports, local outputs, or temporary dependency folders.
- For reproducibility, prefer snapshot fixtures over live network calls in tests.

## Provider Changes

When adding or changing a quote provider:

- Normalize output into `StockData`.
- Mark unavailable metrics as `—` at render time instead of fabricating values.
- Preserve raw provider payloads only in `StockData.raw` for debugging.
- Add parser-level tests that do not require live network access.

## Reporting Issues

Please include:

- Stock code or ticker.
- Provider used.
- Whether the problem came from Markdown, HTML, or snapshot replay.
- A small sanitized snapshot when possible.

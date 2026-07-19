# Stock Universe Maintenance Rollback

This change is isolated to the silent stock-universe/data-quality layer.

Rollback steps:

1. Revert the pull request commit that adds `stocks/universe_quality.py`, `tests/test_universe_quality.py`, `.github/workflows/stock-universe-maintenance.yml`, and `docs/data-quality/2026-07-19T081301Z.json`.
2. Delete any generated `data/data_quality_report.json` artifact from a failed manual run if it is misleading.
3. Leave `config/stocks.yaml` and `stocks/scanner.py` unchanged; this change does not alter Buy/Sell/Short/Hold classification, risk/reward, targets, triggers, invalidations, or Telegram alert gates.

Telegram is intentionally disabled in the manual universe workflow, so rollback does not require Telegram cleanup.

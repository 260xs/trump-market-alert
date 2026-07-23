# Event Risk Maintenance Report - 2026-07-21

Run scope: catalyst calendar, market-regime state, and event-risk gates only. Telegram market alerts were not sent. Broad public-figure discovery, Buy/Sell strategy logic changes, long-term profitability analysis, and cron additions were not performed.

## Repository inspection

Verified on `main` at commit `291e135b8912ff4423f8f7bfd0392d631ac0c5df`:

- `.github/workflows/stable-monitor.yml` exists and is manual `workflow_dispatch` only.
- `.github/workflows/hourly-stock-scan.yml` exists and is manual `workflow_dispatch` only.
- `.github/workflows/stock-candidate-refresh.yml` exists and is manual `workflow_dispatch` only.
- `.github/workflows/telegram-test.yml` exists and is manual `workflow_dispatch` only.
- Existing stock strategy logic lives in `stocks/scanner.py`.
- Existing SQLite stock tables live in `stocks/research_db.py`.
- No existing event calendar, source-health, market-regime snapshot, or event-risk decision tables were found by code search.

## Changes staged in this branch

Added `stocks/event_risk.py` with SQLite-backed records for:

- official event source metadata and source-health checks
- UTC event calendar rows with exact timestamps or verified windows
- historical event revisions for created, changed-time, status-changed, cancelled, and updated events
- market-regime snapshots with state, confidence, data quality, inputs, and timestamp
- event-risk gate decisions with allowed/blocked state and exact reason

Added `tests/test_event_risk.py` covering:

- daylight-saving UTC conversion
- market holidays
- duplicate events
- changed times
- cancelled events
- uncertain timestamps
- earnings near a signal
- macro releases near a signal
- competing-catalyst rejection
- stale regime data
- one-source failure isolation

## Event coverage

No live official-source refresh was completed in this environment. Network access to direct GitHub/API endpoints was blocked, and the available GitHub connector did not expose Actions run listing or `workflow_dispatch` execution tools.

Events added: 0 live events.
Events updated: 0 live events.
Events cancelled: 0 live events.
Unresolved events: not refreshed in this run.

## Source status

Sources designed for the new schema include official government, central-bank, exchange, regulator, and company-investor pages. Source rows capture official URL, official status, timezone, update frequency, parser/API compatibility, cursor behavior, duplicate policy, last checked time, last success time, and last error.

Sources actually checked live in this run: none, due connector/runtime limitations described above.

## Market regime

Current live market regime was not calculated in this run. The new schema supports `Bullish`, `Bearish`, `Mixed`, and `Uncertain` snapshots with inputs and data-quality status. Stale or conflicting inputs are expected to store `Uncertain` and block event-gated setups.

## Blocked-signal behavior

The new gate returns these block reasons when applicable:

- `major_event_pending`
- `event_time_uncertain`
- `earnings_risk`
- `corporate_action_pending`
- `competing_catalyst`
- `market_regime_uncertain`
- `event_data_stale`

Blocked-signal counts from live scanner: not available because the scanner hook could not be patched through the currently exposed connector tools.

## Validation

Local validation performed without Telegram:

- Direct execution of all `tests/test_event_risk.py` test functions: passed.

Not performed:

- `python -m pytest -q`: blocked because `pytest` is not installed and package installation is blocked by network policy.
- GitHub Actions `workflow_dispatch`: blocked because the exposed connector tools do not include Actions run listing or dispatch.
- Telegram test: intentionally not run.

## Rollback

Rollback is low-risk because this branch only adds new files. Close the PR or revert the commits adding:

- `stocks/event_risk.py`
- `tests/test_event_risk.py`
- `docs/event-risk-report-2026-07-21.md`

## Remaining required action

Patch `stocks/scanner.py` to call `apply_event_risk_gate` after the existing actionable/risk/reward/dedupe checks and before Telegram send, then enable it through `config/stocks.yaml`. The scanner should record the gate decision and skip Telegram delivery when `allowed` is false.

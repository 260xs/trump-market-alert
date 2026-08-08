# Event Risk Maintenance Report - 2026-07-23

Run scope: catalyst calendar, market-regime state, event-risk gates, and supporting workflow/repository inspection only. Telegram market alerts were not sent. Telegram tests were not run. Broad public-figure discovery, Buy/Sell strategy changes, long-term profitability analysis, paid data-provider additions, broad permissions, cron additions, workflow disabling, and forced merges were not performed.

## Repository and PR state

Verified through the GitHub connector on 2026-07-23:

- Repository: `260xs/trump-market-alert`.
- Default branch: `main`.
- Current inspected `main` commit: `291e135b8912ff4423f8f7bfd0392d631ac0c5df` (`Remove routine health cron Telegram ping`).
- Existing draft PR: #25, `maintenance/event-risk-gates-20260721`, head `08ed07b1a53819a68cf22ce893f2b7787dd9171e` before this report update.
- PR #25 adds the SQLite event-risk foundation but does not yet hook `stocks.scanner.hourly_scan` into the gate before Telegram delivery.

## Workflows checked

These workflow files exist on `main` and are manual `workflow_dispatch` only, with no cron found in the fetched workflow definitions:

- `.github/workflows/stable-monitor.yml`
- `.github/workflows/hourly-stock-scan.yml`
- `.github/workflows/stock-candidate-refresh.yml`
- `.github/workflows/telegram-test.yml`

`hourly-stock-scan.yml` uses `actions/checkout@v6`, `actions/setup-python@v6`, `actions/cache/restore@v5`, `actions/cache/save@v5`, and `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`.

Actions queued/running/conclusion status was not fully verifiable from this runtime because the exposed connector tools do not include Actions run listing, logs, artifacts, caches, or `workflow_dispatch`, `gh` is not installed, and direct clone/API access returned HTTP 403. Because same-job queue/running state could not be proved, no workflow was dispatched.

## Event-risk implementation inspected

PR #25 adds `stocks/event_risk.py` with SQLite-backed tables for:

- `event_sources`
- `event_calendar`
- `event_revisions`
- `market_regime_snapshots`
- `event_risk_decisions`

The event rows include title, event type, UTC exact time or verified window, source URL, source confidence, affected country, market, sector, company, ticker/asset, expected impact, confirmed-time flag, last verification time, collection cursor, status, and raw payload JSON. Event revisions preserve changed times, status changes, cancellations, and other updates.

The gate currently supports these block reasons:

- `major_event_pending`
- `event_time_uncertain`
- `earnings_risk`
- `corporate_action_pending`
- `competing_catalyst`
- `market_regime_uncertain`
- `event_data_stale`

## Confirmed defect / remaining gap

Confirmed on `main`: `stocks/scanner.py` sends actionable stock Telegram alerts after actionable, confidence, risk/reward, risk percentage, and dedupe checks, but it does not call `apply_event_risk_gate` before Telegram delivery.

Confirmed on PR #25: `stocks/event_risk.py` exposes `apply_event_risk_gate`, but the branch report itself states the scanner hook could not be patched in that prior run.

Impact: until the scanner is wired to the event-risk gate and configured, the live stock scanner can still send an otherwise valid High-confidence setup without blocking for stale event data, uncertain event timing, earnings risk, major macro risk, corporate actions, or uncertain market regime.

## Source and event refresh status

No live official-source refresh was completed in this run. Direct outbound official-source checks and direct GitHub/API clone/download were blocked by the runtime network policy.

Events added: 0 live events.
Events updated: 0 live events.
Events cancelled: 0 live events.
Unresolved events: not refreshed in this runtime.

Official source classes that remain required for the eventual refresh are government statistical calendars, central-bank calendars/minutes/speeches, Treasury calendars, exchange market-holiday pages, regulator/company-investor pages, and official corporate-action/earnings materials. PR #25 has storage fields for source status, official URL, timezone, update frequency, parser/API compatibility, cursor behavior, duplicate policy, last check, last success, and last error.

## Market regime

Current live market regime was not calculated in this run because reliable fresh market inputs and Actions/cache artifacts were not accessible from the runtime.

Stored live regime: unavailable.
Regime timestamp: unavailable.
Data-quality status: unavailable.
Expected scanner behavior once wired: stale, missing, conflicting, or `Uncertain` regime snapshots must block with `market_regime_uncertain`.

## Blocked-signal counts

Live scanner blocked-signal counts: unavailable because the gate is not wired into `stocks/scanner.py` on `main`, and no dry-run stock scan was dispatched.

Expected behavior after the minimal scanner hook is added:

- stale or unavailable calendar source data blocks with `event_data_stale`
- uncertain event time blocks with `event_time_uncertain`
- ticker-specific upcoming earnings blocks with `earnings_risk`
- broad high-impact macro or market holiday events block with `major_event_pending`
- pending dividends, splits, shareholder votes, lockups, merger deadlines, and corporate actions block with `corporate_action_pending`
- missing/stale/conflicting regime blocks with `market_regime_uncertain`

## Validation

Performed:

- Fetched and inspected `stocks/scanner.py`, `config/stocks.yaml`, `stocks/research_db.py`, `tests/test_stock_scanner.py`, PR #25 `stocks/event_risk.py`, PR #25 `tests/test_event_risk.py`, and the operational workflows listed above.
- Confirmed workflows fetched here are `workflow_dispatch` only; no cron was added.
- Confirmed Telegram was not sent or tested from this run.

Not performed:

- Local pytest: blocked because direct clone/download is blocked, so the complete repository could not be checked out.
- GitHub Actions dispatch/run monitoring: blocked because Actions run-list/dispatch/log APIs are not exposed in this runtime.
- Live official-source refresh: blocked by runtime network limits and missing dispatch/log/artifact access.

## Proposed smallest safe code patch, not applied in this run

Patch `stocks/scanner.py` on the existing PR branch to import `apply_event_risk_gate`, then call it after existing actionable/confidence/risk/dedupe checks and before `telegram.send_text`. Use a config flag such as `settings.enable_event_risk_gate` defaulting to false on `main` until a verified event calendar and fresh market-regime job are present. When enabled, write the decision to SQLite and skip Telegram when blocked.

Add config defaults in `config/stocks.yaml`:

- `enable_event_risk_gate: false`
- `event_risk_sqlite_path: data/stocks.sqlite3`
- `event_risk_lookahead_hours: 72`
- `event_risk_max_source_age_hours: 24`
- `event_risk_max_regime_age_hours: 6`

Add scanner regression coverage proving an actionable setup with stale event data records a gate decision and sends zero Telegram messages when the gate is enabled.

This code patch was not applied because clone/push and an existing-file update API were unavailable in this session. A risky full-file rewrite through a partial connector was intentionally avoided.

## Rollback

This report-only update can be rolled back by removing `docs/event-risk-report-2026-07-23.md` from PR #25. No runtime scanner behavior changes were made by this report.

## Required action

Provide an existing-file update path through the GitHub connector, enable `gh`/Actions access for this repo, or run the small scanner-hook patch in a normal checkout, then dispatch a Telegram-disabled dry run and review blocked-signal counts before merging.

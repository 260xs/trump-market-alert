# Data Quality Maintenance Report - 2026-07-17

Generated: 2026-07-17 08:24 UTC
Base commit: d86f7146084bb3198c4d01d99cc48a6685097a91
Scope: stock universe, market-data quality, provider/scanner reliability only
Telegram: disabled/not dispatched for this maintenance run

## Executive status

This run did not prove the stock universe is complete or healthy. The repository currently uses a curated YAML stock universe plus yfinance data access. It does not yet contain exchange-directory ingestion, independent provider metadata reconciliation, persisted universe membership tables, provider identifier tables, quarantine tables, corporate-action audit tables, or deterministic batch cursor tables for a broad active common stock/ADR/ETF universe.

No public-figure scan was run. No Telegram alert/test was sent. No Buy/Sell/Short/Hold strategy rules were changed. No profitability evaluation was performed.

## Workflow/run status

Verified from repository files on main:

- .github/workflows/hourly-stock-scan.yml exists and is workflow_dispatch-only.
- .github/workflows/stock-candidate-refresh.yml exists and is workflow_dispatch-only.
- .github/workflows/stable-monitor.yml exists and is workflow_dispatch-only.
- .github/workflows/telegram-test.yml exists and is workflow_dispatch-only.
- .github/workflows/system-health.yml exists and is workflow_dispatch-only.
- .github/workflows/workflow-watchdog.yml exists and is workflow_dispatch-only.

The container could not query GitHub Actions runs directly because outbound GitHub API/clone access returned 403, and the available GitHub connector in this session did not expose Actions run-list or workflow_dispatch tools. Therefore no workflow was dispatched, and no duplicate queued/running job could be conclusively verified from Actions run state in this run.

The connector returned no combined status checks for base commit d86f7146084bb3198c4d01d99cc48a6685097a91.

## Provider status

Verified providers in current stock code:

| Provider | Current use | Status | Evidence |
| --- | --- | --- | --- |
| yfinance | stocks.market_data.fetch_bars downloads OHLCV bars with auto_adjust=True | Present, free public data wrapper | stocks/market_data.py |
| Official exchange directories | Not implemented | Gap | No repository files found for exchange-directory ingestion |
| Independent metadata reconciliation provider | Not implemented | Gap | No repository files found for provider disagreement/quarantine handling |

Provider reliability checks performed in this run:

- Authentication: yfinance path has no configured authentication.
- Rate limits/legal limits: no repository-level provider-limit model found.
- Pagination: no broad-universe pagination/cursor implementation found.
- Retries: MARKET_DATA_RETRIES and retry sleep are implemented for yfinance downloads.
- Timeouts: yfinance call does not pass an explicit request timeout.
- Schema changes: dataframe column normalization handles tuple columns for OHLCV.
- Symbol formatting/exchange suffixes: no central symbol-formatting policy found.
- Caching: in-memory TTL cache exists in stocks/market_data.py; GitHub Actions caches data/ for SQLite.
- One-symbol failure isolation: hourly_scan and discover_candidates catch per-symbol failures and continue.

## Current universe coverage

Current configured stock universe:

- Source: config/stocks.yaml
- Count: 151 unique symbols
- Duplicates detected in YAML inspection: 0
- Type: curated static list, not official active exchange universe

Requested broad universe target:

- active common stocks
- ADRs
- ETFs
- exchange, currency, asset type, legal name, ticker, share class, listing status
- first/last seen time and provider identifiers
- exclusion/quarantine reasons for unsupported securities

Current repository coverage for that target: incomplete.

Machine-readable run counts:

```json
{
  "run_timestamp_utc": "2026-07-17T08:24:00Z",
  "base_commit": "d86f7146084bb3198c4d01d99cc48a6685097a91",
  "configured_yaml_universe_symbols": 151,
  "configured_yaml_duplicates": 0,
  "broad_exchange_universe_eligible": null,
  "processed_symbols": 0,
  "passed_symbols": 0,
  "quarantined_symbols": 0,
  "failed_symbols": 0,
  "remaining_symbols": null,
  "telegram_sent": false,
  "public_figure_scan_ran": false,
  "stock_scanner_workflow_dispatched": false,
  "candidate_refresh_workflow_dispatched": false,
  "coverage_complete": false,
  "coverage_blocker": "Actions run listing/dispatch unavailable in this session and repository lacks broad exchange-universe ingestion/quarantine tables."
}
```

## SQLite/schema status

Verified stock SQLite tables in stocks/research_db.py:

- stock_alerts
- top_candidates
- stock_scans
- active_stock_setups

Missing for requested universe/data-quality maintenance:

- symbol_universe or equivalent listing master
- provider_symbols/provider_identifiers
- symbol_status_history
- symbol_exclusions
- symbol_quarantine
- provider_disagreements
- market_data_quality_runs
- market_data_quality_results
- corporate_actions
- batch_cursors
- failed_symbols
- data_version or per-alert data/strategy version table for old predictions

## Data-quality validation coverage

Existing scanner behavior verified by code inspection:

- hourly bars require at least 60 bars before setup analysis can be actionable.
- daily context requires at least 50 bars.
- per-symbol fetch/analyze exceptions are logged and do not stop the whole hourly scan.
- candidate discovery failures are logged per symbol and do not stop the whole discovery job.
- Telegram is skipped when TelegramClient is not configured.

Missing checks for broad reliable universe/data quality:

- fresh timestamp and exchange timezone validation
- trading-calendar validation
- adjusted and unadjusted price comparison
- split/dividend adjustment verification
- duplicate timestamp detection
- missing candle detection
- partial/stale/revised data detection
- impossible OHLC values beyond basic indicator availability
- zero/negative price quarantine
- volume quality and average dollar volume gates for universe eligibility
- spread availability checks
- independent provider disagreement quarantine
- corporate-action event capture for ticker/name changes, mergers, spin-offs, delistings and relistings

## Corporate actions

Current code fetches yfinance bars with auto_adjust=True. No repository evidence was found that the scanner stores raw unadjusted prices, split factors, dividend events, ticker/name-change history, merger/spin-off data, delisting status, or the provider/data version used for each old alert.

Risk: later price adjustments or reused tickers could make old scan payloads difficult to reproduce or audit. This report does not change historical predictions.

## Confirmed defects/gaps

1. Broad universe ingestion is not implemented. The current universe is a curated 151-symbol YAML list.
2. Provider metadata reconciliation and quarantine handling are not implemented.
3. Data-quality SQLite tables and deterministic batch cursor tables are not implemented.
4. Corporate-action audit/storage is not implemented.
5. Existing workflow regression tests still reference old cron schedules even though main workflows are now manual-only. This is a validation defect, but existing-file update tooling was not exposed in this session, so this report does not patch those tests.
6. Recent Actions run state could not be verified from this environment, and no workflow_dispatch was performed.

## Exclusions/quarantine summary

No broad universe build was run, so no symbol-level exclusions or quarantines were produced in this report. Current repository logic does not persist machine-readable exclusion/quarantine reasons for unsupported security types.

## Rollback

Remove this file:

- docs/data_quality_report_2026-07-17.md

No scanner code, strategy rules, workflows, secrets, Telegram settings, or provider dependencies were changed by this report.

## Recommended next implementation step

Add a manual-only, Telegram-disabled universe audit command that builds and persists exchange/provider symbol metadata and quarantine reasons without feeding symbols into alerts until quality checks pass. Keep it unmerged for review if it introduces new provider dependencies or broad symbol rules.

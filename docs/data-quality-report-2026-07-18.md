# Data Quality Report - 2026-07-18T08:13Z

Scope: stock universe, market-data quality, and scanner reliability only. Telegram disabled; no public-figure scan; no Buy/Sell strategy rule changes.

## Repository State

- Inspected repository: 260xs/trump-market-alert, default branch main at d86f7146084bb3198c4d01d99cc48a6685097a91.
- Current stock provider adapter: stocks/market_data.py using yfinance download with retries and in-memory TTL cache.
- Current scanner universe source: config/stocks.yaml YAML list plus priority_stocks. No official exchange-directory ingestion, provider symbol-file ingestion, persisted batch cursor, failed-symbol log, quarantine table, symbol-history table, or corporate-action table was found in the inspected stock code.
- Current SQLite stock tables: stock_alerts, top_candidates, stock_scans, active_stock_setups.

## GitHub Actions Status Checked

- Public Actions page showed latest visible Hourly Stock Research Scanner run #202 triggered by schedule on 2026-07-16 16:38 UTC with Status Success and total duration 45s.
- Public Actions page showed latest visible Stock Candidate Refresh run #21 triggered by schedule on 2026-07-16 08:41 UTC with Status Success and total duration 52s.
- No duplicate workflow_dispatch run was started from this automation.

## Coverage

- Providers checked: yfinance adapter code only. Live provider API was not called from this environment.
- Exchanges checked: none through official exchange directories; current repo does not contain exchange directory ingestion.
- Eligible symbols: not fully computed; config/stocks.yaml contains the current configured YAML universe.
- Processed symbols: 0 in this automation.
- Passed symbols: 0 in this automation.
- Quarantined symbols: 0 in this automation; no quarantine table exists yet.
- Failed symbols: 0 in this automation; no failed-symbol log exists yet.
- Remaining symbols: unknown until a proper persisted broad-universe job exists and completes.

## Confirmed Defect

- The market-data adapter accepted malformed rows from provider dataframes, including naive timestamps, duplicate timestamps, nonpositive prices, impossible OHLC values, and negative volume. These rows could flow into indicator calculations.

## Repair

- Add strict row validation in stocks/market_data.py before bars are cached or returned.
- Add regression tests for bad timezone, duplicate timestamps, invalid prices/volume, impossible OHLC rows, and deterministic UTC timestamp ordering.

## Known Gaps

- Broad legal universe construction from official exchange directories or reputable symbol files is not implemented.
- Symbol history for delistings, ticker changes, share classes, and relistings is not implemented.
- Independent provider metadata comparison and machine-readable quarantine reasons are not implemented.
- Corporate-action audit tables and adjusted/unadjusted validation are not implemented.
- Persisted deterministic batch cursors are not implemented.

## Rollback

- Revert the patch touching stocks/market_data.py, tests/test_market_data_quality.py, and this report if the stricter validation unexpectedly rejects valid provider rows.

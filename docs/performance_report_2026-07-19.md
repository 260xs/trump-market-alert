# Paper Performance Evaluation Report - 2026-07-19

## Run metadata

- Report version: `paper-performance-audit-v2`
- Evaluation timestamp: `2026-07-18T22:30:01Z` (`2026-07-19 02:30:01 Asia/Dubai`)
- Repository inspected: `260xs/trump-market-alert`
- Base branch inspected: `main`
- Base commit observed: `d86f7146084bb3198c4d01d99cc48a6685097a91` (`Make operational workflows manual-only`)
- Scope: audit-only. No live market scans, stock scans, public-figure scans, Telegram market alerts, Telegram tests, production signal-rule changes, deployments, or strategy changes were performed.
- Secrets policy: no secrets were read, requested, printed, committed, or logged.

## Executive conclusion

Insufficient out-of-sample evidence to claim profitability.

No matured Buy, Sell, or verified public-figure alert could be evaluated in this run because the timestamped SQLite alert history, saved market data, strategy-version metadata, Actions caches, logs, and artifacts were not accessible through the available tools. Missing records were excluded rather than reconstructed or guessed.

## Workflow dispatch and run verification

The requested performance-evaluation workflow could not be dispatched or monitored by this automation run.

| Item | Verified evidence | Result |
| --- | --- | --- |
| Performance-evaluation workflow on `main` | Direct fetch of `.github/workflows/performance-evaluation.yml` returned GitHub 404. Public Actions workflow list did not show a performance evaluator. | Not present on `main`; no run link or conclusion exists for this workflow. |
| Equivalent merged evaluator | `manual-run-all.yml`, `stable-monitor.yml`, `hourly-stock-scan.yml`, and `stock-candidate-refresh.yml` exist on `main`, but they are scanner workflows, not paper-performance evaluators. | No equivalent safe evaluator found on `main`. |
| Same audit queued/running | Public Actions page is read-only and exposes recent summaries, but not authenticated queued/running state, artifacts, logs, or workflow dispatch controls. | Could not prove a same audit was queued or running. No duplicate was started. |
| Actions dispatch/list capability | `gh` is not installed; direct `git`/GitHub network access from the container failed with `CONNECT tunnel failed, response 403`; exposed GitHub connector does not provide Actions run-list or workflow-dispatch tools. | Blocked. |

Recent public Actions summaries visible during this run:

| Workflow | Public run | Trigger | Visible conclusion/status | Duration | Link |
| --- | ---: | --- | --- | --- | --- |
| Market-Moving Public Figure Alert | #251 | schedule | Listed as completed with duration; public index presents it as a successful recent run. | 1m 29s | https://github.com/260xs/trump-market-alert/actions/runs/29517005381 |
| Hourly Stock Research Scanner | #202 | schedule | Listed as completed with duration; public index presents it as a successful recent run. | 45s | https://github.com/260xs/trump-market-alert/actions/runs/29516399012 |
| GitHub Actions Watchdog | #14 | schedule | Listed as completed with duration. | 8s | https://github.com/260xs/trump-market-alert/actions/runs/29515779108 |
| Telegram Test | #33 | schedule | Listed as completed with duration. No Telegram test was dispatched by this audit. | 10s | https://github.com/260xs/trump-market-alert/actions/runs/29509943393 |

Important limitation: public Actions HTML showed older scheduled runs from `main`, while direct workflow files fetched from current `main` contain `workflow_dispatch` and no cron for the inspected scanner workflows. This report records the inconsistency and does not infer current queued/running state from the public page.

## Repository and data inventory

| Evidence source | Status | Audit impact |
| --- | --- | --- |
| Local checkout | Unavailable. Direct `git ls-remote`/clone to GitHub failed with proxy 403; only GitHub connector file reads were available. | Could not run local evaluator, inspect uncommitted SQLite files, or execute tests. |
| Public-figure SQLite schema | `database/db.py` defines `raw_statements`, `detected_entities`, `alerts`, `dedupe_keys`, `source_state`, and `scheduler_runs`. | Schema stores alert/source records, but actual production database rows were unavailable. |
| Stock SQLite schema | `stocks/research_db.py` defines `stock_alerts`, `top_candidates`, `stock_scans`, and `active_stock_setups`. | Schema stores alerts/scans/setups, but actual production database rows were unavailable. |
| Saved market data | Not committed; expected to live under Actions cache/artifact paths such as `data/stocks.sqlite3` and scanner caches. | Could not compute trigger activation, forward outcomes, MFE/MAE, target/invalidation sequence, benchmark/sector adjustment, or data-quality flags. |
| Strategy versions | No merged per-alert strategy-version performance table found from accessible files. | Historical rows cannot be attributed reliably without persisted metadata. |
| Prior audit report | PR #7 adds `docs/performance_report_2026-07-18.md`, but it is draft/unmerged and documents the same blocked evidence path. | Useful context only; not production state on `main`. |

## Record accounting

| Category | Count | Status / exclusion reason |
| --- | ---: | --- |
| Alert records examined from production SQLite | 0 | SQLite databases/caches/artifacts inaccessible. |
| Matured High-confidence Buy alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Matured High-confidence Sell alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Matured verified public-figure Good/Bad alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Pending alerts | Unknown | Requires original alert timestamps and current/historical market data. |
| Excluded records | Unknown | Raw records inaccessible; record ids cannot be enumerated. |

Global exclusion reason for unavailable rows: `Source SQLite/cache/artifact unavailable to this automation run; excluded rather than reconstructed or guessed.`

## Required per-alert fields

No per-alert fields were computed in this run. Each field below remains blocked by missing timestamped rows and saved market data:

| Required field | Status | Reason |
| --- | --- | --- |
| Trigger activated and trigger time | Not computed | Requires original alert rows and forward candles. |
| Price at alert and trigger | Not computed | Requires immutable alert timestamp, trigger level, and market-data snapshot. |
| 1-hour, 1-day, 5-day, 20-day outcomes | Not computed | Requires mature post-alert/post-trigger market data. |
| Maximum favorable and adverse movement | Not computed | Requires intraperiod OHLC data. |
| Target or invalidation first | Not computed | Requires original target/invalidation and forward candles. |
| Market- and sector-adjusted return | Not computed | Requires matching benchmark/sector series. |
| Spread, slippage, latency, and costs | Not computed | Requires timestamped alert delivery and execution-cost assumptions. |
| Market regime | Not computed | Requires persisted regime snapshot or reproducible classifier. |
| Strategy version | Not computed | Requires per-alert strategy metadata or reliable commit mapping. |
| Data-quality status | Not computed | Requires raw provider snapshots, fetch time, stale/revised flags, and cache lineage. |

## Formulas and assumptions for the evaluator

These formulas are recorded for reproducibility and must be applied only to timestamped out-of-sample records:

- Buy trigger activation: first post-alert market timestamp where price reaches or crosses the entry trigger.
- Buy paper return: `(measurement_or_exit_price - trigger_price) / trigger_price - estimated_costs_pct`, measured only after trigger activation.
- Sell downside avoidance: `(price_at_alert_or_trigger - later_price) / price_at_alert_or_trigger`, interpreted as avoided downside, not a short trade.
- Sell exit P&L: computed only when the Sell closes an existing tracked paper Buy position; otherwise no trade P&L is recorded.
- Public-figure Good accuracy: positive when post-alert abnormal return is greater than zero after latency/cost assumptions.
- Public-figure Bad accuracy: positive when post-alert abnormal return is less than zero after latency/cost assumptions.
- Abnormal return: asset return minus benchmark or sector return over the same timestamped horizon.
- Net expectancy after costs: `(success_probability x average_net_gain) - (failure_probability x average_net_loss) - realistic_costs`.
- Profit factor: gross gains divided by gross losses after costs when costed returns are available.
- Maximum drawdown: largest peak-to-trough decline in the chronological paper-equity curve after costs.
- Confidence interval/bootstrap: apply only when sample size is large enough for resampling to be meaningful; otherwise state insufficient sample.

Cost assumptions were not applied numerically because no trades/outcomes were measurable. A future evaluator should store the exact spread, slippage, latency, commission/fee, and data-source assumptions used for each run.

## Results by required segment

All metrics below are unavailable rather than zero because no timestamped out-of-sample observations were accessible.

| Segment | Sample size | Trigger rate | Directional precision | Win rate | Average gain | Average loss | Payoff ratio | Profit factor | Net expectancy after costs | Max drawdown | Benchmark-adjusted performance | False-positive rate | Confidence calibration |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Buy alerts | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Sell downside-avoidance alerts | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Verified public-figure alerts | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| By strategy version | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| By ticker | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| By source/public figure | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| By sector | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| By market regime | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## Strongest and weakest groups

No strongest or weakest ticker, source, public figure, sector, strategy version, or market-regime group can be identified from evidence in this run. Any ranking would require original alert rows and forward outcomes.

## Largest evidence-based weakness

Confirmed largest weakness: the project does not have a merged, dispatchable, reproducible performance-evaluation workflow on `main`, and the available automation environment cannot access the historical SQLite/cache/artifact evidence needed to evaluate profitability or usefulness.

| Problem | Estimated effect | Frequency | Confidence | Evidence |
| --- | --- | --- | --- | --- |
| Missing merged paper-performance evaluator | Blocks all cost-adjusted profitability/usefulness claims. | Systemic | High | `.github/workflows/performance-evaluation.yml` is absent on `main`; public workflow list does not show a performance evaluator. |
| Inaccessible SQLite/caches/artifacts | Blocks record-level outcome calculation, exclusions, and reproducibility. | Systemic for this audit path | High | Workflows restore/save `data` through Actions cache; no cache/artifact/log access is exposed to this run. |
| No per-alert strategy/regime/performance table on `main` | Prevents reliable slicing by strategy version/regime and trend tracking. | Systemic | Medium-High | Accessible schemas contain alerts/scans/setups, but no merged outcome/evaluation table was found. |
| Actions run-list/dispatch unavailable | Prevents duplicate-run protection and real workflow conclusion verification. | This automation environment | High | No `gh`, direct GitHub network 403, connector lacks Actions dispatch/list. |
| Workflow/documentation state mismatch | Can confuse audit scheduling and run attribution. | Current visible state | Medium | Public Actions shows recent scheduled runs from older workflow versions; fetched current `main` workflows are manual-only. |

Hypotheses not confirmed because record-level data was unavailable:

- Late detection or source latency reduced expectancy.
- Wide spreads, slippage, or low liquidity erased small expected moves.
- Trigger placement was overextended or invalidations were too wide.
- Market-regime or sector confirmation was weak.
- Duplicate alerts, incorrect entity mappings, stale data, revised data, or competing catalysts caused false positives.

## Improvement candidate for the separate research/improvement automation

Candidate: implement and shadow-test a merged, Telegram-disabled paper-performance evaluator that reads immutable alert records and restored market-data caches, writes reproducible SQLite performance tables, and uploads the database/report as artifacts.

- Measured problem: no real profitability/usefulness evaluation can be performed because the merged branch lacks a dispatchable evaluator and this automation cannot access the SQLite/cache/artifact evidence.
- Affected records: all historical stock `Buy`/`Sell` alerts and verified public-figure `Good`/`Bad` alerts whose rows exist only in inaccessible workflow caches/artifacts.
- Expected benefit: makes mature/pending/excluded counts, trigger rates, cost-adjusted expectancy, profit factor, drawdown, benchmark-adjusted returns, false-positive rates, confidence calibration, and ranked loss-of-expectancy causes measurable.
- Risk: false precision if the evaluator reconstructs prices, rewrites alerts, ignores inactive triggers, or fills missing data. It must preserve original records and label missing/stale/revised data explicitly.
- Required data: immutable alerts, raw statements, stock alert payloads, active/closed paper Buy positions, strategy version per alert, source/delivery timestamps, saved OHLCV snapshots or provider fetch metadata, benchmark/sector series, spread/slippage/latency/cost assumptions, and data-quality flags.
- Proposed test: shadow-only branch with Telegram credentials explicitly blank and fixture SQLite databases covering activated/pending Buy, Sell downside-avoidance, Sell closing an existing paper Buy, verified public Good/Bad, stale data, revised data, missing data, duplicate alerts, and inactive triggers.
- Recommendation: shadow testing only. Do not deploy strategy-rule changes from the current evidence.

## Actions taken and not taken

Taken:

- Inspected repository metadata, permissions, recent commits, open PRs, workflow files, public Actions summaries, and database schema files.
- Added this report-only audit record on branch `audit/performance-evaluation-20260719`.

Not taken:

- No performance-evaluation workflow was dispatched because no such workflow exists on `main` and Actions dispatch/list capability is unavailable.
- No live market scan, stock scan, public-figure scan, candidate refresh, Telegram test, or Telegram market alert was run.
- No production strategy rules, Buy/Sell gates, confidence labels, thresholds, old prices, alert timestamps, alert history, asset mappings, or workflow schedules were changed.
- No SQLite production rows were modified.
- No secrets were read, requested, exposed, logged, or committed.

## Validation

- Report-only change; no production code changed.
- Direct file fetches verified current `main` workflow files and schema files through the GitHub connector.
- Direct fetch of `.github/workflows/performance-evaluation.yml` on `main` returned 404.
- Public Actions page was inspected for current visible workflow list and recent run summaries.
- Local tests were not run because there is no local checkout and direct GitHub clone/download is blocked by network policy.
- No GitHub Actions workflow conclusion was produced by this audit because no dispatch occurred.

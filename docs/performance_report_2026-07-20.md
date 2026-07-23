# Paper Performance Evaluation Report - 2026-07-20

## Run metadata

- Report version: `paper-performance-audit-v3`
- Evaluation timestamp: `2026-07-19T22:30:01Z` (`2026-07-20 02:30:01 Asia/Dubai`)
- Repository inspected: `260xs/trump-market-alert`
- Base branch inspected: `main`
- Base commit observed: `294eb417f59df3257b2f2922d739698de2f942ae` (`Send daily system health checks to Telegram`)
- Scope: audit-only. No live market scans, stock scans, public-figure scans, candidate refreshes, Telegram tests, Telegram market alerts, production signal-rule changes, deployments, or strategy changes were performed.
- Secrets policy: no secrets were read, requested, printed, committed, or logged.

## Executive conclusion

Insufficient out-of-sample evidence to claim profitability.

No matured High-confidence `Buy`, `Sell`, or verified public-figure `Good`/`Bad` alert could be evaluated in this run because the timestamped production SQLite alert history, saved market data, strategy-version metadata, Actions caches, logs, and artifacts were not accessible to this automation. Missing records were excluded rather than reconstructed or guessed.

## Workflow dispatch and run verification

The requested performance-evaluation workflow could not be dispatched or monitored.

| Item | Verified evidence | Result |
| --- | --- | --- |
| Performance-evaluation workflow on `main` | Direct fetch of `.github/workflows/performance-evaluation.yml` returned GitHub 404. The public Actions workflow list did not show a performance evaluator. | Not present on `main`; no performance-evaluation run link or conclusion exists. |
| Equivalent merged evaluator | `manual-run-all.yml`, `stable-monitor.yml`, `hourly-stock-scan.yml`, and `stock-candidate-refresh.yml` were inspected. They run scanners or candidate refreshes, not paper-performance evaluation. | No safe equivalent evaluator found on `main`. |
| Same audit queued/running | Open PR #12 is a prior draft report branch, not a queued/running GitHub Actions evaluation. The public Actions page is read-only and does not expose authenticated queued/running state. | No duplicate evaluator was started. |
| Actions dispatch/list capability | Direct `git clone` failed with `CONNECT tunnel failed, response 403`; no `gh` CLI is available; the exposed GitHub connector in this run did not include Actions run-list, artifact, cache, or workflow-dispatch tools. | Blocked. |

Recent public Actions evidence visible during this run:

| Workflow | Public run | Trigger | Verified visible conclusion | Link |
| --- | ---: | --- | --- | --- |
| Market-Moving Public Figure Alert | #251 | schedule | `Status Success`; total duration `1m 29s`; triggered July 16, 2026 16:46. | https://github.com/260xs/trump-market-alert/actions/runs/29517005381 |
| Hourly Stock Research Scanner | #202 | schedule | `Status Success`; total duration `45s`; triggered July 16, 2026 16:38. | https://github.com/260xs/trump-market-alert/actions/runs/29516399012 |
| GitHub Actions Watchdog | #14 | schedule | Listed on the public Actions index as a completed scheduled run with duration `8s`. | https://github.com/260xs/trump-market-alert/actions/runs/29515779108 |
| Telegram Test | #33 | schedule | Listed on the public Actions index as a completed scheduled run with duration `10s`. No Telegram test was dispatched by this audit. | https://github.com/260xs/trump-market-alert/actions/runs/29509943393 |

Important limitation: the public Actions page showed older scheduled runs from commit `49f35de`, while current `main` workflow files fetched through the GitHub connector are manual-only `workflow_dispatch` for the inspected scanner workflows. This report records the inconsistency and does not infer current queued/running state from it.

## Repository and data inventory

| Evidence source | Status | Audit impact |
| --- | --- | --- |
| Local checkout | Unavailable. Direct clone to GitHub failed with proxy 403; only GitHub connector reads and public GitHub HTML were available. | Could not run a local evaluator, inspect uncommitted SQLite files, or execute the test suite. |
| Public-figure SQLite schema | `database/db.py` defines `raw_statements`, `detected_entities`, `alerts`, `dedupe_keys`, `source_state`, and `scheduler_runs`. | Schema can store alert/source records, but actual production rows were unavailable. |
| Stock SQLite schema | `stocks/research_db.py` defines `stock_alerts`, `top_candidates`, `stock_scans`, and `active_stock_setups`. | Schema can store stock alerts/scans/setups, but actual production rows were unavailable. |
| Saved market data | Expected under workflow cache/artifact paths such as `data/market_alerts.sqlite3` and `data/stocks.sqlite3`; not committed. | Could not compute trigger activation, forward outcomes, MFE/MAE, target/invalidation order, benchmark/sector adjustment, costs, or data-quality flags. |
| Strategy versions and market regimes | No merged per-alert strategy-version/performance table was found in accessible files. | Historical rows cannot be sliced reliably by strategy version or market regime. |
| Prior audit branch | PR #12 adds `docs/performance_report_2026-07-19.md`, but it is draft/unmerged and records the same blocked evidence path. | Useful context only; not production `main` state. |

## Record accounting

| Category | Count | Status / exclusion reason |
| --- | ---: | --- |
| Alert records examined from production SQLite | 0 | Production SQLite databases/caches/artifacts inaccessible. |
| Matured High-confidence Buy alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Matured High-confidence Sell alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Matured verified public-figure Good/Bad alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Pending alerts | Unknown | Requires original alert timestamps, trigger levels, delivery timestamps, and current/historical market data. |
| Excluded records | Unknown | Raw record ids cannot be enumerated without the original SQLite/cache/artifact data. |

Global exclusion reason for unavailable rows: `Source SQLite/cache/artifact unavailable to this automation run; excluded rather than reconstructed or guessed.`

## Required per-alert fields

No per-alert fields were computed in this run. Each required field remains blocked by missing timestamped rows and saved market data:

| Required field | Status | Reason |
| --- | --- | --- |
| Trigger activated and trigger time | Not computed | Requires original alert rows and forward candles. |
| Price at alert and trigger | Not computed | Requires immutable alert timestamp, trigger level, and timestamped market-data snapshot. |
| 1-hour, 1-day, 5-day, and 20-day outcomes | Not computed | Requires mature post-alert/post-trigger market data. |
| Maximum favorable and adverse movement | Not computed | Requires intraperiod OHLCV data. |
| Target or invalidation first | Not computed | Requires original target/invalidation and forward candles. |
| Market- and sector-adjusted return | Not computed | Requires matching benchmark and sector series. |
| Spread, slippage, latency, and costs | Not computed | Requires timestamped delivery/fill assumptions and cost model inputs. |
| Market regime | Not computed | Requires persisted regime snapshot or reproducible classifier. |
| Strategy version | Not computed | Requires per-alert strategy metadata or reliable commit mapping. |
| Data-quality status | Not computed | Requires raw provider snapshots, fetch time, stale/revised flags, and cache lineage. |

## Formulas and assumptions to apply once data is available

- Buy trigger activation: first post-alert market timestamp where price reaches or crosses the entry trigger.
- Buy paper return: `(measurement_or_exit_price - trigger_price) / trigger_price - estimated_costs_pct`, measured only after the entry trigger activates.
- Sell downside avoidance: `(price_at_alert_or_trigger - later_price) / price_at_alert_or_trigger`, interpreted as avoided downside, not a short trade.
- Sell exit P&L: computed only when the Sell closes an existing tracked paper Buy position; otherwise no trade P&L is recorded.
- Public-figure Good accuracy: positive when post-alert abnormal return is greater than zero after latency/cost assumptions.
- Public-figure Bad accuracy: positive when post-alert abnormal return is less than zero after latency/cost assumptions.
- Abnormal return: asset return minus benchmark or sector return over the same timestamped horizon.
- Net expectancy after costs: `(success_probability x average_net_gain) - (failure_probability x average_net_loss) - realistic_costs`.
- Profit factor: gross gains divided by gross losses after costs when costed returns are available.
- Maximum drawdown: largest peak-to-trough decline in the chronological paper-equity curve after costs.
- Confidence interval/bootstrap: apply only when sample size is large enough for resampling to be meaningful; otherwise label the sample insufficient.

Cost assumptions were not applied numerically because no trades/outcomes were measurable. A future evaluator must store the exact spread, slippage, latency, commission/fee, market-data provider, benchmark/sector mapping, and data-quality assumptions used for each run.

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

Confirmed largest weakness: the project does not have a merged, dispatchable, reproducible paper-performance evaluator on `main`, and this automation path cannot access the historical SQLite/cache/artifact evidence required to evaluate profitability or usefulness.

| Rank | Problem | Estimated effect | Frequency | Confidence | Evidence |
| ---: | --- | --- | --- | --- | --- |
| 1 | Missing merged paper-performance evaluator | Blocks all cost-adjusted profitability/usefulness claims. | Systemic | High | `.github/workflows/performance-evaluation.yml` is absent on `main`; no evaluator workflow is visible in Actions; inspected merged workflows are scanners/refreshes. |
| 2 | Inaccessible SQLite/caches/artifacts | Blocks record-level outcomes, exclusions, and reproducibility. | Systemic for this audit path | High | Workflow files restore/save `data`; production databases and artifacts are not accessible through current tools. |
| 3 | No per-alert performance/strategy/regime table on `main` | Prevents reliable slicing by strategy version, market regime, ticker, source, and confidence calibration. | Systemic | Medium-High | Accessible schemas contain alert and scan tables, but no merged outcome/evaluation table was found. |
| 4 | Actions run-list/dispatch unavailable to this automation | Prevents duplicate-run protection and real evaluator conclusion verification. | This run | High | No `gh`, direct GitHub network 403, and connector lacks Actions dispatch/list/artifact/cache operations. |
| 5 | Workflow state mismatch | Can confuse audit scheduling and run attribution. | Current visible state | Medium | Public Actions shows scheduled runs from commit `49f35de`; current `main` scanner workflows fetched by connector are manual-only after later commits. |

Hypotheses not confirmed because record-level data was unavailable:

- Late detection or source latency reduced expectancy.
- Wide spreads, slippage, low liquidity, or realistic costs erased small expected moves.
- Trigger placement was overextended or invalidations were too wide.
- Market-regime or sector confirmation was weak.
- Duplicate alerts, incorrect entity mappings, stale/revised data, or competing catalysts caused false positives.

## Improvement candidate for separate research/improvement automation

Candidate: implement and shadow-test a merged, Telegram-disabled paper-performance evaluator that reads immutable alert records and restored market-data caches, writes reproducible SQLite performance tables, and uploads the database/report as artifacts.

- Measured problem: no real profitability/usefulness evaluation can be performed because `main` lacks a dispatchable evaluator and this automation cannot access the SQLite/cache/artifact evidence.
- Affected records: all historical stock `Buy`/`Sell` alerts and verified public-figure `Good`/`Bad` alerts whose rows exist only in inaccessible workflow caches/artifacts.
- Expected benefit: makes mature/pending/excluded counts, trigger rates, directional precision, cost-adjusted expectancy, profit factor, drawdown, benchmark-adjusted returns, false-positive rates, confidence calibration, and ranked lost-expectancy causes measurable.
- Risk: false precision if the evaluator reconstructs prices, rewrites alerts, ignores inactive triggers, moves timestamps, relabels confidence, or fills missing data. It must preserve original records and label missing/stale/revised data explicitly.
- Required data: immutable alerts, raw statements, stock alert payloads, active/closed paper Buy positions, strategy version per alert, source/delivery timestamps, saved OHLCV snapshots or provider fetch metadata, benchmark/sector series, spread/slippage/latency/cost assumptions, and data-quality flags.
- Proposed test: shadow-only branch with Telegram credentials explicitly blank and fixture SQLite databases covering activated/pending Buy, Sell downside avoidance, Sell closing an existing paper Buy, verified public Good/Bad, stale data, revised data, missing data, duplicate alerts, and inactive triggers.
- Recommendation: shadow testing only. Do not deploy strategy-rule changes from the current evidence.

## Actions taken and not taken

Taken:

- Inspected repository metadata, permissions, recent commits, open PRs, merged workflow files, public Actions summaries, and database schema files.
- Checked prior audit PR #12 and confirmed it is a draft report branch, not a running evaluator.
- Added this report-only audit record on branch `audit/performance-evaluation-20260720`.

Not taken:

- No performance-evaluation workflow was dispatched because no such workflow or safe equivalent exists on `main`, and Actions dispatch/list capability is unavailable in this run.
- No live market scan, stock scan, public-figure scan, candidate refresh, Telegram test, or Telegram market alert was run.
- No production strategy rules, Buy/Sell gates, confidence labels, thresholds, old prices, alert timestamps, alert history, asset mappings, database migrations, or workflow schedules were changed.
- No SQLite production rows were modified.
- No secrets were read, requested, exposed, logged, or committed.

## Validation

- Report-only change; no production code changed.
- Direct file fetches verified current `main` workflow files and schema files through the GitHub connector.
- Direct fetch of `.github/workflows/performance-evaluation.yml` on `main` returned 404.
- Public Actions pages verified recent public-figure and stock scanner runs had visible `Status Success`; no performance-evaluation run existed to verify.
- Local tests were not run because direct clone/download is blocked by network policy and this change is documentation-only.
- No GitHub Actions workflow conclusion was produced by this audit because no dispatch occurred.

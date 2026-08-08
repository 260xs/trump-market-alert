# Paper Performance Evaluation Report - 2026-07-23

## Run metadata

- Report version: `paper-performance-audit-v6`
- Evaluation timestamp: `2026-07-22T22:30:01Z` (`2026-07-23 02:30:01 Asia/Dubai`)
- Repository inspected: `260xs/trump-market-alert`
- Base branch inspected: `main`
- Base commit observed from GitHub connector: `291e135b8912ff4423f8f7bfd0392d631ac0c5df` (`Remove routine health cron Telegram ping`)
- Scope: audit-only. No live market scans, stock scans, public-figure scans, candidate refreshes, Telegram tests, Telegram market alerts, production signal-rule changes, deployments, or strategy changes were performed.
- Secrets policy: no secrets were read, requested, printed, committed, or logged.

## Executive conclusion

Insufficient out-of-sample evidence to claim profitability.

No matured High-confidence `Buy`, `Sell`, or verified public-figure `Good`/`Bad` alert could be evaluated in this run because the required timestamped production SQLite alert history, saved market-data snapshots, strategy-version metadata, Actions caches, logs, and artifacts were not accessible to this automation. Missing evidence was excluded rather than reconstructed or guessed.

## Workflow dispatch and run verification

The requested performance-evaluation workflow could not be dispatched or monitored.

| Item | Verified evidence | Result |
| --- | --- | --- |
| Same audit queued/running | Open draft PR #27 exists for the 2026-07-22 report-only audit. It is not a queued/running GitHub Actions evaluation run. No dispatchable performance evaluator was found on `main`. | No duplicate evaluator run was started. |
| Performance-evaluation workflow on `main` | Direct connector fetch of `.github/workflows/performance-evaluation.yml` returned GitHub 404. Public Actions workflow list did not include a performance-evaluation workflow. | Not present on `main`; no workflow_dispatch run could be started. |
| Repository equivalent | Inspected `manual-run-all.yml`, `stable-monitor.yml`, `hourly-stock-scan.yml`, `stock-candidate-refresh.yml`, and `telegram-test.yml`. They run scanners, candidate refresh, or Telegram test; none performs paper-performance evaluation. | No safe equivalent evaluator found. |
| Real GitHub conclusion for this audit | No run was dispatched because the workflow is absent and Actions dispatch/list tools are unavailable. | No performance-evaluation run link or conclusion exists for this audit. |
| Actions access in this environment | `gh` CLI is not installed; direct `git ls-remote`, `git clone`, GitHub archive download, and GitHub REST calls failed with `CONNECT tunnel failed, response 403`; the exposed connector lacks Actions run-list, workflow-dispatch, artifact, cache, and log operations. | Blocked from authenticated Actions verification. |

Recent public Actions evidence visible from the public GitHub page:

| Workflow | Run | Trigger | Visible conclusion | Link |
| --- | ---: | --- | --- | --- |
| Market-Moving Public Figure Alert | #251 | schedule | Success; triggered July 16, 2026 16:46; duration 1m 29s. | https://github.com/260xs/trump-market-alert/actions/runs/29517005381 |
| Hourly Stock Research Scanner | #202 | schedule | Success; triggered July 16, 2026 16:38; duration 45s. | https://github.com/260xs/trump-market-alert/actions/runs/29516399012 |
| Stock Candidate Refresh | #21 | schedule | Success; duration 52s from the public workflow list and run page summary. | https://github.com/260xs/trump-market-alert/actions/runs/29484343755 |
| Manual Run All Scanners | #5 | workflow_dispatch | Visible in the public Actions index as manually run on `main`; duration 2m 22s. | https://github.com/260xs/trump-market-alert/actions/runs/29515501248 |

Limitation: the public Actions pages showed 546 workflow runs and older scheduled workflow runs, but they did not expose authenticated logs/artifacts/caches or current queued/running state. Current `main` workflow files fetched through the connector are manual-only for the inspected scanner and Telegram-test workflows, so visible older scheduled runs reflect historical workflow definitions rather than the current `main` files.

## Repository and data inventory

| Evidence source | Status | Audit impact |
| --- | --- | --- |
| Local checkout | Unavailable. Direct GitHub clone/archive/REST access failed with proxy 403, and `gh` is unavailable. | Could not run local evaluator, inspect SQLite files, run tests, or scan artifacts locally. |
| Public-figure SQLite schema | `database/db.py` defines `raw_statements`, `detected_entities`, `alerts`, `dedupe_keys`, `source_state`, and `scheduler_runs`. | Schema supports alert/source records, but production rows were unavailable. |
| Stock SQLite schema | `stocks/research_db.py` defines `stock_alerts`, `top_candidates`, `stock_scans`, and `active_stock_setups`. | Schema supports stock alerts/scans/setups, but production rows were unavailable. |
| Saved market data | Workflow files restore/save `data`, including `data/market_alerts.sqlite3` and `data/stocks.sqlite3`, through Actions cache. | Cache/artifact data was not accessible; no timestamped outcomes could be computed. |
| Strategy versions and regimes | No merged per-alert strategy-version/performance table was found in accessible files. | Cannot slice results by strategy version or market regime. |
| Prior audit artifacts | PR #27 contains a prior report-only performance audit, still draft/unmerged. | Context only; not production `main` evidence. |

## Record accounting

| Category | Count | Status / exclusion reason |
| --- | ---: | --- |
| Alert records examined from production SQLite | 0 | Production SQLite/cache/artifact data inaccessible. |
| Matured High-confidence Buy alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Matured High-confidence Sell alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Matured verified public-figure Good/Bad alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Pending alerts | Unknown | Requires original alert rows, trigger levels, timestamps, and forward market data. |
| Excluded records | Unknown | Raw record IDs cannot be enumerated without original SQLite/cache/artifact data. |

Global exclusion reason: `Source SQLite/cache/artifact unavailable to this automation run; excluded rather than reconstructed or guessed.`

## Required per-alert fields

No per-alert outcomes were computed. Each required field is blocked by missing immutable alert rows and saved timestamped market data.

| Required field | Status | Reason |
| --- | --- | --- |
| Trigger activated and trigger time | Not computed | Requires original alert rows and forward candles. |
| Price at alert and trigger | Not computed | Requires immutable alert timestamp, trigger level, and timestamped price data. |
| 1-hour, 1-day, 5-day, and 20-day outcomes | Not computed | Requires mature post-alert/post-trigger data. |
| Maximum favorable and adverse movement | Not computed | Requires intraperiod OHLCV data. |
| Target or invalidation first | Not computed | Requires original target/invalidation and forward candles. |
| Market- and sector-adjusted return | Not computed | Requires synchronized benchmark and sector series. |
| Spread, slippage, latency, and costs | Not computed | Requires timestamped delivery/fill assumptions and cost model inputs. |
| Market regime and strategy version | Not computed | Requires persisted regime/version metadata or reproducible classifier inputs. |
| Data-quality status | Not computed | Requires provider snapshots, fetch timestamps, stale/revised flags, and cache lineage. |

## Formulas and assumptions for a future evaluator

- Buy trigger activation: first post-alert market timestamp where price reaches or crosses the entry trigger.
- Buy paper return: `(measurement_or_exit_price - trigger_price) / trigger_price - estimated_costs_pct`, measured only after the entry trigger activates.
- Sell downside avoidance: `(price_at_alert_or_trigger - later_price) / price_at_alert_or_trigger`, interpreted as avoided downside, not as a short trade.
- Sell exit P&L: computed only when the Sell closes an existing tracked paper Buy position; otherwise no trade P&L is recorded.
- Public-figure Good accuracy: positive when post-alert abnormal return is greater than zero after latency and cost assumptions.
- Public-figure Bad accuracy: positive when post-alert abnormal return is less than zero after latency and cost assumptions.
- Abnormal return: asset return minus benchmark or sector return over the same timestamped horizon.
- Net expectancy after costs: `(success_probability x average_net_gain) - (failure_probability x average_net_loss) - realistic_costs`.
- Profit factor: gross gains divided by gross losses after costs when costed returns are available.
- Maximum drawdown: largest peak-to-trough decline in the chronological paper-equity curve after costs.
- Confidence intervals/bootstrap ranges: apply only when sample size is large enough for resampling to be meaningful; otherwise label the sample insufficient.

No numeric spread, slippage, latency, or cost assumptions were applied because no record-level outcomes were measurable.

## Results by required segment

All metrics are unavailable rather than zero because no timestamped out-of-sample observations were accessible.

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

No strongest or weakest ticker, source, public figure, sector, strategy version, or market-regime group can be identified from evidence in this run. Ranking would require original alert rows and forward outcomes.

## Largest evidence-based weakness

Confirmed largest weakness: `main` lacks a merged, dispatchable, reproducible paper-performance evaluator, and this automation path cannot access the historical SQLite/cache/artifact evidence required to evaluate profitability or usefulness.

| Rank | Problem | Estimated effect | Frequency | Confidence | Evidence |
| ---: | --- | --- | --- | --- | --- |
| 1 | Missing merged paper-performance evaluator | Blocks all cost-adjusted profitability/usefulness claims. | Systemic | High | `.github/workflows/performance-evaluation.yml` is absent on `main`; accessible workflows are scanners/refresh/test only. |
| 2 | Inaccessible SQLite/caches/artifacts | Blocks record-level outcomes, exclusions, reproducibility, and data-quality checks. | Systemic for this automation path | High | Workflow files restore/save `data`; cache/artifact/log access is unavailable here. |
| 3 | No merged per-alert performance/strategy/regime table | Prevents slicing by strategy version, regime, ticker, source, and confidence calibration. | Systemic | Medium-High | Accessible schemas store alerts/scans, but no performance outcome table was found. |
| 4 | Actions dispatch/run-list unavailable in this environment | Prevents duplicate-run monitoring and real evaluator conclusion verification. | This run | High | No `gh`, direct GitHub clone/archive/REST 403, connector lacks Actions operations. |
| 5 | Workflow documentation/runtime mismatch | Can confuse audit scheduling and run attribution. | Current visible state | Medium | README documents schedules; fetched `main` workflows inspected here are manual-only, while public Actions still shows older scheduled runs. |

Hypotheses not confirmed because record-level data was unavailable:

- Late detection or source latency reduced expectancy.
- Wide spreads, slippage, low liquidity, or realistic costs erased small expected moves.
- Trigger placement was overextended or invalidations were too wide.
- Market-regime or sector confirmation was weak.
- Duplicate alerts, incorrect entity mappings, stale/revised data, or competing catalysts caused false positives.

## Improvement candidate for separate research/improvement automation

Candidate: implement and shadow-test a merged, Telegram-disabled paper-performance evaluator that reads immutable alert records and restored market-data caches, writes reproducible SQLite performance tables, and uploads the database/report as artifacts.

- Measured problem: no real profitability/usefulness evaluation can be performed because `main` lacks a dispatchable evaluator and this automation cannot access the SQLite/cache/artifact evidence.
- Affected records: all historical stock `Buy`/`Sell` alerts and verified public-figure `Good`/`Bad` alerts whose rows exist only in workflow caches/artifacts.
- Expected benefit: makes mature/pending/excluded counts, trigger rates, directional precision, cost-adjusted expectancy, profit factor, drawdown, benchmark-adjusted returns, false-positive rates, confidence calibration, and ranked lost-expectancy causes measurable.
- Risk: false precision if the evaluator reconstructs prices, rewrites alerts, ignores inactive triggers, moves timestamps, relabels confidence, or fills missing data. It must preserve original records and label missing/stale/revised data explicitly.
- Required data: immutable alerts, raw statements, stock alert payloads, active/closed paper Buy positions, strategy version per alert, source/delivery timestamps, saved OHLCV snapshots or provider fetch metadata, benchmark/sector series, spread/slippage/latency/cost assumptions, and data-quality flags.
- Proposed test: shadow-only branch with Telegram credentials explicitly blank and fixture SQLite databases covering activated/pending Buy, Sell downside avoidance, Sell closing an existing paper Buy, verified public Good/Bad, stale data, revised data, missing data, duplicate alerts, and inactive triggers.
- Recommendation: shadow testing only. Do not deploy strategy-rule changes from the current evidence.

## Actions taken and not taken

Taken:

- Inspected repository metadata, permissions, recent commits, open PRs, branches, merged workflow files, public Actions summaries, README deployment notes, and database schema files.
- Checked for existing performance-evaluation workflow or equivalent evaluator on `main`.
- Added this report-only audit record on branch `audit/performance-evaluation-20260723`.

Not taken:

- No performance-evaluation workflow was dispatched because no such workflow or safe equivalent exists on `main`, and Actions dispatch/run-list capability is unavailable in this run.
- No live market scan, stock scan, public-figure scan, candidate refresh, Telegram test, or Telegram market alert was run.
- No production strategy rules, Buy/Sell gates, confidence labels, thresholds, old prices, alert timestamps, alert history, asset mappings, database migrations, workflow schedules, or deployment settings were changed.
- No SQLite production rows were modified.
- No secrets were read, requested, exposed, logged, or committed.

## Validation

- Report-only change; no production code changed.
- Direct connector fetch verified current `main` workflow files and schema files.
- Direct connector fetch of `.github/workflows/performance-evaluation.yml` on `main` returned 404.
- Public Actions pages verified visible Success status for older public-figure run #251, hourly stock run #202, and stock candidate refresh #21, but logs/artifacts/caches remain inaccessible without sign-in.
- Local tests were not run because direct clone/download is blocked by network policy and this is documentation-only.
- No GitHub Actions workflow conclusion was produced by this audit because no dispatch occurred.

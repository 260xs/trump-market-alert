# Paper Performance Evaluation Report - 2026-07-18

## Run metadata

- Report version: `paper-performance-audit-v1`
- Evaluation timestamp: `2026-07-17T22:30:01Z` (`2026-07-18 02:30:01 Asia/Dubai`)
- Repository inspected: `260xs/trump-market-alert`
- Base branch inspected: `main`
- Base commit observed: `d86f7146084bb3198c4d01d99cc48a6685097a91`
- Scope: audit-only. No live market scans, Telegram market alerts, production signal-rule changes, deployments, or strategy changes were performed.
- Secrets policy: no secrets were read, requested, printed, committed, or logged.

## Workflow/run verification

The requested performance-evaluation workflow could not be dispatched from this automation run.

Verified facts:

| Item | Evidence | Result |
| --- | --- | --- |
| Existing performance-evaluation workflow on `main` | Repository search and direct workflow-file reads did not find a committed `performance`, `paper`, or equivalent evaluator workflow on `main`. | Not present on `main` |
| Draft audit workflow | PR #3, `Add manual missed opportunity audit workflow`, adds `.github/workflows/missed-opportunity-audit.yml`. | Draft PR, not merged, not a full paper-performance evaluator |
| GitHub Actions dispatch/list API from container | Direct `curl` to GitHub API failed with `CONNECT tunnel failed, response 403`; `gh` CLI is unavailable. | Blocked |
| Public Actions page | Public page was readable and showed recent workflow-run summaries. | Read-only verification only |

Recent operational runs verified from the public Actions page:

| Workflow | Run | Trigger | Commit | Conclusion | Duration | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| Market-Moving Public Figure Alert | #251 | schedule | `49f35de` | Success | 1m 29s | https://github.com/260xs/trump-market-alert/actions/runs/29517005381 |
| Hourly Stock Research Scanner | #202 | schedule | `49f35de` | Success | 45s | https://github.com/260xs/trump-market-alert/actions/runs/29516399012 |
| Telegram Test | #33 | schedule | `49f35de` | Public page did not expose complete final details in the captured lines; no audit Telegram test was dispatched by this run. | 10s listed on Actions index | https://github.com/260xs/trump-market-alert/actions/runs/29509943393 |

Important limitation: the public Actions page showed 546 workflow runs and older scheduled runs on commit `49f35de`; direct files fetched from `main` currently show `workflow_dispatch` only for the core operational workflows. This report records that inconsistency instead of guessing whether a queued audit exists.

## Data inventory

| Evidence source | Status | Audit impact |
| --- | --- | --- |
| Local repository checkout | Unavailable; direct clone failed with `CONNECT tunnel failed, response 403`. | Could not run local tests or inspect SQLite caches locally. |
| SQLite databases | Not committed to repository; expected to live under Actions cache paths such as `data/market_alerts.sqlite3` and `data/stocks.sqlite3`. | Could not examine alert-history rows or paper-position rows from this run. |
| Alert history | Not accessible as timestamped rows in the current connector/tool surface. | No mature alert outcomes could be calculated without inventing records. |
| Saved market data | Not accessible from repository files or Actions artifacts in this run. | No 1-hour, 1-day, 5-day, 20-day, MFE, MAE, target/invalidation, benchmark, or sector-adjusted returns could be recomputed. |
| Strategy versions | No committed performance/evaluation table discovered on `main`. Operational logic versions can only be inferred from commits unless explicit strategy metadata exists in SQLite. | Strategy-version attribution is blocked for historical rows. |
| Actions artifacts/logs | Public pages show run summaries but logs/artifacts require signed-in Actions access. | Audit artifacts and cached databases could not be downloaded. |

## Records examined

This run examined repository metadata, workflow definitions, PR metadata, public Actions summaries, and the draft missed-opportunity audit workflow. It did not access the underlying SQLite alert records or cached market data.

| Category | Count | Basis |
| --- | ---: | --- |
| Alert records examined from SQLite | 0 | SQLite databases/artifacts inaccessible. |
| Matured High-confidence Buy alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Matured High-confidence Sell alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Matured verified public-figure alerts evaluated | 0 | No timestamped out-of-sample rows available. |
| Pending alerts | Unknown | Requires alert timestamps and current/historical market data. |
| Excluded records | Unknown | Raw records inaccessible; exclusions cannot be enumerated by id. |

Excluded record reason for all unavailable historical rows: `Source SQLite/cache/artifact unavailable to this automation run; record excluded rather than reconstructed or guessed.`

## Required paper-performance fields

The following fields were not computed because the necessary timestamped out-of-sample records were unavailable:

| Field | Status | Reason |
| --- | --- | --- |
| Trigger activated and trigger time | Not computed | Requires original alert rows and post-alert candles. |
| Price at alert and trigger | Not computed | Requires immutable alert timestamp and market-data snapshots. |
| 1-hour, 1-day, 5-day, 20-day outcomes | Not computed | Requires mature timestamped rows and historical candles. |
| Maximum favorable/adverse movement | Not computed | Requires intraperiod OHLC data. |
| Target or invalidation first | Not computed | Requires original levels and forward candles. |
| Market- and sector-adjusted return | Not computed | Requires benchmark/sector series at matching timestamps. |
| Spread, slippage, latency, costs | Not computed | Requires pricing source, assumed execution model, and alert-delivery timestamps. |
| Market regime | Not computed | Requires committed regime snapshot or reproducible regime classifier. |
| Strategy version | Not computed | Requires persisted strategy version per alert or reliable commit mapping. |
| Data-quality status | Blocked | Missing/stale/revised-data checks require raw datasets. |

## Formulas intended for the evaluator

These formulas should be applied only to timestamped out-of-sample observations:

- Buy trigger activation: first post-alert market timestamp where price reaches or crosses the entry trigger.
- Buy paper return: `(exit_or_measure_price - trigger_price) / trigger_price - estimated_costs_pct`, measured only after trigger activation.
- Sell downside avoidance: `(price_at_alert_or_trigger - later_price) / price_at_alert_or_trigger`, interpreted as avoided downside, not a short trade.
- Sell exit P&L: only computed when the Sell closes an existing tracked paper Buy position; otherwise no trade P&L is recorded.
- Public-figure Good directional outcome: positive if post-alert abnormal return is greater than zero over the selected horizon after costs/latency assumptions.
- Public-figure Bad directional outcome: positive if post-alert abnormal return is less than zero over the selected horizon after costs/latency assumptions.
- Abnormal return: asset return minus benchmark or sector return over the same timestamped horizon.
- Net expectancy: `(success_probability x average_net_gain) - (failure_probability x average_net_loss) - realistic_costs`.
- Profit factor: gross gains divided by gross losses, after costs when costed returns are available.
- False-positive rate: false positives divided by alerts with mature measurable outcomes.
- Confidence calibration: observed success rate by stored confidence bucket compared with expected confidence ordering.

## Results

Because no timestamped out-of-sample alert rows and no saved market-data rows were available to this run, all performance metrics are unavailable rather than zero.

| Segment | Sample size | Trigger rate | Directional precision | Win rate | Average gain | Average loss | Payoff ratio | Profit factor | Net expectancy after costs | Maximum drawdown | Benchmark-adjusted performance | False-positive rate | Confidence calibration |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Buy alerts | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Sell downside-avoidance alerts | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Verified public-figure alerts | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| By ticker/source/person/sector/regime/version | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

Insufficient out-of-sample evidence to claim profitability.

## Biggest evidence-based weakness

Confirmed weakness: no merged, reproducible paper-performance evaluation path exists on `main`, and the required historical evidence is not accessible to this audit run through repository files, public Actions pages, or exposed connector tools.

Why this is the largest measurable weakness:

| Factor | Evidence | Frequency | Estimated effect | Confidence |
| --- | --- | --- | --- | --- |
| Missing merged evaluator | No performance/paper/equivalent evaluator workflow discovered on `main`; PR #3 is draft and only classifies missed opportunities. | Systemic | Blocks all profitability/usefulness claims. | High |
| Inaccessible SQLite/cached artifacts | Databases are restored/saved by workflow caches but not exposed to this run. | Systemic | Prevents record-level evaluation and reproducibility. | High |
| No committed performance tables/report baseline | Repository search found no paper-performance or expectancy artifacts on `main`. | Systemic | Prevents trend tracking across runs. | High |
| Dispatch/log API blocked | Container API calls to GitHub failed with 403 and `gh` is unavailable. | This run | Prevented `workflow_dispatch` and artifact verification. | High |
| README/workflow mismatch | Fetched `main` workflows are manual-only while README still describes scheduled workflows. Public Actions page shows recent older scheduled runs on `49f35de`. | Current docs/state | Can confuse audit scheduling and run attribution. | Medium |

Hypotheses not confirmed because record-level data was unavailable:

| Hypothesis | Needed evidence |
| --- | --- |
| Late detection reduced expectancy | Alert issued timestamps, source published timestamps, trigger timestamps, delivery timestamps, and intraday candles. |
| Trigger placement is overextended | Original trigger levels, post-trigger MFE/MAE, and strategy version per alert. |
| Stale/revised data distorted results | Data provider snapshots, fetch timestamps, vendor revision status, and cache lineage. |
| Wide spreads/slippage dominate returns | Bid/ask or conservative spread assumptions by ticker/time, plus realistic execution-latency model. |
| Weak regime/sector alignment | Regime snapshot and sector benchmark at alert time. |

## Improvement candidate for separate research/improvement automation

Candidate: build and shadow-test a merged paper-performance evaluator that reads immutable alert records and restored market-data caches, writes reproducible SQLite tables, and uploads artifacts without Telegram.

- Measured problem: profitability/usefulness cannot be evaluated because the merged branch lacks a complete evaluator and this run could not access historical SQLite/cached market data.
- Affected records: all historical Buy, Sell, and verified public-figure alerts stored only in inaccessible caches/artifacts.
- Expected benefit: enables real sample sizes, mature/pending/excluded counts, cost-adjusted expectancy, false-positive analysis, confidence calibration, and ranked loss-of-expectancy causes.
- Risk: if it uses reconstructed prices or missing records, it could create false precision. The evaluator must preserve original alerts and label missing/stale/revised data instead of filling gaps.
- Required data: immutable alerts table, paper position table if any, source/delivery timestamps, strategy version per alert, saved OHLCV snapshots or reproducible provider fetch metadata, sector/benchmark series, spread/slippage/latency/cost assumptions, and data-quality flags.
- Proposed test: shadow-only workflow on a focused branch with Telegram credentials explicitly blank, fixture SQLite databases covering activated/pending Buy, Sell downside-avoidance, Sell closing an existing paper Buy, verified public Good/Bad, duplicate, stale-data, and missing-data cases. Merge only after regression tests and workflow syntax checks pass.
- Deployment recommendation: shadow testing only. Do not deploy production strategy changes from this evidence.

## Validation performed by this run

- Confirmed repository metadata and permissions through the GitHub app.
- Fetched core workflow files from `main`.
- Fetched README from `main`.
- Fetched PR #3 metadata and workflow patch.
- Checked public GitHub Actions page and opened recent run summaries for public-figure and stock workflows.
- Attempted direct clone and GitHub API access; both were blocked by `CONNECT tunnel failed, response 403`.
- Confirmed `gh` CLI is not installed in the container.
- No Telegram messages were sent.
- No live public-figure scan, stock scan, candidate refresh, Telegram test, or market-data scan was dispatched by this run.

## Files updated

This report file was added as the audit record for this scheduled run. No production logic, workflow cron, alert thresholds, Buy/Sell gates, confidence labels, old prices, timestamps, alert history, or strategy rules were modified.

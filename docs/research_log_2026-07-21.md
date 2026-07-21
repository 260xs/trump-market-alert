# Research Log - 2026-07-21 Scheduled Maintenance

## Repository Evidence Reviewed

- Repository: 260xs/trump-market-alert, default branch main, latest inspected commit 291e135b8912ff4423f8f7bfd0392d631ac0c5df.
- Recent commits show operational scan crons were removed on 2026-07-16 in ebf6d251ba0644321be5c9eb12940792ae5cc1ba.
- Current main workflow files for stable-monitor.yml, hourly-stock-scan.yml, and stock-candidate-refresh.yml contain workflow_dispatch but no schedule trigger.
- README still documents the MVP schedules: public figure scanner 7,27,47 * * * *, hourly stock scanner 13 * * * *, candidate refresh 31 6 */3 * *.
- tests/test_workflows.py currently asserts those operational scanners are manual-only, which conflicts with the README and the GitHub Actions MVP requirement.
- Public GitHub Actions page shows historical scheduled scanner runs, but current run-list/log/artifact APIs were not available in this environment.
- Main branch has no docs/research_log.md and no performance-evaluation workflow found by repository search.
- Open PR #21 records the latest 2026-07-21 paper-performance audit conclusion: insufficient out-of-sample evidence to claim profitability, because no merged reproducible evaluator and no accessible historical SQLite/cache/artifact evidence exist on main.

## Selected Measured Weakness

Confirmed weakness: scheduled scanner coverage is disabled on main for the public-figure scanner, hourly stock scanner, and stock candidate refresh. This directly harms alert timing and coverage because no new scheduled scans can start from those workflow files.

Profitability impact is not quantified. The measured operational impact is binary: expected scheduled scans cannot be triggered by cron from the current workflow definitions. This is a reliability/coverage repair, not a production strategy change.

## Current Baseline

- stable-monitor.yml: manual-only.
- hourly-stock-scan.yml: manual-only.
- stock-candidate-refresh.yml: manual-only.
- Telegram test workflow: manual-only and sends only the exact setup-test message when manually dispatched.
- System health workflow: manual-only, no routine success Telegram heartbeat.
- Latest paper performance: unavailable/insufficient on main; no net expectancy, precision, average gain/loss, profit factor, drawdown, timing, or regime stability can be verified from accessible main-branch artifacts.

## Proposed Change

Restore only the documented MVP cron triggers for the three scanner workflows and update workflow regression coverage to assert the exact crons. Do not dispatch workflows. Do not change alert thresholds, Buy/Sell gates, public-figure confidence gates, dedupe, asset mappings, stock formulas, data providers, or Telegram formats.

## External Methods Reviewed

1. Zipline / Zipline Refresh
   - Sources: https://zipline-trader.readthedocs.io/en/latest/beginner-tutorial.html and https://zipline.ml4trading.io/
   - Problem addressed: realistic event-driven backtesting, slippage, transaction costs, order delay, and avoiding look-ahead bias.
   - Expected effect: better measurement of expectancy and timing if a future evaluator replays signals chronologically with costs.
   - Risks: adding a full engine is heavy; dependency and data-ingestion complexity are high for this small Telegram-only repo.
   - License/data needs: open-source engine; market data still must be legally sourced.
   - Test method: shadow evaluator comparing current scanner outputs to chronological forward returns after costs.
   - Decision: Backlog. Useful design principles, not suitable for this minimal reliability patch.

2. vectorbt
   - Sources: https://vectorbt.dev/ and https://github.com/polakowo/vectorbt
   - Problem addressed: fast large-scale strategy research and portfolio statistics across many parameter combinations.
   - Expected effect: stronger walk-forward evaluation and sensitivity testing across tickers/regimes.
   - Risks: high risk of overfitting if used to tune thresholds aggressively; dependency footprint larger than current tests need.
   - License/data needs: open-source/community edition; legal historical data required.
   - Test method: frozen development/holdout split, no holdout tuning, compare net expectancy and drawdown after costs.
   - Decision: Shadow-test later only if a reproducible evaluator exists.

3. Backtrader
   - Sources: https://www.backtrader.com/ and https://www.backtrader.com/docu/slippage/slippage/
   - Problem addressed: broker-simulation concepts, commission schemes, slippage, order modeling, analyzers.
   - Expected effect: more realistic cost modeling for paper performance.
   - Risks: GPL-3.0 license is likely incompatible with copying code into this repo; direct integration is not appropriate without explicit license review.
   - License/data needs: GPL-3.0 for upstream project; do not copy code.
   - Test method: reuse concepts only: explicit spread/slippage/latency cost fields in internal evaluator.
   - Decision: Reject direct reuse; keep concepts in backlog.

4. QuantConnect LEAN
   - Sources: https://github.com/quantconnect/lean and https://www.lean.io/
   - Problem addressed: professional event-driven research/backtest/live architecture with data normalization and broad asset coverage.
   - Expected effect: useful architecture reference for separating research, backtest, paper, and live concerns.
   - Risks: too large for MVP; includes trading/live infrastructure outside this repo's Telegram-only boundary.
   - License/data needs: Apache-2.0 upstream, but no code copied.
   - Test method: use as architecture reference for future paper evaluator, not as dependency now.
   - Decision: Backlog.

5. Event-study methodology
   - Sources: https://www.eventstudytools.com/introduction-event-study-methodology and https://www.bauer.uh.edu/rsusmel/phd/lecture%206.pdf
   - Problem addressed: measuring abnormal returns around events with estimation and event windows.
   - Expected effect: better public-figure impact attribution and competing-catalyst rejection.
   - Risks: needs clean event timestamps, quote/source verification, and market data around the original detection time; multiple overlapping catalysts can mislead results.
   - License/data needs: methodology only; no code copied.
   - Test method: shadow event study with predeclared windows and market-relative returns.
   - Decision: Backlog.

6. Official aggregate market-data documentation
   - Sources: https://massive.com/docs/rest/stocks/overview and https://polygon.readthedocs.io/en/latest/Stocks.html
   - Problem addressed: aggregate bars may omit empty intervals and adjusted/unadjusted settings affect historical candles.
   - Expected effect: better stale/partial-data rejection and split-aware performance evaluation.
   - Risks: provider access and rate limits; cannot assume missing bars are valid flat prices.
   - License/data needs: provider terms/API keys.
   - Test method: regression fixtures for empty bars, duplicate timestamps, adjustment flags, stale data, and provider disagreement.
   - Decision: Backlog; related data-quality work is already open in PR #14.

## Single Highest-Value Market-Logic Idea For Evaluation

Chosen idea: build a Telegram-disabled chronological paper-performance evaluator that replays stored stock scans and public-figure detections, applies spread/slippage/latency/cost assumptions, records net expectancy, precision, average gain/loss, profit factor, drawdown, timing, stability by ticker/figure/regime, and uploads immutable artifacts.

Decision: Backlog/Shadow-test, not applied in this patch. The idea addresses the largest profitability measurement gap, but this run lacks accessible historical artifacts and a local checkout, and open PR #21 already documents the same blocked conclusion. No production strategy change is justified.

## Evaluation Plan For Future Market-Logic Change

- Baseline: current main strategy version at commit 291e135b8912ff4423f8f7bfd0392d631ac0c5df.
- Proposed change: one market-logic idea at a time; initial candidate is evaluator/shadow instrumentation only.
- Development period: historical records before 2026-07-01 UTC if available.
- Untouched holdout: 2026-07-01 through 2026-07-20 UTC, never tuned after viewing results.
- Walk-forward: train/select thresholds only on prior window, evaluate next window, then roll forward without revising past decisions.
- Signal-time rule: use only data available at the original scan/detection time.
- Costs: include realistic spread, slippage, latency delay, and transaction/carry assumptions; do not use best possible fills.
- Success criteria: out-of-sample net expectancy improves after costs, High-confidence precision does not materially decline, drawdown remains acceptable, results are not driven by one ticker/figure/event, negative and ambiguity tests stay silent, dedupe and verification remain intact, all tests pass.
- Failure criteria: small sample, mixed result, weaker precision, higher drawdown, one-name dependence, leakage risk, or any weakened gate.
- Rollback: revert the market-logic PR or keep it shadow-only; preserve all losing and inconclusive results.

## Decision This Run

Apply a reliability fix in draft PR only: restore documented scanner schedules and test assertions. No production market-logic idea was applied. No paper-performance improvement is claimed.

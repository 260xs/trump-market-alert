# Event-Risk Maintenance Report - 2026-07-18

Generated: 2026-07-18 10:05 UTC
Base commit: d86f7146084bb3198c4d01d99cc48a6685097a91
Scope: catalyst calendar, market-regime state, event-risk gates and maintenance report only.
Telegram: disabled/not dispatched for this maintenance run.

## Status

No Telegram market alerts, Telegram tests, broad public-figure discovery, Buy/Sell strategy changes, Short/Hold creation, cron triggers, paid providers or profitability evaluation were performed.

The repository still has no merged event-risk subsystem on `main`. This branch adds a small SQLite-backed event-risk module, a manual-only `workflow_dispatch` maintenance workflow, tests, and this report. The gate code is isolated and does not alter stock strategy scoring.

## Workflow State

Public Actions page showed recent historical scheduled runs from July 16, 2026, including Market-Moving Public Figure Alert #251, Hourly Stock Research Scanner #202, Telegram Test #33 and Stock Candidate Refresh #21. The currently fetched workflow files on `main` are manual-only, so those historical scheduled runs appear to predate the July 16 manual-only commits.

No same event-risk maintenance job was visible as queued or running. A workflow dispatch was not performed from this container because the available GitHub connector does not expose Actions dispatch or logs and direct GitHub API access is blocked by the network proxy.

## Sources Checked

- Federal Reserve FOMC calendar: official .gov source. 2026 FOMC meetings include July 28-29. The page states FOMC minutes are released three weeks after policy decisions.
- BLS 2026 release schedule: official .gov source. The page says all times are Eastern Time and lists Aug. 7 8:30 AM Employment Situation and Aug. 12 8:30 AM CPI.
- BEA release schedule: official .gov source. It lists July 30 8:30 AM GDP (Advance Estimate), Q2 2026, and the page was last modified on 7/18/26.
- EIA Weekly Petroleum Status Report: official .gov source. It lists Release Date July 15, 2026 and Next Release Date July 22, 2026, but no confirmed exact future clock time was stored.
- NYSE hours/holiday calendar: official exchange source. It lists 2026 holidays and states all times are Eastern Time.
- Nokia investor relations events: official company source. It lists report for Q2 and half-year 2026 on 23 July 2026, but no exact release clock time was confirmed on the inspected page.

## Events Added By The New Maintenance Module

- EIA Weekly Petroleum Status Report next release, 2026-07-22 window, `time_confirmed=false`, impact Medium, Energy.
- Nokia Q2 and half-year 2026 financial report, 2026-07-23 window, `time_confirmed=false`, impact High, ticker `NOK`.
- FOMC meeting, July 28-29 2026 window, `time_confirmed=false`, impact High, broad U.S. risk assets.
- BEA GDP advance estimate, Q2 2026, 2026-07-30 12:30 UTC, `time_confirmed=true`, impact High.
- BLS JOLTS, June 2026, 2026-08-04 14:00 UTC, `time_confirmed=true`, impact Medium.
- BLS Employment Situation, July 2026, 2026-08-07 12:30 UTC, `time_confirmed=true`, impact High.
- BLS Consumer Price Index, July 2026, 2026-08-12 12:30 UTC, `time_confirmed=true`, impact High.
- NYSE Labor Day market holiday, 2026-09-07 00:00 UTC date marker, `time_confirmed=true`, impact Medium.

## Events Updated, Cancelled, Unresolved

- Updated in production SQLite: 0. The workflow was not dispatched.
- Cancelled in production SQLite: 0. The workflow was not dispatched.
- Unresolved times preserved as uncertain: EIA July 22 release clock time, Nokia July 23 report clock time, FOMC July 28-29 statement/press-conference clock time until parser confirmation.

## Market Regime

Current stored regime on `main`: not found.

New module behavior: if broad-index trend, volatility, breadth, sector leadership or risk-on/risk-off inputs are stale, unavailable or conflicting, regime is stored as `Uncertain` with data quality `stale_or_incomplete`.

Current run assessment: `Uncertain`; no fresh complete regime input feed was available in this container.

## Risk Gate Behavior

The new gate blocks or marks No Signal when:

- a matching Medium/High impact event has uncertain timing: `event_time_uncertain`
- a matching confirmed earnings event is pending: `earnings_risk`
- a matching corporate action, vote, court or regulatory event is pending: `corporate_action_pending`
- a matching confirmed macro/central-bank/holiday/energy event is pending: `major_event_pending`
- event data is stale or setup levels are incomplete: `event_data_stale`
- regime data is unavailable, stale or `Uncertain`: `market_regime_uncertain`
- a scheduled event better explains a public-figure-attributed move: `competing_catalyst`

Blocked-signal counts in production: unavailable until the manual workflow is dispatched and/or the live scanner imports this module before send.

## Tests Added

Regression coverage added for daylight-saving conversion, market holidays, duplicate events, changed and cancelled event revisions, uncertain timestamps, earnings near a signal, macro releases near a signal, competing-catalyst rejection, stale regime data and one-source failure isolation.

## Rollback

Close the PR or revert the commit adding `.github/workflows/event-risk-maintenance.yml`, `event_risk/`, `scripts/maintain_event_risk.py`, `tests/test_event_risk.py` and `docs/event_risk_report_2026-07-18.md`.

No existing scanner strategy files, Telegram settings, secrets, cron schedules or provider credentials are changed by this branch.

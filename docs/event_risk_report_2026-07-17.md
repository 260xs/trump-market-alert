# Event-Risk Maintenance Report - 2026-07-17

Generated: 2026-07-17 10:20 UTC
Base commit: d86f7146084bb3198c4d01d99cc48a6685097a91
Scope: catalyst calendar, market-regime state, event-risk gates, source coverage, and maintenance blockers only
Telegram: disabled/not dispatched for this maintenance run

## Executive status

No Telegram market alerts, Telegram tests, broad public-figure discovery, Buy/Sell strategy changes, Short/Hold creation, or long-term profitability evaluation were performed.

The repository currently does not contain an implemented catalyst/event calendar, event revision tables, market-regime snapshots, or a wired event-risk gate in `stocks.scanner.hourly_scan`. The scanner can generate and send otherwise actionable Buy/Sell/Short research alerts after stock-rule and dedupe checks, but there is no persisted pre-send gate for scheduled macro/company/corporate-action risk.

Because the exposed GitHub connector in this run did not provide a safe update-existing-file operation or Actions run-list/dispatch capability, this run made a report-only branch and did not attempt a half-wired code change.

## Workflow/run status

Verified from repository files on `main`:

- `.github/workflows/stable-monitor.yml` exists and is `workflow_dispatch`-only.
- `.github/workflows/hourly-stock-scan.yml` exists and is `workflow_dispatch`-only.
- `.github/workflows/stock-candidate-refresh.yml` exists and is `workflow_dispatch`-only.
- `.github/workflows/telegram-test.yml` exists and is `workflow_dispatch`-only.
- `.github/workflows/system-health.yml` exists and is `workflow_dispatch`-only.
- `.github/workflows/workflow-watchdog.yml` exists and is `workflow_dispatch`-only.

Actions run state could not be conclusively verified because direct GitHub clone/API access from the container returned 403 and the available connector did not expose Actions run listing or workflow dispatch. No workflow was dispatched. No duplicate queued/running job could be conclusively confirmed or monitored from this session.

## Repository findings

Verified code and schema surface:

- `stocks/scanner.py` implements stock setup analysis, duplicate checks, and Telegram delivery.
- `stocks/research_db.py` creates `stock_alerts`, `top_candidates`, `stock_scans`, and `active_stock_setups`.
- No `event-risk-refresh.yml` workflow exists on `main`.
- No `docs/event-risk-report.md` exists on `main`.
- No event-calendar, source-cursor, event-revision, market-regime, or risk-gate decision tables were found in the fetched files.
- No implemented event-risk gate was found before Telegram delivery in `hourly_scan`.

Expected but missing for this maintenance scope:

- `event_sources`
- `event_calendar`
- `event_revisions`
- `source_cursors`
- `market_regime_snapshots`
- `risk_gate_decisions`
- `competing_catalyst_checks`
- persisted block reasons such as `major_event_pending`, `event_time_uncertain`, `earnings_risk`, `corporate_action_pending`, `competing_catalyst`, `market_regime_uncertain`, and `event_data_stale`

## Official source checks

| Source | Official status | Compatibility notes | Result |
| --- | --- | --- | --- |
| Federal Reserve FOMC calendar | Official central-bank source | HTML calendar, UTC conversion required from ET | Usable for FOMC meetings, statements, minutes and press conferences |
| Federal Reserve monthly events calendar | Official central-bank source | HTML calendar, event times shown in ET | Usable for speeches, Beige Book and FOMC items |
| BLS release schedules | Official government source | HTML schedules, release times shown in ET | Usable for CPI, PPI, Employment Situation and related releases |
| BEA release schedule | Official government source | HTML schedule, release times shown in ET | Usable for GDP, personal income/outlays and trade releases |
| U.S. Treasury tentative auction schedule | Official government source | PDF and XML links; times may require auction detail pages or TreasuryDirect rules | Usable for dates; exact times require careful confirmation |
| TreasuryDirect auction announcements/results | Official government source | Provides announcement/result detail pages and schedule links | Usable for auction details and duplicate handling |
| NYSE market-hours/holiday calendar | Official exchange source | HTML holiday table | Usable for U.S. equity holiday gates |
| CME holiday/trading-hours calendar | Official exchange source | HTML calendar, product-specific hours | Usable for futures holiday gates; product-specific parser needed |
| EIA Weekly Petroleum Status Report | Official government source | HTML page with release and next release date | Usable for energy inventory dates; exact release time needs source-specific confirmation |
| OPEC press releases | Official producer-organization source | HTML press releases; meeting cadence can be announced in releases | Usable when direct OPEC release exists |
| NVIDIA investor events | Official company IR source | HTML events page | Usable for NVDA company events |
| Nokia investor relations events | Official company IR source | HTML financial calendar | Usable for NOK earnings/financial-report events |
| Netflix investor events | Official company IR source | HTML events page | Usable for NFLX earnings event timestamps |
| UnitedHealth investor page | Official company IR source | HTML investor/news pages | Usable for UNH earnings/result timestamps |

Sources verified in this run:

- Federal Reserve FOMC calendars: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- Federal Reserve July 2026 calendar: https://www.federalreserve.gov/newsevents/2026-july.htm
- BLS Employment Situation schedule: https://www.bls.gov/schedule/news_release/empsit.htm
- BLS current-year release schedule: https://www.bls.gov/schedule/news_release/current_year.asp
- BEA release schedule: https://www.bea.gov/news/schedule
- Treasury tentative auction schedule: https://home.treasury.gov/system/files/221/Tentative-Auction-Schedule.pdf
- TreasuryDirect auctions page: https://www.treasurydirect.gov/auctions/announcements-data-results/
- NYSE hours/holiday calendar: https://www.nyse.com/markets/hours-calendars
- CME holiday/trading-hours calendar: https://www.cmegroup.com/trading-hours.html
- EIA Weekly Petroleum Status Report: https://www.eia.gov/petroleum/supply/weekly/
- OPEC official release: https://www.opec.org/pr-detail/1781604-7-june-2026.html
- NVIDIA IR events: https://investor.nvidia.com/events-and-presentations/events-and-presentations/default.aspx
- Nokia IR events: https://www.nokia.com/about-us/investors/investor-relations-events/
- Netflix IR events: https://ir.netflix.net/investor-news-and-events/investor-events/default.aspx
- UnitedHealth investor page: https://www.unitedhealthgroup.com/investors.html

## Upcoming verified event coverage

Window start: 2026-07-17 10:05 UTC
Priority window: next 72 hours, through 2026-07-20 10:05 UTC
Retention target: next 30 days, through 2026-08-16 10:05 UTC

### Within 72 hours

| UTC time/window | Confirmed | Event | Type | Impact | Affected market/assets | Source |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-07-20, exact auction time not stored by repo | No | 13-week and 26-week U.S. Treasury bill auctions | Treasury auction | Medium | USD rates, Treasuries, broad risk assets | Treasury tentative auction schedule lists announcement 2026-07-16, auction 2026-07-20, settlement 2026-07-23 |

No FOMC rate decision, FOMC minutes, CPI, PPI, Employment Situation, BEA GDP, NYSE market holiday, CME broad market holiday, OPEC meeting, NVIDIA earnings/annual-meeting event, Nokia earnings, Netflix earnings event, or UnitedHealth earnings event was verified inside the 72-hour window.

### Next 30 days, selected high-impact events

| UTC time/window | Confirmed | Event | Type | Impact | Affected market/assets | Source |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-07-22, exact release time not confirmed in repo | No | EIA Weekly Petroleum Status Report next release | Energy inventory | Medium | Oil, energy sector, inflation-sensitive assets | EIA page shows next release date 2026-07-22 |
| 2026-07-22, exact auction time not stored by repo | No | 20-year U.S. Treasury bond reopening auction | Treasury auction | Medium/High | Long-duration Treasuries, rates, growth equities | Treasury tentative auction schedule |
| 2026-07-23, exact company release time not confirmed in source snippet | No | Nokia Q2 and half-year 2026 report | Earnings/company event | High for NOK | NOK | Nokia IR financial calendar |
| 2026-07-23, exact auction time not stored by repo | No | 10-year TIPS auction | Treasury auction | Medium/High | TIPS, real yields, rates-sensitive equities | Treasury tentative auction schedule |
| 2026-07-28 to 2026-07-29, statement expected 2026-07-29 18:00 UTC based Fed calendar 2:00 p.m. ET listing | Yes for date/calendar item; parser should confirm timestamp | FOMC meeting and statement | Central-bank decision | High | USD, rates, equities, gold, crypto | Federal Reserve FOMC calendar and July 2026 Fed calendar |
| 2026-07-29 18:30 UTC | Yes | FOMC press conference | Central-bank press conference | High | USD, rates, equities, gold, crypto | Federal Reserve July 2026 calendar lists 2:30 p.m. ET |
| 2026-07-30 12:30 UTC | Yes | BEA GDP advance estimate, Q2 2026 | Macro release | High | Broad U.S. risk assets, USD, rates | BEA release schedule lists July 30 at 8:30 AM ET |
| 2026-08-04 14:00 UTC | Yes | BLS JOLTS, June 2026 | Labor macro release | Medium | USD, rates, equities | BLS current-year release schedule lists Aug. 4 at 10:00 AM ET |
| 2026-08-07 12:30 UTC | Yes | BLS Employment Situation, July 2026 | Labor macro release | High | Broad U.S. risk assets, USD, rates | BLS Employment Situation schedule lists Aug. 7 at 8:30 AM ET |
| 2026-08-12 12:30 UTC | Yes | BLS CPI, July 2026 | Inflation macro release | High | Broad U.S. risk assets, USD, rates, gold, crypto | BLS current-year release schedule lists Aug. 12 at 8:30 AM ET |
| 2026-08-12, exact time not confirmed by official OPEC source in this run | No | OPEC Monthly Oil Market Report | Energy report | Medium | Oil, energy sector | Official OPEC release checked; future report date was only seen in non-official calendar, so keep unconfirmed until official OPEC page confirms |

## Event changes/cancellations/postponements

No repository event table exists, so no stored event revisions could be compared.

Verified from official-source inspection:

- Added to report-only coverage: Treasury July 20 bill auctions; EIA July 22 next release; Nokia July 23 report; FOMC July 28-29 meeting; FOMC July 29 press conference; BEA July 30 GDP release; BLS Aug. 7 Employment Situation; BLS Aug. 12 CPI.
- Updated in SQLite: 0, because no event-calendar table exists and no workflow was dispatched.
- Cancelled/postponed in SQLite: 0, because no event-calendar table exists.
- Unresolved/uncertain times: Treasury auction exact times in repository calendar, EIA release exact time in repository calendar, Nokia release time, OPEC August report official confirmation.

## Market-regime state

Current stored regime in repository: not found.

Run assessment: `Uncertain`.

Reason: the repository lacks market-regime snapshot storage and this session did not have a complete reliable data feed for broad-index trend, volatility, breadth, sector leadership, and risk-on/risk-off inputs. A partial news/source review showed elevated technology/semiconductor volatility and conflicting sector leadership, but partial inputs are not sufficient for a `Bullish`, `Bearish`, or `Mixed` stored regime. Per rule, stale or incomplete inputs must produce `Uncertain`.

Required future stored inputs:

- broad-index trend with timestamp
- volatility input with timestamp
- breadth input with timestamp
- sector leadership input with timestamp
- risk-on/risk-off input with timestamp
- confidence
- data-quality status
- source URLs/provider identifiers

## Risk-gate behavior

Current implemented blocked-signal count: unavailable; no risk-gate decision table exists.

Expected gate behavior for the verified events above:

- Any high-confidence setup in rates-sensitive assets near the unresolved July 20 Treasury bill auctions should be blocked or marked `No Signal` if exact event timing is unavailable: `event_time_uncertain`.
- Any NOK setup before the verified July 23 Nokia Q2/half-year report should be blocked or marked `No Signal`: `earnings_risk`.
- Any broad-index, rates-sensitive, gold, crypto, or high-duration equity setup before the July 28-29 FOMC decision/press conference should be blocked or marked `No Signal`: `major_event_pending`.
- Any broad U.S. equity, USD, rates, gold, or crypto setup before the July 30 GDP release, Aug. 7 Employment Situation, or Aug. 12 CPI should be blocked when the event window overlaps the configured risk window: `major_event_pending`.
- Any public-figure impact attribution should be rejected when a scheduled release, earnings event, filing, or regulatory/company announcement is a better competing catalyst: `competing_catalyst`.
- If the future calendar refresh fails or becomes stale, otherwise actionable setups should be blocked or marked `No Signal`: `event_data_stale`.
- If market-regime inputs remain unavailable/stale/conflicting, otherwise actionable setups should be blocked or marked `No Signal`: `market_regime_uncertain`.

Blocked setup counts from this run:

```json
{
  "major_event_pending": null,
  "event_time_uncertain": null,
  "earnings_risk": null,
  "corporate_action_pending": null,
  "competing_catalyst": null,
  "market_regime_uncertain": null,
  "event_data_stale": null,
  "reason_counts_available": false
}
```

## Tests and dry run

Tests run in this session: none.

Reason: the repository was not locally cloneable from this container due outbound GitHub access returning 403, and the available connector could read files but did not provide a full checkout. No Telegram-enabled workflow or dry run was dispatched. No Telegram setup test or market alert was sent.

Regression tests that should be added with the eventual code change:

- daylight-saving conversion for ET to UTC
- market holiday gate
- duplicate events
- changed event times and event revisions
- cancelled events
- uncertain timestamps remain unconfirmed and block setups
- earnings near a signal blocks setup
- macro release near a signal blocks setup
- competing-catalyst rejection for public-figure attribution
- stale regime data produces `Uncertain`
- one-source failure isolation

## Confirmed defects/gaps

1. Catalyst/event calendar storage is not implemented.
2. Historical event revisions are not implemented.
3. Source cursor storage and duplicate-event handling are not implemented.
4. Market-regime snapshots are not implemented.
5. Event-risk gate decisions and block reasons are not implemented.
6. `stocks.scanner.hourly_scan` is not wired to a pre-send event-risk gate.
7. Public-figure impact attribution does not appear to have a persisted competing-catalyst check in the fetched files.
8. Actions run listing and workflow dispatch could not be performed with available tools in this session.

## Rollback

This report-only branch can be rolled back by closing the PR or deleting this file:

- `docs/event_risk_report_2026-07-17.md`

No scanner code, strategy rules, workflows, secrets, Telegram configuration, provider dependencies, or cron schedules were changed.

## Recommended next implementation step

Add a manual-only, Telegram-disabled event-risk maintenance workflow and a small SQLite-backed event-risk module. Keep the first PR unmerged for review if it introduces new providers or uncertain event rules. The minimum code change should:

1. create event/source/regime/risk-gate tables in SQLite using UTC timestamps;
2. collect only official-source events with confirmed vs uncertain time handling;
3. preserve event revisions and source cursors;
4. compute `Bullish`, `Bearish`, `Mixed`, or `Uncertain` regime snapshots;
5. gate `stocks.scanner.hourly_scan` immediately before Telegram delivery without changing setup scoring;
6. store exact block reasons and suppress Telegram for blocked setups;
7. add the regression tests listed above;
8. run a Telegram-disabled dry run and compare blocked-signal behavior before merge.
# Automation Backlog

Updated: 2026-08-02

## Purpose

This is the authoritative, concise handoff for the scheduled research/improvement and stability runs. It records only work supported by current repository evidence. Do not create a new PR when a listed draft already contains the same idea; first re-evaluate the current `main` implementation.

## Current Direction

- Keep the three production scanner schedules enabled:
  - public figures: `7,27,47 * * * *`
  - hourly stocks: `13 * * * *`
  - candidate refresh: `31 6 */3 * *`
- Keep Telegram quiet: scheduled scans may send only qualifying market alerts; workflow-failure messages remain opt-in through `ENABLE_WORKFLOW_FAILURE_TELEGRAM=true`.
- Keep the Telegram setup test manual-only and limited to its exact test message.
- Prefer direct, tested commits to `main`; do not grow the draft-PR backlog.

## Open PR Reconciliation

### Superseded or contradictory

- #35 and #26: manual-dispatch-only workflow changes contradict the restored scheduled MVP on `main`.
- #33: superseded by #34.
- #24: the scanner schedule restoration is already represented by current `main`.
- #23, #19, #18, and #2: their manual/failure-message policy changes are superseded by the current scheduled workflows with opt-in failure alerts.

### Report-only or archive value

- #4, #5, #6, #7, #8, #12, #13, #16, #17, #20, #21, #27, #28, #31, and #32 are dated coverage, data-quality, missed-opportunity, or paper-performance reports. They must not be applied as recurring production work. Preserve their conclusions through this backlog and re-run only when new evidence is available.
- #34 is a shadow-only coverage registry. Keep it separate from production watchlists until source ownership, cursors, dedupe, and parser behavior are validated.

### Keep for focused re-evaluation

- #9: Telegram-error redaction and workflow-test work. Re-evaluate only against current delivery code and tests; do not apply its stale workflow policy wholesale.
- #10: provider-candle validation. Re-evaluate as a focused stability fix if current data validation lacks equivalent coverage.
- #22: ticker ambiguity precedence. Re-evaluate with current mapper tests before applying; preserve conservative ambiguity blocking.
- #25: event-risk foundation. Keep as a larger future research item, not a weekly-maintenance change.
- #29: stock model-view vocabulary. Current configuration is already intentionally Buy/Sell-only for Telegram; do not apply without checking current scanner behavior and policy tests.
- #30: stock-universe/data-quality foundation. Keep for a dedicated, test-backed maintenance run; it overlaps #14.
- #11 and #14: superseded by the later #25 and #30 foundations respectively.

## Ranked Next Tasks

1. Add a Telegram-disabled, manual dry-run workflow that emits scanner decisions and artifacts without dispatching alerts. This unblocks safe investigation of failures and candidate quality.
2. Audit ticker-mapper ambiguity behavior against #22's regression cases, then make only a focused, test-backed correction if current `main` is missing it.
3. Review provider-candle validation and stock-universe quality from #10/#30; select one narrow data-integrity gap with a targeted test before implementation.

## Evidence Gaps

- This scheduled steward has repository, PR, commit, workflow-file, and issue-search access, but no GitHub Actions run-list/log/artifact/dispatch endpoint. Do not claim a workflow passed, failed, or sent Telegram without direct run evidence.
- No Telegram message is sent by backlog maintenance.

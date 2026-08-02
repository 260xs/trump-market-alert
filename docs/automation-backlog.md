# Automation Backlog and PR Stewardship

Updated: 2026-08-02 UTC
Repository: `260xs/trump-market-alert`
Canonical branch: `main`
Evidence baseline: `e25bf3c72ac646cf4ff8abd017d39b108b110332`

## Operating direction

- Keep the scheduled GitHub Actions MVP active for public-figure scans, hourly stock scans, and the three-day candidate refresh.
- Keep `telegram-test.yml` manual-only and keep workflow-failure Telegram delivery opt-in.
- Do not send routine Telegram messages during maintenance.
- Do not reopen stale PR branches when the useful result is already on `main`.
- Prefer one focused, validated change over dated report-only PRs or parallel foundations.
- Preserve strict alert gates, dedupe, asset ambiguity suppression, public-source restrictions, and no-trading boundaries.

## PR dispositions

### Superseded or duplicate

- #35: manual-dispatch-only operations conflicts with the current scheduled MVP and is superseded by the restored schedules on `main`.
- #24: schedule restoration is already present on `main`; superseded.
- #26, #23, #19, #18, #9: workflow quieting and opt-in failure-alert changes are represented by later `main` commits; superseded.
- #22: ambiguous ticker precedence repair is represented by recent `main` commits; superseded.
- #29: stock model-view narrowing is represented by current `main` policy/docs; superseded unless a focused regression gap is demonstrated.
- #33: duplicate of the newer shadow worldwide coverage registry PR #34; superseded.
- #28, #17, #13, #8, #4: dated public-figure coverage reports are superseded by the latest shadow registry direction in #34.
- #27, #21, #16, #12, #7: repeated dated paper-performance reports; preserve the conclusion, but do not create another dated report PR until a reproducible evaluator exists.
- #20: older missed-opportunity audit; superseded by the newer audit record in #31.

### Keep for later, blocked on integration or validation

- #25: event-risk foundation. Keep as research input only until a small integration patch can be tested against the existing stock-alert gate without changing Telegram volume.
- #30: stock-universe/data-quality foundation. Keep as research input only; provider-backed refresh and Actions artifact evidence are still required before integration.
- #14: older stock-universe/data-quality foundation; superseded by #30.
- #11: older event-risk foundation; superseded by the more complete #25.
- #34: shadow-only worldwide coverage registry. Keep only if it remains useful after consolidation; candidates must stay non-active until source ownership, parsing, cursor, entity mapping, and dedupe behavior are validated.
- #31: latest missed-opportunity audit. Keep as the current report reference, but do not repeat daily report-only PRs without new evidence.
- #32: latest paper-performance audit. Keep as the current evidence reference, but do not claim profitability or usefulness without reproducible paper-performance data.

## Top three next actions

1. **Stability run:** verify the scheduled workflow regression suite and inspect the next available Actions outcomes; repair only a confirmed failure.
2. **Research/improvement run:** design the smallest Telegram-disabled paper-performance evaluator that writes reproducible result tables/artifacts, then add focused tests before any production use.
3. **Research/improvement run:** evaluate a minimal event-risk integration point for the existing stock-alert gate using the #25 tests and preserving all current entry/exit, confidence, risk/reward, and dedupe gates.

## Backlog rules for future runs

- One active PR per improvement topic.
- A report-only result should be committed directly only when it is the current durable evidence needed by another run.
- If a newer PR or `main` already contains the result, comment the evidence and close/supersede the older PR when repository tooling permits.
- Do not activate shadow people, broaden sources, add cron, enable routine Telegram, or weaken any gate based only on a report or candidate list.
- Do not require Memory for startup, execution, validation, or reporting.

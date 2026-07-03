# Operations Reliability Research

Updated: 2026-07-03

## What changed now

- Daily Telegram heartbeat is enabled in `.github/workflows/telegram-test.yml`.
- It runs at `5 13 * * *`, which is 13:05 UTC and avoids the busiest top-of-hour GitHub Actions window.
- It still sends exactly `✅ Telegram test successful` and nothing else.
- The public scanner, hourly stock scanner, and candidate refresh remain strict and quiet.
- Workflow failure Telegram alerts remain opt-in through `ENABLE_WORKFLOW_FAILURE_TELEGRAM=true`.

## Research findings

GitHub Actions scheduled workflows are useful for the MVP, but they are best-effort. GitHub documents that scheduled workflows may be delayed during high-load periods, especially near the start of each hour, and in high-load cases queued jobs may be dropped. That means GitHub Actions is good enough for a low-cost MVP heartbeat and scheduled checks, but it is not a true 24/7 guarantee.

Telegram bot delivery should continue to use the official Bot API `sendMessage` endpoint with repository secrets for `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Secrets should only be passed to the workflow steps that need them.

GitHub repository secrets are the right place for Telegram values. Repository variables are better for non-secret feature flags such as enabling workflow failure alerts.

## Manual GitHub settings to check

Required repository secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Optional repository variables:

- `ENABLE_WORKFLOW_FAILURE_TELEGRAM=true` only if you want Telegram messages when a workflow fails.
- `ENABLE_LIVE_AUDIO=false` unless intentionally testing the heavier live audio path.
- `ENABLE_PROVISIONAL_LIVE_ALERTS=false` unless live audio is intentionally enabled and tested.

## Recommended next upgrades

1. Add a lightweight status artifact or database row from each scheduled run so the Telegram command center can report the last successful GitHub Actions run, not only local runner state.
2. Add a weekly non-Telegram CI workflow that runs tests and dependency checks so operational scans stay separate from validation.
3. Add source-health counters per public source so repeated fetch failures are visible without sending Telegram noise.
4. Add a manual `dry-run` workflow for stock and public scanners that never sends Telegram and prints decisions for debugging.
5. Keep the always-on runner path as the future reliability upgrade for true 24/7 monitoring.

## Sources

- GitHub Actions schedule event docs: https://docs.github.com/actions/using-workflows/events-that-trigger-workflows
- GitHub Actions secrets docs: https://docs.github.com/actions/security-guides/using-secrets-in-github-actions
- GitHub Actions variables docs: https://docs.github.com/actions/learn-github-actions/variables
- Telegram Bot API docs: https://core.telegram.org/bots/api

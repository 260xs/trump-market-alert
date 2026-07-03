# Operations Reliability Research

Updated: 2026-07-03

## What changed now

- Daily Telegram heartbeat is enabled in `.github/workflows/telegram-test.yml`.
- It runs at `5 13 * * *`, which is 13:05 UTC and avoids the busiest top-of-hour GitHub Actions window.
- It sends exactly `✅ Telegram test successful` and nothing else.
- Daily system health checks are enabled in `.github/workflows/system-health.yml` at `37 4 * * *`.
- Daily GitHub Actions watchdog checks are enabled in `.github/workflows/workflow-watchdog.yml` at `25 13 * * *`.
- The watchdog reviews important workflow runs from the last 24 hours and sends one grouped Telegram alert if any failed.
- The public scanner, hourly stock scanner, and candidate refresh remain strict and quiet.

## Research findings

GitHub Actions scheduled workflows are useful for the MVP, but they are best-effort. GitHub documents that scheduled workflows may be delayed during high-load periods, especially near the start of each hour, and in high-load cases queued jobs may be dropped. That means GitHub Actions is good enough for a low-cost MVP heartbeat and scheduled checks, but it is not a true 24/7 guarantee.

Telegram bot delivery should continue to use the official Bot API `sendMessage` endpoint with repository secrets for `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Secrets should only be passed to the workflow steps that need them.

Comparable open-source and community market alert systems usually fall into four buckets:

1. Telegram stock analysis bots that combine technical indicators, news sentiment, and fundamentals.
2. Crypto/market scanner bots that reduce noise with multi-factor filters like RSI, MACD, volume, and support/resistance.
3. Macro/news alert bots that emphasize fast source aggregation and strict filtering before notification.
4. Prediction-market and trading bots that add automation, but often cross into execution or speculative trading.

The best ideas to copy for this repo are operational, not speculative: heartbeat checks, grouped failure alerts, multi-factor gates, source-health tracking, dry-run workflows, and stronger dedupe. The ideas to avoid are broker connections, auto-trading, vague AI recommendations, and noisy summaries.

## Automatic workflows now enabled

- `stable-monitor.yml`: public-figure scanner at `7,27,47 * * * *`.
- `hourly-stock-scan.yml`: stock scanner at `13 * * * *`.
- `stock-candidate-refresh.yml`: silent candidate refresh at `31 6 */3 * *`.
- `telegram-test.yml`: daily Telegram heartbeat at `5 13 * * *`.
- `system-health.yml`: daily imports, dependency checks, and tests at `37 4 * * *`.
- `workflow-watchdog.yml`: daily recent-failure watchdog at `25 13 * * *`.

## Secrets and variables

Required repository secrets for Telegram delivery:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

The automation is committed in the repository. If those secrets already exist, no manual GitHub changes are needed. If they do not exist, GitHub Actions cannot send Telegram because secrets cannot be safely generated or guessed from code.

Optional repository variables:

- `ENABLE_WORKFLOW_FAILURE_TELEGRAM=true` can still enable immediate per-workflow failure alerts, but the watchdog now provides automatic daily grouped failure reporting without requiring that variable.
- `ENABLE_LIVE_AUDIO=false` unless intentionally testing the heavier live audio path.
- `ENABLE_PROVISIONAL_LIVE_ALERTS=false` unless live audio is intentionally enabled and tested.

## Recommended next upgrades

1. Add source-health counters per public source so repeated fetch failures are visible without sending Telegram noise.
2. Add a manual `dry-run` workflow for stock and public scanners that never sends Telegram and prints decisions for debugging.
3. Add a status artifact from each scheduled run so the Telegram command center can report the last successful GitHub Actions run.
4. Add richer stock candidate scoring inputs such as earnings calendar proximity, sector ETF trend, and market breadth while keeping Telegram alerts strict.
5. Keep the always-on runner path as the future reliability upgrade for true 24/7 monitoring.

## Sources

- GitHub Actions schedule event docs: https://docs.github.com/actions/using-workflows/events-that-trigger-workflows
- GitHub Actions secrets docs: https://docs.github.com/actions/security-guides/using-secrets-in-github-actions
- GitHub Actions variables docs: https://docs.github.com/actions/learn-github-actions/variables
- Telegram Bot API docs: https://core.telegram.org/bots/api
- GitHub search, Reddit search, and public project scan for stock/news/crypto Telegram alert bots and market scanners.

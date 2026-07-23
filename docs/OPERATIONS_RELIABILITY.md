# Operations Reliability Research

Updated: 2026-07-23

## What changed now

- Operational GitHub Actions workflows are manual-dispatch-only.
- `.github/workflows/stable-monitor.yml`, `.github/workflows/hourly-stock-scan.yml`, `.github/workflows/stock-candidate-refresh.yml`, `.github/workflows/manual-run-all.yml`, `.github/workflows/system-health.yml`, `.github/workflows/workflow-watchdog.yml`, and `.github/workflows/telegram-test.yml` all keep `workflow_dispatch` and do not define cron schedules.
- Routine Telegram health messages and workflow-failure Telegram messages are disabled.
- `.github/workflows/telegram-test.yml` remains the only setup-test workflow and sends exactly `✅ Telegram test successful` when intentionally run.
- Scanner workflows remain strict and quiet unless a real alert gate passes.

## Research findings

GitHub Actions scheduled workflows are useful for a low-cost MVP, but they are best-effort. GitHub documents that scheduled workflows may be delayed during high-load periods, especially near the start of each hour, and in high-load cases queued jobs may be dropped. For the current operating mode, manual `workflow_dispatch` avoids unintended cron-triggered scans and makes each operational run attributable to an explicit request.

Telegram bot delivery should continue to use the official Bot API `sendMessage` endpoint with repository secrets for `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Secrets should only be passed to the workflow steps that need them. Routine health, watchdog, audit, research, and shadow workflows should not send Telegram messages.

Comparable open-source and community market alert systems usually fall into four buckets:

1. Telegram stock analysis bots that combine technical indicators, news sentiment, and fundamentals.
2. Crypto/market scanner bots that reduce noise with multi-factor filters like RSI, MACD, volume, and support/resistance.
3. Macro/news alert bots that emphasize fast source aggregation and strict filtering before notification.
4. Prediction-market and trading bots that add automation, but often cross into execution or speculative trading.

The best ideas to copy for this repo are operational, not speculative: explicit manual dispatches, source-health tracking, grouped non-Telegram audit output, multi-factor gates, dry-run workflows, and stronger dedupe. The ideas to avoid are broker connections, auto-trading, vague AI recommendations, and noisy summaries.

## Manual workflows now enabled

- `stable-monitor.yml`: public-figure scanner, manual dispatch only.
- `hourly-stock-scan.yml`: stock scanner, manual dispatch only.
- `stock-candidate-refresh.yml`: silent candidate refresh, manual dispatch only.
- `manual-run-all.yml`: selected scanners, manual dispatch only.
- `system-health.yml`: imports, dependency checks, and tests, manual dispatch only.
- `workflow-watchdog.yml`: recent workflow-failure audit, manual dispatch only, no Telegram.
- `telegram-test.yml`: manual-only setup test.

## Secrets and variables

Required repository secrets for Telegram delivery:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

The scanner workflows can use those secrets only for qualifying market alerts or the explicit Telegram setup test. If those secrets do not exist, GitHub Actions cannot send Telegram because secrets cannot be safely generated or guessed from code.

Optional repository variables:

- `ENABLE_LIVE_AUDIO=false` unless intentionally testing the heavier live audio path.
- `ENABLE_PROVISIONAL_LIVE_ALERTS=false` unless live audio is intentionally enabled and tested.

## Recommended next upgrades

1. Add source-health counters per public source so repeated fetch failures are visible without sending Telegram noise.
2. Add a manual dry-run workflow for stock and public scanners that never sends Telegram and prints decisions for debugging.
3. Add a status artifact from each manual run so the Telegram command center can report the last verified GitHub Actions run.
4. Add richer stock candidate scoring inputs such as earnings calendar proximity, sector ETF trend, and market breadth while keeping Telegram alerts strict.
5. Keep the always-on runner path as the future reliability upgrade for true 24/7 monitoring.

## Sources

- GitHub Actions schedule event docs: https://docs.github.com/actions/using-workflows/events-that-trigger-workflows
- GitHub Actions secrets docs: https://docs.github.com/actions/security-guides/using-secrets-in-github-actions
- GitHub Actions variables docs: https://docs.github.com/actions/learn-github-actions/variables
- Telegram Bot API docs: https://core.telegram.org/bots/api
- GitHub search, Reddit search, and public project scan for stock/news/crypto Telegram alert bots and market scanners.

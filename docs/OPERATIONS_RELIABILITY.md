# Operations Reliability Research

Updated: 2026-07-18

## Current operating mode

- Operational GitHub Actions workflows are `workflow_dispatch` only.
- No cron schedules should be added by the maintenance audit automation.
- The public scanner, hourly stock scanner, and candidate refresh remain strict and quiet.
- The Telegram test workflow sends exactly `✅ Telegram test successful` only when manually dispatched.
- Workflow failure Telegram alerts are opt-in through `ENABLE_WORKFLOW_FAILURE_TELEGRAM=true`.

## Workflows

- `stable-monitor.yml`: manual public-figure scanner.
- `hourly-stock-scan.yml`: manual stock scanner.
- `stock-candidate-refresh.yml`: manual silent candidate refresh.
- `telegram-test.yml`: manual Telegram setup test.
- `system-health.yml`: manual imports, dependency checks, and tests.
- `workflow-watchdog.yml`: manual recent-failure watchdog.
- `manual-run-all.yml`: manual selected scanner runner.

## Secrets and variables

Required repository secrets for Telegram delivery:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Optional repository secrets:

- `X_BEARER_TOKEN`
- `DISCORD_WEBHOOK_URL`
- `HEALTHCHECKS_URL`

Optional repository variables:

- `ENABLE_WORKFLOW_FAILURE_TELEGRAM=true` enables workflow-failure Telegram alerts.
- `ENABLE_LIVE_AUDIO=false` unless intentionally testing the heavier live audio path.
- `ENABLE_PROVISIONAL_LIVE_ALERTS=false` unless live audio is intentionally enabled and tested.

## Audit findings from 2026-07-18

- Recent public Actions evidence showed a failed System Health Check run on July 16, 2026 because tests still expected cron schedules.
- Workflow files reviewed in this audit use minimum permissions: `contents: read`, with `actions: read` only for the watchdog.
- Workflows use fixed concurrency groups with `cancel-in-progress: false`.
- Workflow action usage is limited to trusted GitHub-owned actions pinned to major versions.
- Telegram secrets are referenced through GitHub Secrets/environment variables, not hardcoded values.
- Production Telegram was not contacted during this audit.
- Telegram delivery now redacts bot token and chat ID values from retry-exhaustion errors.
- Dependency manifests were reviewed; no broad dependency upgrades were made without a compatibility-verified vulnerability fix.
- No production SQLite history was deleted or rewritten.

## Recommended next upgrades

1. Add a manual `dry-run` workflow for stock and public scanners that never sends Telegram and prints decisions for debugging.
2. Add source-health counters per public source so repeated fetch failures are visible without sending Telegram noise.
3. Add a status artifact from each run so operational health can be checked without triggering alerts.
4. Add explicit SQLite backup/restore test coverage for cache recovery and idempotent reruns.
5. Keep the always-on runner path as the future reliability upgrade for true 24/7 monitoring.

## Sources

- GitHub Actions schedule event docs: https://docs.github.com/actions/using-workflows/events-that-trigger-workflows
- GitHub Actions secrets docs: https://docs.github.com/actions/security-guides/using-secrets-in-github-actions
- GitHub Actions variables docs: https://docs.github.com/actions/learn-github-actions/variables
- Telegram Bot API docs: https://core.telegram.org/bots/api

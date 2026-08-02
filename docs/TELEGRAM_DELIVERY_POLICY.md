# Telegram Delivery Policy

## Purpose

Telegram is an alert-only delivery channel. Scheduled scans, successful health checks, candidate refreshes, neutral statements, low-confidence detections, and duplicate setups must remain silent.

This policy describes the behavior enforced by the current GitHub Actions workflows and alert gates. It is the canonical operations reference when older audit material conflicts with the running workflow files.

## Allowed messages

Only the following message types may be sent:

1. The manual setup test in `.github/workflows/telegram-test.yml`, with exactly:

   ```text
   ✅ Telegram test successful
   ```

2. High-confidence public-figure alerts that pass every strict public-source, directness, confidence, asset-mapping, and duplicate gate.

3. Live provisional public-figure alerts only when live mode is intentionally enabled. They must use the required provisional format and never be presented as fully verified.

4. Medium- or high-confidence stock research setups with a `Buy`, `Sell`, or `Short` model view only when the configured entry/trigger, invalidation, risk/reward, and duplicate gates pass. The current stock configuration is stricter: it sends only high-confidence `Buy` or `Sell` alerts and disables `Short`.

5. Workflow-failure alerts only when the repository variable `ENABLE_WORKFLOW_FAILURE_TELEGRAM` is explicitly set to `true`.

## Scheduled workflow behavior

The public-figure monitor, hourly stock scan, stock candidate refresh, system health check, and workflow watchdog are scheduled GitHub Actions workflows. GitHub Actions schedules are best effort and may be delayed.

The daily system health workflow runs imports, dependency checks, and tests. A successful health run sends no Telegram message. Its failure notification is opt-in through `ENABLE_WORKFLOW_FAILURE_TELEGRAM=true`.

The workflow watchdog reads recent failures and can send one grouped failure message only when the same opt-in variable is enabled. It is not a routine heartbeat.

## Operator safeguards

- Keep `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in GitHub Secrets only.
- Do not enable workflow-failure Telegram messages unless prompt operational-failure notification is intended.
- Use the manual Telegram test only for intentional setup validation.
- Do not treat an absent routine Telegram message as a failed scan; inspect the relevant GitHub Actions run instead.
- Do not add success heartbeats, scan summaries, candidate lists, `Hold` messages, neutral mentions, or unverified statements to Telegram.

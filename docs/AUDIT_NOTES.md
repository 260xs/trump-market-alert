# Senior Audit Notes

Updated: 2026-07-18

## Current health report

- Workflow status: recent public Actions evidence showed successful scheduled runs for the public scanner, stock scanner, watchdog and Telegram test on July 16, 2026, plus a failed System Health Check run #13 at `https://github.com/260xs/trump-market-alert/actions/runs/29478622867`.
- Repeated failures: System Health was failing because workflow tests still expected cron schedules after operational workflows were changed to `workflow_dispatch` only.
- Workflow permissions: operational workflows reviewed in this audit use minimum read-only contents permissions; the watchdog additionally uses `actions: read`.
- Workflow concurrency: operational workflows use fixed concurrency groups with `cancel-in-progress: false`, preventing overlapping duplicate runs without interrupting in-flight work.
- Third-party actions: reviewed workflow files use trusted GitHub-owned actions `actions/checkout@v6`, `actions/setup-python@v6`, `actions/cache/restore@v5`, and `actions/cache/save@v5`.
- Telegram configuration status: workflows reference `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` only through GitHub Secrets/environment variables. No Telegram test was sent during this audit.
- Telegram reliability finding: failed Telegram HTTP errors could include the Bot API URL in exception text, which may expose the bot token in logs. This audit adds error redaction before retry exhaustion is raised.
- Dependency/security findings: dependency manifests were reviewed; no broad upgrades were made because no compatibility-verified vulnerability fix was proven in this audit.
- Database integrity and recovery: no production database was downloaded, deleted, or rewritten. SQLite cache paths and save/restore workflow behavior were reviewed from workflow files only.
- Stale locks/cursors: no repository evidence of stale lock or orphaned cursor files was found in this audit.
- Secrets exposure scan: code search for Telegram secret names found only expected GitHub Secret/environment references and documentation placeholders; no secret values were printed or found.
- Unresolved risk: the container could not install pytest or clone the repository because outbound package/GitHub network access was blocked, so full-suite validation is left to GitHub Actions on the pull request.

## Changes from this audit

- Updated workflow tests so they verify the current manual-only `workflow_dispatch` operating mode and continue to reject accidental cron reintroduction.
- Guarded `manual-run-all.yml` failure Telegram alerts behind `ENABLE_WORKFLOW_FAILURE_TELEGRAM`, matching the other operational workflows.
- Added a Telegram redaction regression test for failed sends.

## Rollback

Revert the pull request from this audit to restore the prior test expectations, manual-run failure-alert behavior, and Telegram error formatting.

## Recommended next action

Review and merge the focused reliability/security pull request after GitHub Actions completes successfully.

## Historical notes

This package was rebuilt after a full code review. Earlier reliability work:

- Removed generated `__pycache__` and `.pytest_cache` artifacts from the release package.
- Kept GitHub Actions as the current low-cost MVP path, with the always-on runner documented as the more reliable future path.
- Kept the public-figure scanner strict: Telegram sends only for direct, high-confidence Good/Bad statements with clear ticker mapping.
- Kept the stock scanner quiet unless a Medium/High confidence Buy, Sell, or Short setup exists.
- Added an old-statement guard so a fresh database does not alert on stale posts.
- Fixed public-alert dedupe so a failed Telegram send does not permanently suppress the same alert.
- Fixed stock-alert dedupe so an actionable setup is recorded only after Telegram delivery succeeds.
- Added similar-quote alert dedupe to reduce repeated Telegram messages from reposts and repeated clips.
- Made partial source failures non-fatal unless every source fails or Telegram delivery fails.
- Added Telegram retry logic and message truncation to avoid Telegram API length failures.
- Added stock data availability checks so the stock workflow fails if market data is unavailable for all tickers.
- Added always-on runner healthcheck hooks for public, stock, and candidate jobs.
- Removed pytest from production dependencies and moved it to `requirements-dev.txt`.

Remaining platform limitation:

GitHub Actions workflow dispatch runs are manual and scheduled workflows are best-effort when enabled. For true 24/7 monitoring, run `always_on_runner.py` on an always-on VM or a PC running 24/7.

See also `docs/OPERATIONS_RELIABILITY.md` for operations guidance and next improvements.

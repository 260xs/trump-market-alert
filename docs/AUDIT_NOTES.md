# Senior Audit Notes

This package was rebuilt after a full code review. The highest-impact fixes are:

- Removed generated `__pycache__` and `.pytest_cache` artifacts from the release package.
- Kept the public-figure scanner on a 20-minute schedule: `:07`, `:27`, `:47`.
- Kept the stock scanner hourly and silent unless a Medium/High confidence Buy, Sell, or Short setup exists.
- Added an old-statement guard so a fresh database does not alert on stale posts.
- Fixed public-alert dedupe so a failed Telegram send does not permanently suppress the same alert.
- Added similar-quote alert dedupe to reduce repeated Telegram messages from reposts and repeated clips.
- Made partial source failures non-fatal unless every source fails or Telegram delivery fails.
- Added Telegram retry logic and message truncation to avoid Telegram API length failures.
- Added stock data availability checks so the stock workflow fails if market data is unavailable for all tickers.
- Removed pytest from production dependencies and moved it to `requirements-dev.txt`.

Remaining platform limitation:

GitHub scheduled workflows are best-effort. They can be delayed or dropped under platform load. For better consistency, use the included `workflow_dispatch` support with cron-job.org and Healthchecks.

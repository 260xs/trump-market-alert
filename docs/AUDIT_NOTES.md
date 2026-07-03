# Senior Audit Notes

This package was rebuilt after a full code review. The highest-impact fixes are:

- Removed generated `__pycache__` and `.pytest_cache` artifacts from the release package.
- Kept GitHub Actions scheduled monitoring as the current low-cost MVP path, with the always-on runner documented as the more reliable future path.
- Enabled a daily Telegram heartbeat workflow that sends exactly `✅ Telegram test successful`.
- Kept the public-figure scanner strict: Telegram sends only for direct, high-confidence Good/Bad statements with clear ticker mapping.
- Kept the stock scanner hourly and silent unless a Medium/High confidence Buy, Sell, or Short setup exists.
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

GitHub scheduled workflows are best-effort and may be delayed or dropped during high-load periods. For better consistency than GitHub Actions schedules, run `always_on_runner.py` on an always-on VM or a PC running 24/7.

See also `docs/OPERATIONS_RELIABILITY.md` for current operations guidance and next improvements.

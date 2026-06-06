# Market-Moving Public Figure + Short-Term Stock Alert System

This project has two independent scanners.

1. **Public-figure alert scanner** - watches configured market-moving public figures and sends Telegram only for direct, high-confidence Good/Bad statements about tradable assets. The preferred 24/7 deployment is the always-on runner in `always_on_runner.py`, not GitHub scheduled workflows.
2. **Short-term stock scanner** - checks priority stocks hourly, especially **NVDA** and **NOK**, and sends Telegram only when there is a clean Medium/High confidence entry, exit/risk, or short setup.

This is **not** a trading bot. It does not buy, sell, short, hold, or place trades. Alerts are research signals only.

## Public figures currently enabled

The enabled watchlist lives in:

```text
watchlist.yaml
```

Current enabled market movers:

```text
Donald J. Trump
Kevin Warsh
Scott Bessent
Elon Musk
Jensen Huang
```

Public-figure Telegram wording:

```text
Good = strong positive direct statement
Bad = strong negative direct statement
```

No Telegram alert is sent for neutral statements, vague mentions, inferred-only topics, unclear ticker mapping, or low-confidence quotes.

## Stock scanner behavior

Stock config lives in:

```text
config/stocks.yaml
```

Priority stocks:

```text
NVDA
NOK
```

The stock scanner is strict. Telegram is silent unless all of these are true:

```text
Setup type is Entry or Exit/Risk
Signal is Good or Bad
Model view is Buy, Sell, or Short
Confidence is High or Medium
Trigger level exists
Exit/invalidation level exists
Duplicate protection passed
Telegram delivery succeeds
```

The stock scanner does **not** send:

```text
Neutral summaries
Weak setups
Low-confidence setups
Repeated duplicate setups
Candidate refresh lists by default
```

Short-term focus:

```text
1 week to 3 months
```

## Telegram Command Center

The always-on runner includes a free private Telegram command menu. It uses the same `TELEGRAM_BOT_TOKEN` and only responds to the configured `TELEGRAM_CHAT_ID`.

Enable or disable it with:

```text
RUNNER_ENABLE_TELEGRAM_COMMANDS=true
```

Available commands:

```text
/status - runner, last runs, and pause state
/last_alert - latest public or stock alert
/last_public - latest public-figure alert
/last_stock - latest stock setup alert
/run_public_now - run the public scanner once
/run_stock_now - run the stock scanner once
/pause - pause scheduled runner jobs
/resume - resume scheduled runner jobs
/menu - show the command menu
```

Telegram commands cannot trade, connect to a broker, show secrets, change secrets, bypass public-source rules, or loosen alert thresholds.

## Stock alert meanings

Entry setup:

```text
Signal: Good
Model view: Buy
Meaning: Rule-based short-term entry setup.
Includes: entry trigger, exit/invalidation level, target, confidence, reason.
```

Exit/risk setup:

```text
Signal: Bad
Model view: Sell
Meaning: Rule-based short-term risk or exit setup.
Includes: exit/risk trigger, invalidation/recovery level, downside reference, confidence, reason.
```

Short setup:

```text
Signal: Bad
Model view: Short
Meaning: Rule-based confirmed breakdown setup.
Includes: short/risk trigger, invalidation/recovery level, downside reference, confidence, reason.
```

Hold:

```text
Model view: Hold
Meaning: No clear setup. Telegram stays silent.
```

These are mechanical technical research labels, not personal investment advice or instructions to trade.

## Always-On Runner

Use this for reliable monitoring instead of GitHub scheduled workflows:

```bash
python always_on_runner.py
```

Default cadence:

```text
Public-figure scanner: every 5 minutes
Stock scanner: every 60 minutes
Candidate refresh: every 3 days
```

Deployment files live in:

```text
deploy/market-alert.service
deploy/market-alert.env.example
deploy/README.md
```

The recommended host is an Oracle Cloud Always Free VM, a small VPS, or a PC/Mac that never sleeps. Free tiers that sleep are not true 24/7.

## Healthchecks

Optional healthcheck environment values:

```text
HEALTHCHECKS_URL
RUNNER_HEALTHCHECKS_URL
STOCK_HEALTHCHECKS_URL
CANDIDATE_HEALTHCHECKS_URL
```

`HEALTHCHECKS_URL` is used by the public scheduler. The runner-specific URLs let you monitor public, stock, and candidate jobs independently. Leave them blank if you do not use Healthchecks.

## Manual GitHub Workflows

GitHub Actions workflows are kept for manual runs and testing only. They do not use `schedule` triggers.

Public figure scan:

```text
.github/workflows/stable-monitor.yml
```

Hourly stock scan:

```text
.github/workflows/hourly-stock-scan.yml
```

Stock candidate refresh:

```text
.github/workflows/stock-candidate-refresh.yml
```

Manual scanner run:

```text
.github/workflows/manual-run-all.yml
```

Runs selected scanners once from the GitHub Actions tab.

Telegram test:

```text
.github/workflows/telegram-test.yml
```

Sends exactly:

```text
✅ Telegram test successful
```

## GitHub Secrets / Environment Values

Required:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Optional:

```text
DISCORD_WEBHOOK_URL
X_BEARER_TOKEN
HEALTHCHECKS_URL
RUNNER_HEALTHCHECKS_URL
STOCK_HEALTHCHECKS_URL
CANDIDATE_HEALTHCHECKS_URL
```

For the always-on runner, put these values in `/etc/market-alert.env` on the host. Do not commit real secrets.

## Optional Live Audio

```text
ENABLE_LIVE_AUDIO=true
ENABLE_PROVISIONAL_LIVE_ALERTS=true
LIVE_SAMPLE_SECONDS=90
```

Live audio uses `yt-dlp`, `ffmpeg`, and `faster-whisper`. Live alerts are marked as provisional and include the approximate live minute.

## Local Run

Install:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-stocks.txt
```

Public figure scan once:

```bash
RUN_ONCE=true python main.py
```

Hourly stock scan:

```bash
python -m stocks.scanner --mode hourly
```

Always-on runner:

```bash
python always_on_runner.py
```

3-day candidate refresh:

```bash
python -m stocks.scanner --mode discover
```

## Testing

```bash
pytest
```

## Important Limitations

GitHub Actions scheduled jobs are not reliable enough for time-sensitive monitoring, so scheduled triggers are intentionally disabled. For the most reliable always-on system, run `always_on_runner.py` on an always-on VM or a PC running 24/7.

The stock scanner uses public market data through `yfinance`. Free market data can be delayed, incomplete, or temporarily unavailable.

Nothing here is financial advice. Verify every alert manually before making any decision.

## Developer Validation

For local tests, install dev dependencies:

```bash
python -m pip install -r requirements.txt -r requirements-stocks.txt -r requirements-dev.txt
python -m pytest -q
```

## Senior Audit Notes

See `docs/AUDIT_NOTES.md` for the fixes made during the final audit.

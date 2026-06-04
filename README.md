# Market-Moving Public Figure + Short-Term Stock Alert System

This project has two independent scanners.

1. **Public-figure alert scanner** — watches configured market-moving public figures and sends Telegram only for direct, high-confidence Good/Bad statements about tradable assets. It runs every 20 minutes in GitHub Actions.
2. **Short-term stock scanner** — checks priority stocks hourly, especially **NVDA** and **NOK**, and sends Telegram only when there is a clean Medium/High confidence entry, exit/risk, or short setup.

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

## Stock alert meanings

### Entry setup

```text
Signal: Good
Model view: Buy
Meaning: Rule-based short-term entry setup.
Includes: entry trigger, exit/invalidation level, target, confidence, reason.
```

### Exit/Risk setup

```text
Signal: Bad
Model view: Sell
Meaning: Rule-based short-term risk or exit setup.
Includes: sell/risk trigger, invalidation level, downside reference, confidence, reason.
```

### Short setup

```text
Signal: Bad
Model view: Short
Meaning: Rule-based confirmed breakdown setup.
Includes: short trigger, short invalidation / cover level, downside reference, confidence, reason.
```

### Hold

```text
Model view: Hold
Meaning: No clear setup. Telegram stays silent.
```

These are mechanical technical research labels, not personal investment advice or instructions to trade.

## Workflows

Public figure scan:

```text
.github/workflows/stable-monitor.yml
```

Runs around every 20 minutes:

```text
:07, :27, :47
```

Hourly stock scan:

```text
.github/workflows/hourly-stock-scan.yml
```

Runs around:

```text
:13 every hour
```

3-day stock candidate refresh:

```text
.github/workflows/stock-candidate-refresh.yml
```

Runs every 3 days around 06:31 UTC. It updates candidate tickers silently by default. Telegram alerts still only come from actionable hourly setups.

## GitHub secrets

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
```

## Optional GitHub variables for live audio

```text
ENABLE_LIVE_AUDIO=true
ENABLE_PROVISIONAL_LIVE_ALERTS=true
LIVE_SAMPLE_SECONDS=90
```

Live audio uses `yt-dlp`, `ffmpeg`, and `faster-whisper`. Live alerts are marked as provisional and include the approximate live minute.

## Local run

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

3-day candidate refresh:

```bash
python -m stocks.scanner --mode discover
```

## Testing

```bash
pytest
```

## Important limitations

GitHub Actions scheduled jobs are free and useful, but they are not guaranteed to start exactly on time. For the most reliable always-on system, run this project on an always-on VM.

The stock scanner uses public market data through `yfinance`. Free market data can be delayed, incomplete, or temporarily unavailable.

Nothing here is financial advice. Verify every alert manually before making any decision.


## Developer validation

For local tests, install dev dependencies:

```bash
python -m pip install -r requirements.txt -r requirements-stocks.txt -r requirements-dev.txt
python -m pytest -q
```


## Senior audit notes

See `docs/AUDIT_NOTES.md` for the fixes made during the final audit.

# Market-Moving Public Figure + Short-Term Stock Alert System

This project has two independent scanners that send Telegram only when strict alert rules pass.

1. **Public-figure alert scanner** - watches configured market-moving public figures and sends Telegram only for direct, high-confidence Good/Bad statements about tradable assets.
2. **Short-term stock scanner** - checks priority stocks hourly, especially **NVDA** and **NOK**, and sends Telegram only when there is a clean High-confidence Buy entry or Sell exit/risk setup.

This is **not** a trading bot. It does not buy, sell, short, hold, connect to a broker, or place trades. Alerts are research signals only and use legal public information.

## Public figures currently enabled

The enabled watchlist lives in:

```text
watchlist.yaml
```

Current enabled market movers include Donald J. Trump, Kevin Warsh, Scott Bessent, Elon Musk, Jensen Huang, Jerome Powell, major central bankers, selected mega-cap CEOs, and market-moving investors. Live provisional alerts are limited to enabled people with a high `market_impact_score`.

Public-figure Telegram wording:

```text
Good = strong positive direct statement
Bad = strong negative direct statement
```

No Telegram alert is sent for neutral statements, vague mentions, inferred-only topics, unclear ticker mapping, duplicate quotes, rumors, unverified clips, or low-confidence quotes.

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

The broader research universe is also listed in `config/stocks.yaml`. The candidate refresh ranks that universe, but it is silent by default and does not send candidate-list Telegram messages.

The stock scanner is strict. Telegram is silent unless all of these are true:

```text
Setup type is Entry or Exit/Risk
Signal is Good or Bad
Model view is Buy or Sell
Confidence is High
Trigger level exists
Exit/invalidation level exists
Risk/reward exists
Duplicate protection passed
Telegram delivery succeeds
```

The stock scanner does **not** send:

```text
Neutral summaries
Weak setups
Medium-confidence setups
Low-confidence setups
Short views
Hold views
Repeated duplicate setups
Candidate refresh lists by default
```

Short-term focus:

```text
1 week to 3 months
```

## GitHub Actions MVP Deployment

GitHub Actions scheduled workflows are the current MVP deployment path. GitHub schedules are best-effort and can be delayed, but they are a low-cost way to keep the Telegram-only system running.

Scheduled workflows:

```text
.github/workflows/stable-monitor.yml
  Public-figure scanner: 7,27,47 * * * *

.github/workflows/hourly-stock-scan.yml
  Hourly stock scanner: 13 * * * *

.github/workflows/stock-candidate-refresh.yml
  Stock candidate refresh: 31 6 */3 * *

.github/workflows/system-health.yml
  Daily health check and Telegram heartbeat: 5 13 * * *

.github/workflows/workflow-watchdog.yml
  Recent workflow failure watchdog: 25 13 * * *
```

Manual workflow:

```text
.github/workflows/telegram-test.yml
```

The Telegram test workflow sends exactly:

```text
✅ Telegram test successful
```

The daily system health workflow sends exactly one heartbeat after tests pass:

```text
✅ Daily system health check passed
```

Workflow failure Telegram alerts are off by default. To intentionally enable immediate per-workflow failure alerts, set repository variable:

```text
ENABLE_WORKFLOW_FAILURE_TELEGRAM=true
```

The scheduled watchdog can still send one grouped Telegram alert if watched workflows failed recently.

## GitHub Secrets / Environment Values

Required for alert delivery:

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

Do not commit real secrets. Use GitHub Secrets for scheduled workflows.

## Telegram Command Center

The always-on runner includes a private Telegram command menu. It uses the same `TELEGRAM_BOT_TOKEN` and only responds to the configured `TELEGRAM_CHAT_ID`.

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

Hold:

```text
Model view: Hold
Meaning: No clear setup. Telegram stays silent.
```

`Short` is intentionally disabled. Bearish actionable stock alerts use `Sell` only.

These are mechanical technical research labels, not personal investment advice or instructions to trade.

## Always-On Runner

For more reliable monitoring than GitHub's best-effort schedules, use the always-on runner on a small VM or a PC/Mac that never sleeps:

```bash
python always_on_runner.py
```

Default free-tier cadence:

```text
Public-figure scanner: every 5 minutes
Stock scanner: every 60 minutes during the configured US market window
Candidate refresh: every 7 days
```

Deployment files live in:

```text
deploy/market-alert.service
deploy/market-alert.env.example
deploy/README.md
docs/FREE_TIER_24_7.md
docs/SETUP_STEP_BY_STEP.md
```

A true 24/7 later option is something like an Oracle Cloud Always Free Ampere A1 VM or a PC running 24/7. Free tiers that sleep should not be treated as true 24/7.

## Free-Tier Controls

The runner has resource-friendly defaults for one tiny always-on VM:

```text
RUNNER_FREE_TIER_MODE=true
RUNNER_PUBLIC_INTERVAL_SECONDS=300
RUNNER_STOCK_MARKET_HOURS_ONLY=true
RUNNER_CANDIDATE_INTERVAL_SECONDS=604800
ENABLE_LIVE_AUDIO=false
ENABLE_PROVISIONAL_LIVE_ALERTS=true
LIVE_MIN_MARKET_IMPACT_SCORE=9
```

The systemd service also sets CPU and memory ceilings so the process stays small on free-tier hosts.

## Healthchecks

Optional healthcheck environment values:

```text
HEALTHCHECKS_URL
RUNNER_HEALTHCHECKS_URL
STOCK_HEALTHCHECKS_URL
CANDIDATE_HEALTHCHECKS_URL
```

`HEALTHCHECKS_URL` is used by the public scheduler. The runner-specific URLs let you monitor public, stock, and candidate jobs independently. Leave them blank if you do not use Healthchecks.

## Optional Live Audio

```text
ENABLE_LIVE_AUDIO=true
ENABLE_PROVISIONAL_LIVE_ALERTS=true
LIVE_MIN_MARKET_IMPACT_SCORE=9
LIVE_SAMPLE_SECONDS=90
```

Live audio uses `yt-dlp`, `ffmpeg`, and `faster-whisper`. Keep live audio disabled on the smallest free VM unless you intentionally install and test the heavier stack. When enabled, live provisional alerts are still limited to high-impact watched people and are marked as provisional with the approximate live minute.

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

Candidate refresh:

```bash
python -m stocks.scanner --mode discover
```

## Testing

```bash
python -m pip install -r requirements.txt -r requirements-stocks.txt -r requirements-dev.txt
python -m pytest -q
```

## Important Limitations

GitHub Actions scheduled jobs are best-effort and may be delayed. For the most reliable always-on system, run `always_on_runner.py` on an always-on VM or a PC running 24/7.

The stock scanner uses public market data through `yfinance`. Free market data can be delayed, incomplete, or temporarily unavailable.

Nothing here is financial advice. Verify every alert manually before making any decision.

## Senior Audit Notes

See `docs/AUDIT_NOTES.md` for the fixes made during the final audit.

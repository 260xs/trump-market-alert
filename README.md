# Trump Market Alert

A no-PC market alert system that runs on GitHub Actions, checks public sources for market-related Donald Trump mentions, stores alert history in Postgres, and sends iPhone push notifications through Telegram.

This project is an alerting system only. It does not place trades, buy, sell, or connect to any brokerage.

## What it does

- Runs automatically from GitHub Actions.
- Checks public sources on a schedule.
- Detects market-related mentions such as stocks, crypto, companies, commodities, banks, CEOs, sectors, tariffs, interest rates, and financial markets.
- Maps known entities to tickers or assets.
- Classifies the mention as bullish, bearish, neutral, or unclear.
- Stores alert history in Postgres to avoid duplicate alerts.
- Sends Telegram notifications to your iPhone.
- Sends a Telegram warning if the GitHub Actions workflow fails.

## Core services

| Service | Purpose |
| --- | --- |
| GitHub Actions | Runs the scanner every 10 minutes without your PC |
| Supabase Postgres | Stores scanned items and alert history |
| Telegram Bot API | Sends iPhone push notifications |
| Python | Runs the scanner, extraction, classification, and alerts |

## Required GitHub secrets

Add these in:

```text
GitHub repo -> Settings -> Secrets and variables -> Actions -> Repository secrets
```

Required secrets:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
DATABASE_URL
```

Optional secrets:

```text
DISCORD_WEBHOOK_URL
X_BEARER_TOKEN
```

Do not commit secrets into the repo.

## Recommended schedule

The workflow is designed to run every 10 minutes.

Recommended cron:

```yaml
- cron: "7-57/10 * * * *"
```

This runs around:

```text
:07, :17, :27, :37, :47, :57
```

Scheduled jobs may not start at the exact second. A few minutes of delay can happen. The important proof is that GitHub shows runs triggered by:

```text
schedule
```

## Project structure

```text
.github/workflows/stable-monitor.yml
config/entities.yaml
config/sources.yaml
scripts/send_test_alert.py
tests/test_basic.py
trump_market_alert/__init__.py
trump_market_alert/config.py
trump_market_alert/models.py
trump_market_alert/db.py
trump_market_alert/mapping.py
trump_market_alert/extract.py
trump_market_alert/classify.py
trump_market_alert/notifiers.py
trump_market_alert/sources.py
trump_market_alert/runner.py
requirements.txt
pytest.ini
README.md
.gitignore
```

## How the workflow works

Every scheduled run:

1. GitHub starts a temporary Ubuntu runner.
2. Python 3.11 is installed.
3. Dependencies are installed from `requirements.txt`.
4. The scanner runs once:

```bash
python -m trump_market_alert.runner --once
```

5. Sources are checked.
6. Market-related text is extracted.
7. Entities are mapped to assets.
8. Alerts are deduplicated using the database.
9. New alerts are sent to Telegram.
10. The runner stops until the next scheduled run.

## Telegram alert format

Alerts follow this format:

```text
🚨 Trump Market Alert

Quote:
“exact quote or relevant excerpt”

Source:
platform + link

Time published:
date/time

Time detected:
date/time

Mentioned entity:
company / crypto / commodity / sector / policy / CEO / brand

Related assets:
ticker / crypto / asset with explanation

Signal:
Bullish / Bearish / Neutral / Unclear

Confidence:
High / Medium / Low

Type:
Direct mention / Inferred relationship / Mixed

Warning:
Not financial advice. Verify before trading.
```

## Local test

If you run it locally, create a `.env` file first:

```text
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
DATABASE_URL=your_postgres_url
LOG_LEVEL=INFO
```

Then install and run:

```bash
python -m pip install -r requirements.txt
python -m trump_market_alert.runner --once
```

Send a Telegram test alert:

```bash
python scripts/send_test_alert.py
```

## GitHub test

After uploading all files:

1. Go to `Actions`.
2. Open `Trump Market Alert - stable 10 minute monitor`.
3. Click `Run workflow` once.
4. Wait for a green check.
5. Stop touching GitHub.
6. Wait for a scheduled run.

A working scheduled run will show:

```text
Trump scan - schedule - run
```

## Important limitations

This is a free scheduled scanner, not an always-on live transcription server.

It can monitor public text sources, public feeds, public transcripts, and configured APIs. It cannot guarantee perfect real-time detection of every spoken word in every livestream without heavier always-on infrastructure or paid transcription services.

## Safety

This system is for alerts and research only.

It does not provide financial advice and does not execute trades.

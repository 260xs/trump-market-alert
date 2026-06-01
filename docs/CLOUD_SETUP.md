# Trump Market Alert - Free No-PC 5-Minute Cloud Setup

This project monitors public sources for market-related Donald Trump mentions and sends iPhone push notifications through Telegram.

It is designed for this setup:

```text
GitHub Actions public repo -> runs every 5 minutes
Supabase free Postgres -> stores alert history and dedupe data
Telegram bot -> sends iPhone notifications
No PC required after setup
```

This is not a trading bot. It never buys, sells, or places trades. It only monitors public information and sends alerts.

## What it does

- Checks public sources every 5 minutes through GitHub Actions.
- Sends Telegram alerts to your iPhone.
- Quotes the detected text.
- Includes the original source link.
- Detects market-related mentions.
- Maps companies, CEOs, brands, crypto, commodities, sectors, and policy topics to related assets.
- Classifies the signal as Bullish, Bearish, Neutral, or Unclear.
- Avoids duplicate alerts.
- Stores alert history in Postgres.
- Keeps raw-source history cleaned so the free database lasts longer.
- Sends throttled error alerts if sources fail.
- Includes a keepalive workflow to reduce the chance that GitHub disables scheduled workflows because the public repo looks inactive.

## Why the repo should be public

For a no-PC, long-term free setup, use a public GitHub repository.

A private repo can work technically, but a 5-minute schedule runs about this often:

```text
12 runs/hour * 24 hours/day * 30 days = about 8,640 runs/month
```

GitHub rounds each job to at least one minute, so a private repo can exceed the free private Actions minutes. A public repo is the practical long-term free option.

Your code can be public. Your bot token, chat ID, and database password stay private in GitHub Secrets. Never upload `.env`.

## Project structure

```text
trump_market_alert_cloud_5min/
  .github/workflows/
    monitor.yml        # scheduled 5-minute checker
    manual_test.yml    # manual setup test + sample Telegram alert
    keepalive.yml      # twice-monthly repo activity commit
  config/
    sources.yaml       # public sources
    entities.yaml      # ticker/asset mappings
  trump_market_alert/
    runner.py          # main runner
    db.py              # SQLite/Postgres database layer
    extract.py         # quote/entity detection pipeline
    classify.py        # signal classification
    mapping.py         # ticker/asset mapping
    notifiers.py       # Telegram/Discord/email notification code
    sources/           # Truth Social, YouTube, RSS, optional X API
  scripts/
    get_telegram_chat_id.py
    test_telegram.py
    send_sample_alert.py
    inspect_db.py
  tests/
  .env.example
  requirements.txt
```

## Step 1 - Create your Telegram bot

1. Open Telegram on your iPhone.
2. Search for `@BotFather`.
3. Send:

```text
/newbot
```

4. Follow the instructions.
5. Copy the bot token.
6. Open your new bot chat.
7. Send:

```text
/start
```

## Step 2 - Get your Telegram chat ID

After sending `/start` to your bot, open this in a browser:

```text
https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```

Replace `YOUR_BOT_TOKEN` with your real bot token.

Look for this part:

```json
"chat":{"id":123456789}
```

The number is your `TELEGRAM_CHAT_ID`.

## Step 3 - Create the free Postgres database

Recommended beginner option: Supabase free Postgres.

1. Create a Supabase account.
2. Create a new project.
3. Save your database password.
4. Open your project.
5. Click `Connect`.
6. Choose the Postgres connection string.
7. Prefer the `Session pooler` connection string for GitHub Actions.
8. Replace `[YOUR-PASSWORD]` with your real database password.
9. Add `?sslmode=require` at the end if it is not already there.

It should look like this format:

```text
postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-region.pooler.supabase.com:5432/postgres?sslmode=require
```

Save this as your `DATABASE_URL` GitHub secret.

## Step 4 - Create the GitHub repo

1. Create a new GitHub repository.
2. Make it public for the long-term free setup.
3. Upload all project files from this folder.
4. Do not upload `.env`.
5. Make sure these workflow files exist:

```text
.github/workflows/monitor.yml
.github/workflows/manual_test.yml
.github/workflows/keepalive.yml
```

## Step 5 - Add GitHub Secrets

In your GitHub repo:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

Add these required secrets:

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

## Step 6 - Optional GitHub Variables

In your GitHub repo:

```text
Settings -> Secrets and variables -> Actions -> Variables
```

You can leave these empty because the workflow already has defaults.

Optional variables:

```text
TRUTH_SOCIAL_ENABLED=true
YOUTUBE_ENABLED=true
RSS_ENABLED=true
X_ENABLED=false
ALERT_LOOKBACK_MINUTES=20
MAX_ITEMS_PER_SOURCE=20
RETENTION_DAYS=180
CHECK_RUN_RETENTION_DAYS=30
SEND_ERROR_ALERTS=true
ERROR_ALERT_HOURS=6
LOG_LEVEL=INFO
```

Recommended values:

```text
ALERT_LOOKBACK_MINUTES=20
MAX_ITEMS_PER_SOURCE=20
RETENTION_DAYS=180
CHECK_RUN_RETENTION_DAYS=30
ERROR_ALERT_HOURS=6
```

## Step 7 - Run the manual test

In GitHub:

```text
Actions -> Trump Market Alert - manual setup test -> Run workflow
```

This does two things:

1. Connects to your database.
2. Sends a sample Telegram alert.

Expected Telegram result:

```text
🚨 Trump Market Alert

Quote:
“Dell is doing a great job.”

Mentioned entity:
Dell Technologies

Related assets:
DELL/stock

Signal:
Bullish

Confidence:
High
```

If you receive this on your iPhone, Telegram is working.

## Step 8 - Enable the automatic 5-minute monitor

The automatic workflow is:

```text
Trump Market Alert - 5 minute monitor
```

It runs on this schedule:

```text
3-58/5 * * * *
```

That means it checks at approximately:

```text
minute 3, 8, 13, 18, 23, 28, 33, 38, 43, 48, 53, 58
```

It is intentionally not scheduled at minute 0 because GitHub can be busier at the start of the hour.

## iPhone notification checklist

On your iPhone:

1. Install Telegram.
2. Open the chat with your bot.
3. Make sure the chat is not muted.
4. Go to iPhone Settings.
5. Open Notifications.
6. Open Telegram.
7. Enable notifications, lock screen, banners, and sounds.

## Alert format

Telegram alerts use this format:

```text
🚨 Trump Market Alert

Quote:
“exact quote”

Source:
platform + link

Time published:
date/time

Time detected:
date/time

Mentioned entity:
company / crypto / commodity / sector / policy / CEO / brand

Related assets:
- ticker/crypto/asset: explanation

Signal:
Bullish / Bearish / Neutral / Unclear

Confidence:
High / Medium / Low

Type:
Direct mention / Inferred relationship / Mixed

Warning:
Not financial advice. Verify before trading.
```

## Sources enabled by default

```text
Truth Social public posts
Donald J. Trump YouTube channel RSS/transcripts when available
White House YouTube channel RSS/transcripts when available
White House public feed
Rev transcript RSS
Google News RSS search for Trump + market terms
```

X/Twitter is included only as an optional official API source. It is disabled by default.

## Long-term safety features

### 1. Postgres history

The database stores:

```text
raw_items   -> source items already seen
alerts      -> alert history and dedupe keys
state       -> last run state and throttles
check_runs  -> recent run logs
```

### 2. Duplicate protection

The dedupe key uses:

```text
source + item ID + normalized quote + detected entities + related assets
```

So the same quote should not alert repeatedly.

### 3. Database cleanup

Alert history is kept.

Old raw source items are deleted after:

```text
RETENTION_DAYS=180
```

Old check-run logs are deleted after:

```text
CHECK_RUN_RETENTION_DAYS=30
```

This keeps the free database small over time.

### 4. Error alert throttling

If a source fails, the bot can send a Telegram warning.

It will not spam you. Default throttle:

```text
ERROR_ALERT_HOURS=6
```

### 5. GitHub keepalive

Public GitHub repos can have scheduled workflows disabled after long inactivity.

This project includes:

```text
.github/workflows/keepalive.yml
```

It commits a tiny timestamp file twice per month to create repository activity.

## Important limits

This is a strong free setup, but not perfect.

- GitHub scheduled workflows can be delayed or skipped during high load.
- It checks every 5 minutes, not every second.
- Exact speech quotes depend on when transcripts/captions/public articles become available.
- Truth Social public endpoints can change.
- X/Twitter requires legal official API access if you enable it.
- Free database limits can change, so keep retention enabled.

## Troubleshooting

### No Telegram alert from manual test

Check:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Also make sure you sent `/start` to the bot first.

### GitHub Action says missing secret

Go to:

```text
Settings -> Secrets and variables -> Actions -> Secrets
```

Add the missing secret exactly as named.

### Database connection failed

Check:

```text
DATABASE_URL
```

Common fixes:

```text
Use the Supabase Session pooler connection string
Use port 5432 for Session pooler
Replace [YOUR-PASSWORD] with the actual database password
Add ?sslmode=require
Do not include spaces
```

### The workflow stops after weeks

Check:

```text
Actions tab -> disabled workflow warning
```

The keepalive workflow is included to reduce this risk. You can also manually run the keepalive workflow or make a small commit.

### Alerts are slow for videos

Text posts are usually faster.

Videos, speeches, livestreams, interviews, and press conferences depend on public transcript/caption availability.

## Local testing, optional

You do not need to run this on your PC long-term.

For one-time local testing:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m trump_market_alert.runner --test-sample
python -m trump_market_alert.runner --once
python -m trump_market_alert.runner --status
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m trump_market_alert.runner --test-sample
python -m trump_market_alert.runner --once
python -m trump_market_alert.runner --status
```

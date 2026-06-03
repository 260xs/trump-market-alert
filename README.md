# Market-Moving Public Figure Alert System

This project monitors legal public sources and sends Telegram alerts only for market-moving public statements.

It has two alert lanes:

1. **Strict verified alerts** — direct, high-confidence, strongly bullish/bearish statements.
2. **Live provisional alerts** — optional live-audio alerts from public livestreams. These are clearly labeled as provisional and include the approximate live minute/timestamp where the quote was detected.

This is not a trading bot. It does not buy, sell, short, hold, or place trades.

## What to upload

Upload everything inside this folder to your GitHub repository root:

```text
.github
alerts
config
database
docs
nlp
scripts
sources
tests
.env.example
.gitignore
README.md
config.py
dedupe.py
main.py
pipeline.py
pytest.ini
requirements.txt
requirements-live.txt
scheduler.py
watchlist.yaml
```

Do not delete your GitHub secrets. Keep:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Optional secrets/variables:

```text
DISCORD_WEBHOOK_URL
HEALTHCHECKS_URL
X_BEARER_TOKEN
```

Optional GitHub variables:

```text
ENABLE_LIVE_AUDIO=true
ENABLE_PROVISIONAL_LIVE_ALERTS=true
LIVE_SAMPLE_SECONDS=90
```

## Telegram alert policy

### Strict alerts send only if all pass

```text
speaker_confidence >= 0.95
quote_confidence >= 0.95
source_confidence >= 0.95
entity_confidence >= 0.95
direct_or_inferred == direct
signal is Strong Bullish or Strong Bearish
duplicate == false
```

### Live provisional alerts send only if all pass

```text
live source is configured and public
provisional live alerts enabled
entity maps clearly to a tradable asset
statement is a direct mention
signal is Strong Bullish or Strong Bearish
duplicate == false
```

Live alerts are marked:

```text
⚠️ LIVE PROVISIONAL Market Alert
```

They include:

```text
Approx live minute
Transcript timestamp inside the sampled audio
Source link
Confidence details
```

## GitHub Actions mode

The workflow runs around:

```text
:07, :17, :27, :37, :47, :57 UTC
```

It also supports external `workflow_dispatch`, so cron-job.org can trigger it as a backup.

## True 24/7 mode

For real continuous live monitoring, run this on a VM:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-live.txt
sudo apt-get update && sudo apt-get install -y ffmpeg
python main.py
```

GitHub Actions is useful for free scheduled checks, but a VM is better for continuous livestream monitoring.

## Test locally

```bash
pip install -r requirements.txt
pytest
python scripts/send_test_alert.py
```

# Setup Guide

## 1. Keep your current secrets

Your GitHub secrets are already set:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
DATABASE_URL
```

Do not delete them.

## 2. Replace repo files

In GitHub, upload the contents of this folder into your repo.

Upload the folder contents, not the zip itself.

Make sure these files exist after upload:

```text
.github/workflows/monitor.yml
.github/workflows/manual_test.yml
.github/workflows/live_audio.yml
.github/workflows/cleanup_old_files.yml
.github/workflows/keepalive.yml
trump_market_alert/runner.py
config/sources.yaml
config/entities.yaml
requirements.txt
```

## 3. Clean old wrong folder

Go to:

```text
Actions -> Trump Market Alert - cleanup old wrong files -> Run workflow
```

This deletes:

```text
.github/workflows/.github
Dockerfile
Procfile
```

## 4. Run manual test

Go to:

```text
Actions -> Trump Market Alert - manual test -> Run workflow
```

Expected result:

```text
Green check
Telegram sample alert arrives
```

## 5. Confirm automatic schedule

Go to:

```text
Actions -> Trump Market Alert - 10 minute monitor
```

Wait for the next scheduled minute:

```text
02, 12, 22, 32, 42, 52
```

The event should show:

```text
schedule
```

GitHub scheduled runs can be delayed, especially around busy times.

## 6. Optional X API

Add secret:

```text
X_BEARER_TOKEN
```

Add repository variable:

```text
X_ENABLED=true
```

This project does not scrape logged-in X pages or bypass X restrictions.

## 7. Optional live audio

Add repository variables:

```text
LIVE_AUDIO_ENABLED=true
LIVE_AUDIO_SECONDS=90
LIVE_AUDIO_MODEL=tiny.en
```

Then run:

```text
Actions -> Trump Market Alert - optional live audio sampler -> Run workflow
```

This is experimental and slower.

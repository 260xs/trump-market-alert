# Free 24/7 Deployment Guide

The project cannot run from Telegram alone. Telegram is the control panel and alert channel; one always-on machine still has to run `always_on_runner.py`.

## Best Free Choice

Use one Oracle Cloud Always Free Ampere A1 VM.

Official Oracle Always Free limits for Ampere A1 VMs:

```text
3,000 OCPU hours per month
18,000 GB-hours per month
```

Source: https://docs.oracle.com/iaas/Content/FreeTier/resourceref.htm

A small bot does not need the full allowance. Recommended shape:

```text
Shape: VM.Standard.A1.Flex
OCPUs: 1
Memory: 1 GB to 2 GB
Boot volume: 50 GB or less if the console allows it
Image: Ubuntu LTS / Oracle Linux compatible with Python 3
```

This keeps the project far below the monthly Ampere A1 limits while still running 24/7.

## How The Hours Work

The Oracle numbers are monthly allocation limits. They are not consumed faster because Python checks every 5 minutes. What matters is the VM size you allocate and how long it exists.

Approximate monthly use for a VM running all month:

```text
1 OCPU x 744 hours = 744 OCPU-hours
2 GB RAM x 744 hours = 1,488 GB-hours
```

That is well below:

```text
3,000 OCPU-hours
18,000 GB-hours
```

Avoid creating multiple VMs unless you are tracking the total carefully.

## Current Free-Tier Defaults

The repo is configured to stay light by default:

```text
RUNNER_FREE_TIER_MODE=true
RUNNER_PUBLIC_INTERVAL_SECONDS=300
RUNNER_STOCK_INTERVAL_SECONDS=3600
RUNNER_STOCK_MARKET_HOURS_ONLY=true
RUNNER_CANDIDATE_INTERVAL_SECONDS=604800
RUNNER_LOOP_SLEEP_SECONDS=5
ENABLE_LIVE_AUDIO=false
ENABLE_PROVISIONAL_LIVE_ALERTS=false
```

Meaning:

```text
Public scanner stays active every 5 minutes.
Stock scanner checks hourly, but only during the configured US market window.
Candidate discovery runs weekly instead of every few days.
Telegram command polling runs inside the same process.
Live audio/transcription stays off because it is heavier.
```

## Settings To Keep It Free

Use these in `/etc/market-alert.env`:

```text
RUNNER_FREE_TIER_MODE=true
RUNNER_PUBLIC_INTERVAL_SECONDS=300
RUNNER_ENABLE_STOCK_SCAN=true
RUNNER_STOCK_INTERVAL_SECONDS=3600
RUNNER_STOCK_MARKET_HOURS_ONLY=true
RUNNER_STOCK_MARKET_TIMEZONE=America/New_York
RUNNER_STOCK_MARKET_OPEN=09:30
RUNNER_STOCK_MARKET_CLOSE=16:15
RUNNER_STOCK_MARKET_DAYS=0,1,2,3,4
RUNNER_ENABLE_CANDIDATE_REFRESH=true
RUNNER_CANDIDATE_INTERVAL_SECONDS=604800
RUNNER_ENABLE_TELEGRAM_COMMANDS=true
ENABLE_LIVE_AUDIO=false
ENABLE_PROVISIONAL_LIVE_ALERTS=false
```

If you want the cheapest/laziest safe mode, disable stock discovery:

```text
RUNNER_ENABLE_CANDIDATE_REFRESH=false
```

If you want the lightest public-figure-only mode:

```text
RUNNER_ENABLE_STOCK_SCAN=false
RUNNER_ENABLE_CANDIDATE_REFRESH=false
```

## What Not To Do

Do not run multiple always-on copies of the same bot.

Do not enable live audio on a 1 GB VM unless you intentionally install and test the heavier dependencies.

Do not use sleeping app hosts for true monitoring. If the host sleeps, Telegram commands and scans stop.

Do not add paid APIs unless you intentionally accept the cost.

Do not loosen alert gates to create more messages. More messages do not mean better alerts.

## Backup Option

Google Cloud has an Always Free `e2-micro` VM in eligible US regions, but it is smaller and more region-limited than Oracle Ampere A1.

Source: https://docs.cloud.google.com/free/docs/free-cloud-features

Use Google only if Oracle sign-up or regional capacity blocks you.

## Exact Next Step

After creating the Oracle VM, run the main setup guide:

```text
docs/SETUP_STEP_BY_STEP.md
```

Then send this to the bot:

```text
/menu
```

# Always-On Deployment

Use this when GitHub Actions scheduled runs are not accurate enough.

The always-on runner is a normal Python process. It runs continuously on an always-awake machine and uses the same strict alert gates as the GitHub workflows.

Default free-tier cadence:

```text
Public-figure scanner: every 5 minutes
Stock scanner: every 60 minutes during configured US market hours
Candidate refresh: every 7 days
```

Recommended hosts:

```text
Oracle Cloud Always Free Ampere A1 VM
A small paid VPS
A home PC or Mac that never sleeps
```

Free app hosts that sleep are not true 24/7 runners.

For the free Oracle sizing guide, see:

```text
docs/FREE_TIER_24_7.md
```

## Install Outline

On the VM or PC:

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin market-alert || true
sudo mkdir -p /opt/trump-market-alert
sudo chown market-alert:market-alert /opt/trump-market-alert
```

Clone or copy the repo into `/opt/trump-market-alert`, then install dependencies:

```bash
cd /opt/trump-market-alert
python3 -m venv .venv
. .venv/bin/activate
export PIP_NO_CACHE_DIR=1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt -r requirements-stocks.txt
```

Create the private env file:

```bash
sudo cp deploy/market-alert.env.example /etc/market-alert.env
sudo chmod 600 /etc/market-alert.env
sudo nano /etc/market-alert.env
```

Add real values for:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Do not paste those values into chat or commit them to the repo.

Install the service:

```bash
sudo cp deploy/market-alert.service /etc/systemd/system/market-alert.service
sudo systemctl daemon-reload
sudo systemctl enable --now market-alert.service
```

Check status and logs:

```bash
systemctl status market-alert.service
journalctl -u market-alert.service -f
```

## Telegram Command Center

The command center is free and runs inside the same always-on process. It only responds to `TELEGRAM_CHAT_ID`.

Set:

```text
RUNNER_ENABLE_TELEGRAM_COMMANDS=true
```

Then send `/menu` to the bot from the configured Telegram chat.

Commands:

```text
/status
/last_alert
/last_public
/last_stock
/run_public_now
/run_stock_now
/pause
/resume
/menu
```

If the bot has an existing webhook configured elsewhere, Telegram long polling may not work until that webhook is removed.

## Healthchecks

For basic public scanner health, set:

```text
HEALTHCHECKS_URL=
```

For independent always-on runner job monitoring, create separate Healthchecks checks and set:

```text
RUNNER_HEALTHCHECKS_URL=
STOCK_HEALTHCHECKS_URL=
CANDIDATE_HEALTHCHECKS_URL=
```

Each configured job healthcheck receives `/start`, success, and `/fail` pings. Leave these blank if you do not use Healthchecks.

## Manual Run Without Service

```bash
cd /opt/trump-market-alert
. .venv/bin/activate
set -a
. /etc/market-alert.env
set +a
python always_on_runner.py
```

## Cadence Settings

The runner reads these environment variables:

```text
RUNNER_PUBLIC_INTERVAL_SECONDS=300
RUNNER_STOCK_INTERVAL_SECONDS=3600
RUNNER_STOCK_MARKET_HOURS_ONLY=true
RUNNER_STOCK_MARKET_TIMEZONE=America/New_York
RUNNER_STOCK_MARKET_OPEN=09:30
RUNNER_STOCK_MARKET_CLOSE=16:15
RUNNER_STOCK_MARKET_DAYS=0,1,2,3,4
RUNNER_CANDIDATE_INTERVAL_SECONDS=604800
```

Keep public scans at 300 seconds or higher unless the source APIs and Telegram behavior are known to be stable. The alert gates still prevent Telegram spam, but source providers may rate-limit overly aggressive polling.

## Free-Tier Hard Limits

The systemd unit sets:

```text
CPUQuota=50%
MemoryMax=512M
TasksMax=128
```

These are ceilings, not resource reservations. They help keep the service small on a free VM. If you later enable heavier live transcription, raise these limits intentionally and monitor usage.

# Always-On Deployment

Use this when GitHub Actions scheduled runs are not accurate enough.

The always-on runner is a normal Python process. It runs continuously on an always-awake machine and uses the same strict alert gates as the GitHub workflows.

Default cadence:

```text
Public-figure scanner: every 5 minutes
Stock scanner: every 60 minutes
Candidate refresh: every 3 days
```

Recommended hosts:

```text
Oracle Cloud Always Free VM
A small paid VPS
A home PC or Mac that never sleeps
```

Free app hosts that sleep are not true 24/7 runners.

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
RUNNER_CANDIDATE_INTERVAL_SECONDS=259200
```

Keep public scans at 300 seconds or higher unless the source APIs and Telegram behavior are known to be stable. The alert gates still prevent Telegram spam, but source providers may rate-limit overly aggressive polling.

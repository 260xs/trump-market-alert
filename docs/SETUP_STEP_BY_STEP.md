# Step-by-Step Setup

This project can be controlled from Telegram for free, but it still needs one always-on machine.

Good free/low-cost options:

- Oracle Cloud Always Free VM
- a home PC/Mac that never sleeps
- any small Linux VPS

Do not use a sleeping free app host if you need true 24/7 monitoring.

## 1. Prepare The Server

On the server:

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip
```

Clone the repo:

```bash
sudo mkdir -p /opt/trump-market-alert
sudo chown "$USER":"$USER" /opt/trump-market-alert
git clone https://github.com/260xs/trump-market-alert.git /opt/trump-market-alert
cd /opt/trump-market-alert
```

Run the installer:

```bash
sudo bash scripts/install_always_on.sh
```

## 2. Add Telegram Secrets

Edit the private env file:

```bash
sudo nano /etc/market-alert.env
```

Set:

```text
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
RUNNER_ENABLE_TELEGRAM_COMMANDS=true
```

Do not paste real secret values into chat, GitHub files, screenshots, or logs.

## 3. Optional: Add GitHub Workflow Control From Telegram

This lets Telegram trigger GitHub manual workflows without opening GitHub.

In `/etc/market-alert.env`, set:

```text
GITHUB_ACTIONS_TOKEN=your_github_token_here
GITHUB_REPOSITORY=260xs/trump-market-alert
GITHUB_REF=main
```

Use a fine-grained GitHub token with Actions read/write access for this repository.

If you skip this, local Telegram commands still work. Only `/github_*` commands will be unavailable.

## 4. Check Setup

Run:

```bash
cd /opt/trump-market-alert
. .venv/bin/activate
python scripts/check_setup.py --env-file /etc/market-alert.env --clear-telegram-webhook --send-telegram-test
```

Expected result:

```text
OK: Telegram bot token works
OK: Telegram test message sent
OK: setup check completed
```

## 5. Start The Always-On Runner

```bash
sudo systemctl restart market-alert.service
sudo systemctl status market-alert.service
```

Follow logs:

```bash
journalctl -u market-alert.service -f
```

## 6. Contact It In Telegram

Open your bot chat and send:

```text
/menu
```

Available local commands:

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

Optional GitHub commands:

```text
/github_public
/github_stock
/github_all
/github_candidates
/github_telegram_test
```

## What Telegram Can Do

```text
Show runner status
Show last public alert
Show last stock alert
Run the local public scanner now
Run the local stock scanner now
Pause/resume scheduled local scans
Trigger manual GitHub workflows if GITHUB_ACTIONS_TOKEN is configured
```

## What Telegram Cannot Do

```text
Cannot trade
Cannot connect to a broker
Cannot buy, sell, short, hold, or close positions
Cannot loosen alert rules
Cannot show or change secrets
Cannot bypass public-source rules
Cannot guarantee free data/API uptime
```

## Common Fixes

If `/menu` does not answer:

1. Check `sudo systemctl status market-alert.service`.
2. Check `journalctl -u market-alert.service -n 100`.
3. Run `python scripts/check_setup.py --env-file /etc/market-alert.env --clear-telegram-webhook`.
4. Make sure `TELEGRAM_CHAT_ID` is the same chat where you are messaging the bot.

If `/github_*` commands fail:

1. Make sure `GITHUB_ACTIONS_TOKEN` is set in `/etc/market-alert.env`.
2. Make sure the token has Actions read/write access.
3. Restart the service after editing the env file.

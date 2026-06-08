# Telegram Commands

The always-on runner includes a free private Telegram command center. It uses the configured `TELEGRAM_BOT_TOKEN` and only responds to `TELEGRAM_CHAT_ID`.

Enable it on the always-on host:

```text
RUNNER_ENABLE_TELEGRAM_COMMANDS=true
```

## Local Runner Commands

```text
/status - runner, last runs, and pause state
/last_alert - latest public or stock alert
/last_public - latest public-figure alert
/last_stock - latest stock setup alert
/run_public_now - run the local public scanner once
/run_stock_now - run the local stock scanner once
/pause - pause scheduled local runner jobs
/resume - resume scheduled local runner jobs
/menu - show the command menu
```

## Optional GitHub Workflow Commands

These are free to run, but they need a GitHub token in the host env file. Do not paste the token into chat.

```text
GITHUB_ACTIONS_TOKEN=
GITHUB_REPOSITORY=260xs/trump-market-alert
GITHUB_REF=main
```

The token should be a fine-grained GitHub token with Actions read/write access for this repository.

```text
/github_public - trigger GitHub public scanner workflow
/github_stock - trigger GitHub stock scanner workflow
/github_all - trigger GitHub manual all-scanners workflow
/github_candidates - trigger GitHub candidate refresh workflow
/github_telegram_test - trigger GitHub Telegram test workflow
```

## Cannot Do

```text
Cannot trade
Cannot connect to a broker
Cannot buy, sell, short, hold, or close positions
Cannot loosen alert rules from Telegram
Cannot show or change secrets
Cannot bypass public-source rules
Cannot guarantee free data/API uptime
```

## Notes

If the Telegram bot has a webhook configured elsewhere, long polling may fail until that webhook is removed.

On runner startup, old queued Telegram updates are skipped so stale `/run_*` commands do not fire after a restart.

# Deployment

## Recommended free setups

### Best true 24/7

Oracle Cloud Always Free VM running `python main.py`.

### Best no-PC scheduled setup

GitHub Actions + cron-job.org backup trigger + Healthchecks.

### Not true continuous

GitHub scheduled workflows can be delayed. Use Healthchecks to know when they stop.

## cron-job.org trigger

Create a POST request to:

```text
https://api.github.com/repos/OWNER/REPO/actions/workflows/stable-monitor.yml/dispatches
```

Headers:

```text
Authorization: Bearer YOUR_FINE_GRAINED_TOKEN
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2026-03-10
Content-Type: application/json
User-Agent: cron-job.org
```

Body:

```json
{"ref":"main","inputs":{"trigger_source":"cron-job.org"}}
```

Use a fine-grained GitHub token limited to this repo with Actions read/write permission.

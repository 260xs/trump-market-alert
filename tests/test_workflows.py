from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _workflow(name: str) -> dict:
    with (ROOT / ".github" / "workflows" / name).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # PyYAML 1.1 treats the key "on" as boolean True.
    if True in data and "on" not in data:
        data["on"] = data[True]
    return data


def _crons(name: str) -> list[str]:
    on = _workflow(name)["on"]
    return [entry["cron"] for entry in on.get("schedule", [])]


def test_production_workflow_schedules_are_enabled():
    assert _crons("stable-monitor.yml") == ["7,27,47 * * * *"]
    assert _crons("hourly-stock-scan.yml") == ["13 * * * *"]
    assert _crons("stock-candidate-refresh.yml") == ["31 6 */3 * *"]


def test_daily_system_health_workflow_sends_telegram_heartbeat():
    on = _workflow("system-health.yml")["on"]
    assert "workflow_dispatch" in on
    assert on.get("schedule") == [{"cron": "5 13 * * *"}]

    workflow_text = (ROOT / ".github" / "workflows" / "system-health.yml").read_text(encoding="utf-8")
    assert "daily Telegram health check at 13:05 UTC" in workflow_text
    assert "Validate Telegram secrets for scheduled health check" in workflow_text
    assert "success() && github.event_name == 'schedule'" in workflow_text
    assert 'TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}' in workflow_text
    assert 'TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}' in workflow_text
    assert "✅ Daily system health check passed" in workflow_text
    assert workflow_text.count("✅ Daily system health check passed") == 1


def test_telegram_test_workflow_is_manual_only_exact_message():
    on = _workflow("telegram-test.yml")["on"]
    assert "workflow_dispatch" in on
    assert on.get("schedule", []) == []

    workflow_text = (ROOT / ".github" / "workflows" / "telegram-test.yml").read_text(encoding="utf-8")
    assert "text=✅ Telegram test successful" in workflow_text
    assert workflow_text.count("text=✅ Telegram test successful") == 1


def test_watchdog_schedule_is_enabled():
    assert _crons("workflow-watchdog.yml") == ["25 13 * * *"]


def test_failure_telegram_alerts_are_opt_in():
    for workflow in [
        "stable-monitor.yml",
        "hourly-stock-scan.yml",
        "stock-candidate-refresh.yml",
        "system-health.yml",
    ]:
        text = (ROOT / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
        assert "ENABLE_WORKFLOW_FAILURE_TELEGRAM" in text
        assert "failure() && env.ENABLE_WORKFLOW_FAILURE_TELEGRAM == 'true'" in text


def test_candidate_refresh_does_not_require_or_use_telegram_secrets_for_scan():
    text = (ROOT / ".github" / "workflows" / "stock-candidate-refresh.yml").read_text(encoding="utf-8")
    assert "Validate Telegram secrets" not in text
    assert 'TELEGRAM_BOT_TOKEN: ""' in text
    assert 'TELEGRAM_CHAT_ID: ""' in text

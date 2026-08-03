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


def test_public_workflow_keeps_live_provisional_guarded_for_high_impact_people():
    text = (ROOT / ".github" / "workflows" / "stable-monitor.yml").read_text(encoding="utf-8")
    assert "ENABLE_LIVE_AUDIO: ${{ vars.ENABLE_LIVE_AUDIO || 'false' }}" in text
    assert "ENABLE_PROVISIONAL_LIVE_ALERTS: ${{ vars.ENABLE_PROVISIONAL_LIVE_ALERTS || 'true' }}" in text
    assert "LIVE_MIN_MARKET_IMPACT_SCORE: ${{ vars.LIVE_MIN_MARKET_IMPACT_SCORE || '9' }}" in text


def test_daily_system_health_workflow_is_scheduled_but_quiet():
    on = _workflow("system-health.yml")["on"]
    assert "workflow_dispatch" in on
    assert on.get("schedule") == [{"cron": "5 13 * * *"}]

    workflow_text = (ROOT / ".github" / "workflows" / "system-health.yml").read_text(encoding="utf-8")
    assert "daily system health check at 13:05 UTC" in workflow_text
    assert "Validate Telegram secrets for scheduled health check" not in workflow_text
    assert "Send Telegram daily health check" not in workflow_text
    assert "✅ Daily system health check passed" not in workflow_text


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
        "manual-run-all.yml",
    ]:
        text = (ROOT / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
        assert "ENABLE_WORKFLOW_FAILURE_TELEGRAM" in text
        assert "failure() && env.ENABLE_WORKFLOW_FAILURE_TELEGRAM == 'true'" in text


def test_workflow_watchdog_is_opt_in_before_it_can_access_telegram_secrets():
    text = (ROOT / ".github" / "workflows" / "workflow-watchdog.yml").read_text(encoding="utf-8")
    assert "ENABLE_WORKFLOW_FAILURE_TELEGRAM" in text
    assert "if: env.ENABLE_WORKFLOW_FAILURE_TELEGRAM == 'true'" in text
    assert "TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}" in text


def test_candidate_refresh_does_not_require_or_use_telegram_secrets_for_scan():
    text = (ROOT / ".github" / "workflows" / "stock-candidate-refresh.yml").read_text(encoding="utf-8")
    assert "Validate Telegram secrets" not in text
    assert 'TELEGRAM_BOT_TOKEN: ""' in text
    assert 'TELEGRAM_CHAT_ID: ""' in text


def test_stock_workflows_serialize_shared_database_and_cache_only_successes():
    hourly = _workflow("hourly-stock-scan.yml")
    refresh = _workflow("stock-candidate-refresh.yml")
    assert hourly["concurrency"]["group"] == "stock-research-database"
    assert refresh["concurrency"]["group"] == "stock-research-database"
    assert hourly["concurrency"]["cancel-in-progress"] is False
    assert refresh["concurrency"]["cancel-in-progress"] is False

    for workflow in [
        "stable-monitor.yml",
        "hourly-stock-scan.yml",
        "stock-candidate-refresh.yml",
        "manual-run-all.yml",
    ]:
        text = (ROOT / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
        assert "if: success()\n        uses: actions/cache/save@v5" in text
        assert "if: always()\n        uses: actions/cache/save@v5" not in text

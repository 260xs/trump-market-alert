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


MANUAL_ONLY_WORKFLOWS = [
    "stable-monitor.yml",
    "hourly-stock-scan.yml",
    "stock-candidate-refresh.yml",
    "manual-run-all.yml",
    "system-health.yml",
    "telegram-test.yml",
]


def test_operational_workflows_are_manual_dispatch_only():
    for workflow in MANUAL_ONLY_WORKFLOWS:
        on = _workflow(workflow)["on"]
        assert "workflow_dispatch" in on
        assert _crons(workflow) == []


def test_telegram_test_workflow_sends_exact_message_only_when_dispatched():
    on = _workflow("telegram-test.yml")["on"]
    assert "workflow_dispatch" in on
    assert on.get("schedule", []) == []

    workflow_text = (ROOT / ".github" / "workflows" / "telegram-test.yml").read_text(encoding="utf-8")
    assert 'text=✅ Telegram test successful' in workflow_text
    assert workflow_text.count('text=✅ Telegram test successful') == 1
    assert "Manual Telegram test workflow." in workflow_text


def test_failure_telegram_alerts_are_opt_in():
    for workflow in [
        "stable-monitor.yml",
        "hourly-stock-scan.yml",
        "stock-candidate-refresh.yml",
        "manual-run-all.yml",
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

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_telegram_setup_success_message_is_manual_test_only() -> None:
    occurrences: list[str] = []
    for path in WORKFLOWS.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        occurrences.extend([path.name] * text.count("Telegram test successful"))

    assert occurrences == ["telegram-test.yml"]


def test_routine_workflows_do_not_send_success_heartbeats() -> None:
    prohibited_success_messages = (
        "Daily system health check passed",
        "system health check passed",
        "heartbeat successful",
    )
    for path in WORKFLOWS.glob("*.yml"):
        if path.name == "telegram-test.yml":
            continue
        text = path.read_text(encoding="utf-8").lower()
        assert all(message.lower() not in text for message in prohibited_success_messages), path.name


def test_workflow_failure_messages_remain_explicitly_opt_in() -> None:
    for path in WORKFLOWS.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        if "sendMessage" not in text or "failed" not in text.lower():
            continue
        assert "ENABLE_WORKFLOW_FAILURE_TELEGRAM" in text, path.name
        assert "ENABLE_WORKFLOW_FAILURE_TELEGRAM == 'true'" in text, path.name

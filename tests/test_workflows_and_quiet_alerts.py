from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str) -> dict:
    data = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
    if True in data and "on" not in data:
        data["on"] = data[True]
    return data


def test_operational_workflows_are_manual_only() -> None:
    for path in [
        ".github/workflows/stable-monitor.yml",
        ".github/workflows/hourly-stock-scan.yml",
        ".github/workflows/stock-candidate-refresh.yml",
        ".github/workflows/manual-run-all.yml",
        ".github/workflows/telegram-test.yml",
        ".github/workflows/system-health.yml",
        ".github/workflows/workflow-watchdog.yml",
    ]:
        workflow = load_yaml(path)
        assert "workflow_dispatch" in workflow["on"]
        assert workflow["on"].get("schedule", []) == []


def test_telegram_test_workflow_sends_manual_exact_message() -> None:
    workflow = load_yaml(".github/workflows/telegram-test.yml")
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["on"].get("schedule", []) == []

    workflow_text = (ROOT / ".github" / "workflows" / "telegram-test.yml").read_text(encoding="utf-8")
    assert 'text=✅ Telegram test successful' in workflow_text
    assert workflow_text.count('text=✅ Telegram test successful') == 1


def test_core_workflow_failure_alerts_are_guarded() -> None:
    for path in [
        ".github/workflows/stable-monitor.yml",
        ".github/workflows/hourly-stock-scan.yml",
        ".github/workflows/stock-candidate-refresh.yml",
        ".github/workflows/system-health.yml",
        ".github/workflows/manual-run-all.yml",
    ]:
        workflow = load_yaml(path)
        assert workflow["env"]["ENABLE_WORKFLOW_FAILURE_TELEGRAM"] == "${{ vars.ENABLE_WORKFLOW_FAILURE_TELEGRAM || 'false' }}"
        failure_steps = [
            step
            for job in workflow["jobs"].values()
            for step in job["steps"]
            if step.get("name") in {"Send Telegram failure alert", "Send Telegram health failure alert"}
        ]
        assert failure_steps
        assert all("ENABLE_WORKFLOW_FAILURE_TELEGRAM == 'true'" in step["if"] for step in failure_steps)


def test_automatic_health_and_watchdog_do_not_send_routine_telegram() -> None:
    health_text = (ROOT / ".github" / "workflows" / "system-health.yml").read_text(encoding="utf-8")
    assert "python -m pytest -q" in health_text
    assert "System health check failed" in health_text
    assert "✅ Daily system health check passed" not in health_text
    assert "success() && github.event_name == 'schedule'" not in health_text
    assert "ENABLE_WORKFLOW_FAILURE_TELEGRAM" in health_text
    assert "failure() && env.ENABLE_WORKFLOW_FAILURE_TELEGRAM == 'true'" in health_text

    watchdog = load_yaml(".github/workflows/workflow-watchdog.yml")
    assert watchdog["on"].get("schedule", []) == []
    assert watchdog["permissions"]["actions"] == "read"
    assert watchdog["env"]["ENABLE_WORKFLOW_FAILURE_TELEGRAM"] == "${{ vars.ENABLE_WORKFLOW_FAILURE_TELEGRAM || 'false' }}"
    watchdog_text = (ROOT / ".github" / "workflows" / "workflow-watchdog.yml").read_text(encoding="utf-8")
    assert "WATCHDOG_LOOKBACK_HOURS" in watchdog_text
    assert "GitHub Actions watchdog alert" in watchdog_text
    assert "failure_telegram_enabled" in watchdog_text
    assert "Telegram failure alerts are disabled" in watchdog_text
    assert "ENABLE_WORKFLOW_FAILURE_TELEGRAM" in watchdog_text


def test_candidate_refresh_is_silent_by_default() -> None:
    stocks_cfg = load_yaml("config/stocks.yaml")
    assert stocks_cfg["settings"]["send_candidate_refresh_telegram"] is False
    assert stocks_cfg["settings"]["send_hourly_summary"] is False
    assert stocks_cfg["settings"]["send_only_when_actionable"] is True
    assert stocks_cfg["settings"]["max_alerts_per_run"] <= 5
    assert stocks_cfg["settings"]["duplicate_silence_hours"] >= 24

    workflow_text = (ROOT / ".github/workflows/stock-candidate-refresh.yml").read_text(encoding="utf-8")
    assert "Validate Telegram secrets" not in workflow_text
    assert 'TELEGRAM_BOT_TOKEN: ""' in workflow_text
    assert 'TELEGRAM_CHAT_ID: ""' in workflow_text


def test_stock_universe_expands_without_losing_priorities() -> None:
    stocks_cfg = load_yaml("config/stocks.yaml")
    priority = {item["ticker"] for item in stocks_cfg["priority_stocks"]}
    universe = set(stocks_cfg["universe"])
    assert {"NVDA", "NOK"}.issubset(priority)
    assert priority.issubset(universe)
    assert len(universe) >= 50
    assert {"INTC", "MU", "TSM", "ASML", "QCOM", "XLF", "XLE", "IWM"}.issubset(universe)

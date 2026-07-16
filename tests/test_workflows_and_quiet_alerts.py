from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_scheduled_workflows_use_expected_crons() -> None:
    expected = {
        ".github/workflows/stable-monitor.yml": "7,27,47 * * * *",
        ".github/workflows/hourly-stock-scan.yml": "13 * * * *",
        ".github/workflows/stock-candidate-refresh.yml": "31 6 */3 * *",
        ".github/workflows/telegram-test.yml": "5 13 * * *",
        ".github/workflows/system-health.yml": "37 4 * * *",
        ".github/workflows/workflow-watchdog.yml": "25 13 * * *",
    }

    for path, cron in expected.items():
        workflow = load_yaml(path)
        assert workflow[True]["schedule"] == [{"cron": cron}]
        assert "workflow_dispatch" in workflow[True]


def test_telegram_test_workflow_sends_daily_exact_message() -> None:
    workflow = load_yaml(".github/workflows/telegram-test.yml")
    assert workflow[True]["schedule"] == [{"cron": "5 13 * * *"}]
    assert "workflow_dispatch" in workflow[True]

    workflow_text = (ROOT / ".github" / "workflows" / "telegram-test.yml").read_text(encoding="utf-8")
    assert 'text=✅ Telegram test successful' in workflow_text
    assert workflow_text.count('text=✅ Telegram test successful') == 1
    assert "daily Telegram heartbeat at 13:05 UTC" in workflow_text


def test_core_workflow_failure_alerts_are_guarded() -> None:
    for path in [
        ".github/workflows/stable-monitor.yml",
        ".github/workflows/hourly-stock-scan.yml",
        ".github/workflows/stock-candidate-refresh.yml",
        ".github/workflows/system-health.yml",
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


def test_automatic_health_and_watchdog_are_enabled() -> None:
    health_text = (ROOT / ".github/workflows/system-health.yml").read_text(encoding="utf-8")
    assert "python -m pytest -q" in health_text
    assert "System health check failed" in health_text
    assert "TELEGRAM_BOT_TOKEN" in health_text
    assert "TELEGRAM_CHAT_ID" in health_text
    assert "ENABLE_WORKFLOW_FAILURE_TELEGRAM" in health_text
    assert "failure() && env.ENABLE_WORKFLOW_FAILURE_TELEGRAM == 'true'" in health_text

    watchdog = load_yaml(".github/workflows/workflow-watchdog.yml")
    assert watchdog["permissions"]["actions"] == "read"
    watchdog_text = (ROOT / ".github/workflows/workflow-watchdog.yml").read_text(encoding="utf-8")
    assert "WATCHDOG_LOOKBACK_HOURS" in watchdog_text
    assert "GitHub Actions watchdog alert" in watchdog_text
    assert "Market-Moving Public Figure Alert" in watchdog_text
    assert "Hourly Stock Research Scanner" in watchdog_text
    assert "Stock Candidate Refresh" in watchdog_text
    assert "Telegram Test" in watchdog_text
    assert "System Health Check" in watchdog_text


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

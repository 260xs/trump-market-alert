from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_scheduled_workflows_use_expected_crons() -> None:
    expected = {
        ".github/workflows/stable-monitor.yml": "2,12,22,32,42,52 * * * *",
        ".github/workflows/hourly-stock-scan.yml": "17,47 * * * *",
        ".github/workflows/stock-candidate-refresh.yml": "31 9 * * *",
        ".github/workflows/telegram-test.yml": "5 13 * * *",
    }

    for path, cron in expected.items():
        workflow = load_yaml(path)
        assert workflow[True]["schedule"] == [{"cron": cron}]
        assert "workflow_dispatch" in workflow[True]


def test_failure_telegram_alerts_are_on_by_default_but_guarded() -> None:
    for path in [
        ".github/workflows/stable-monitor.yml",
        ".github/workflows/hourly-stock-scan.yml",
        ".github/workflows/stock-candidate-refresh.yml",
    ]:
        workflow = load_yaml(path)
        assert workflow["env"]["ENABLE_WORKFLOW_FAILURE_TELEGRAM"] == "${{ vars.ENABLE_WORKFLOW_FAILURE_TELEGRAM || 'true' }}"
        failure_steps = [
            step
            for job in workflow["jobs"].values()
            for step in job["steps"]
            if step.get("name") == "Send Telegram failure alert"
        ]
        assert failure_steps
        assert all("ENABLE_WORKFLOW_FAILURE_TELEGRAM == 'true'" in step["if"] for step in failure_steps)


def test_candidate_refresh_is_silent_but_runs_daily() -> None:
    stocks_cfg = load_yaml("config/stocks.yaml")
    assert stocks_cfg["settings"]["send_candidate_refresh_telegram"] is False
    assert stocks_cfg["settings"]["send_hourly_summary"] is False
    assert stocks_cfg["settings"]["send_only_when_actionable"] is True
    assert stocks_cfg["settings"]["max_alerts_per_run"] >= 8
    assert stocks_cfg["settings"]["duplicate_silence_hours"] <= 12

    workflow_text = (ROOT / ".github/workflows/stock-candidate-refresh.yml").read_text(encoding="utf-8")
    assert "Validate Telegram secrets" not in workflow_text


def test_stock_universe_expands_without_losing_priorities() -> None:
    stocks_cfg = load_yaml("config/stocks.yaml")
    priority = {item["ticker"] for item in stocks_cfg["priority_stocks"]}
    universe = set(stocks_cfg["universe"])
    assert {"NVDA", "NOK"}.issubset(priority)
    assert priority.issubset(universe)
    assert len(universe) >= 60
    assert {"INTC", "MU", "TSM", "ASML", "QCOM", "XLF", "XLE", "IWM"}.issubset(universe)


def test_telegram_heartbeat_sends_only_exact_test_message() -> None:
    workflow_text = (ROOT / ".github/workflows/telegram-test.yml").read_text(encoding="utf-8")
    assert 'cron: "5 13 * * *"' in workflow_text
    assert 'text=✅ Telegram test successful' in workflow_text

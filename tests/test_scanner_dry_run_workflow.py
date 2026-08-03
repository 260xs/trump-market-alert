from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _workflow() -> dict:
    data = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "scanner-dry-run.yml").read_text(encoding="utf-8")
    )
    if True in data and "on" not in data:
        data["on"] = data[True]
    return data


def test_scanner_dry_run_is_manual_only_and_telegram_disabled():
    workflow = _workflow()
    assert workflow["on"] == {"workflow_dispatch": None}
    assert workflow["permissions"] == {"contents": "read"}

    text = (ROOT / ".github" / "workflows" / "scanner-dry-run.yml").read_text(encoding="utf-8")
    assert 'TELEGRAM_BOT_TOKEN: ""' in text
    assert 'TELEGRAM_CHAT_ID: ""' in text
    assert "secrets.TELEGRAM_" not in text
    assert "telegram-test.yml" not in text
    assert "actions/upload-artifact@v4" in text
    assert "artifacts/summary.txt" in text
    assert "--mode hourly" in text
    assert "--mode discover" in text

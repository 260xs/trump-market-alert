from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from event_risk import EventRiskStore, SetupContext, evaluate_event_risk
from event_risk.core import refresh_seed_calendar


def _json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh event-risk calendar and regime state without Telegram.")
    parser.add_argument("--sqlite-path", default=os.environ.get("EVENT_RISK_SQLITE_PATH", "data/event_risk.sqlite3"))
    parser.add_argument("--report-json", default="data/event_risk_report.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["TELEGRAM_CHAT_ID"] = ""
    now = datetime.now(timezone.utc)
    store = EventRiskStore(args.sqlite_path)
    summary = refresh_seed_calendar(store, now)

    # Telegram-disabled dry run: verify the gate blocks known risky sample setups and records reasons.
    samples = [
        SetupContext("NOK", "Buy", "Good", "High", 5.0, 4.7, 2.0, sector="Technology", evaluated_at_utc=datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)),
        SetupContext("NVDA", "Sell", "Bad", "High", 150.0, 158.0, 2.1, sector="Technology", evaluated_at_utc=datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)),
    ]
    gate_results = [evaluate_event_risk(store, sample, sample.evaluated_at_utc, timedelta(hours=72)).__dict__ for sample in samples]
    report = _json_safe({
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "telegram_disabled": True,
        "events_upserted": summary["events_upserted"],
        "regime": summary["regime"],
        "dry_run": bool(args.dry_run),
        "sample_gate_results": gate_results,
        "blocked_reason_counts": store.gate_reason_counts(),
    })
    path = Path(args.report_json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

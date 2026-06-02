from __future__ import annotations

from datetime import timezone

from trump_market_alert.config import load_settings, require_settings
from trump_market_alert.models import Alert, RelatedAsset, utc_now
from trump_market_alert.notifiers import send_alert
from trump_market_alert.extract import stable_hash


def main() -> int:
    settings = load_settings()
    require_settings(settings)
    now = utc_now()
    alert = Alert(
        fingerprint=stable_hash("manual-test", now.isoformat()),
        quote="This is a test alert from Trump Market Alert.",
        source_name="Manual test",
        source_type="test",
        source_url="https://github.com/260xs/trump-market-alert",
        time_published=now,
        time_detected=now,
        entity_name="System test",
        entity_type="test",
        matched_alias="test",
        related_assets=[RelatedAsset(symbol="TEST", asset_type="test", name="Test asset", relationship="notification_test")],
        signal="Neutral",
        confidence="High",
        alert_type="Direct mention",
        reason="This verifies Telegram delivery only.",
    )
    send_alert(settings.telegram_bot_token, settings.telegram_chat_id, alert)
    print("Test alert sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

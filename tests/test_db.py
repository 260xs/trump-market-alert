from __future__ import annotations

from pathlib import Path

from trump_market_alert.db import Database
from trump_market_alert.models import Alert, Asset, Entity
from trump_market_alert.utils import now_utc, sha256_text


def test_save_alert_with_slots_assets(tmp_path: Path):
    db = Database("sqlite:///alerts.db", tmp_path)
    db.connect()
    try:
        ent = Entity(
            name="Bitcoin",
            kind="crypto",
            aliases=["Bitcoin"],
            assets=[Asset(symbol="BTC", type="crypto", explanation="Bitcoin asset.")],
        )
        alert = Alert(
            quote="Bitcoin is amazing.",
            source_platform="Sample",
            source_link="https://example.com",
            published_at=now_utc(),
            detected_at=now_utc(),
            entities=[ent],
            signal="Bullish",
            confidence="High",
            alert_type="Direct mention",
            dedupe_key=sha256_text("sample"),
        )
        assert db.save_alert(alert, sent_ok=True)
        assert not db.save_alert(alert, sent_ok=True)
    finally:
        db.close()

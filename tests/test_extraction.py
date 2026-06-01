from pathlib import Path

from trump_market_alert.extract import build_alerts
from trump_market_alert.mapping import EntityMapper
from trump_market_alert.models import Event
from trump_market_alert.utils import now_utc


def test_sample_dell_alert():
    mapper = EntityMapper.from_yaml(Path("config/entities.yaml"))
    ev = Event(
        src="sample",
        item_id="1",
        platform="Sample",
        text="Dell is doing a great job.",
        url="https://example.com",
        published_at=now_utc(),
        kind="sample",
    )
    alerts = build_alerts(ev, mapper, 6, False, [])
    assert alerts
    assert alerts[0].signal == "Bullish"
    assert any(a.symbol == "DELL" for e in alerts[0].entities for a in e.assets)

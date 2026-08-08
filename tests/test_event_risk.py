from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from stocks.event_risk import (
    CalendarEvent,
    EventRiskDB,
    RegimeSnapshot,
    competing_catalyst_for_statement,
    evaluate_event_risk,
    local_to_utc,
)


@dataclass
class Setup:
    ticker: str = "NVDA"
    signal: str = "Good"
    model_view: str = "Buy"
    setup_key: str = "NVDA:entry:101:95"


def _fresh_db(tmp_path, now: datetime) -> EventRiskDB:
    db = EventRiskDB(tmp_path / "stocks.sqlite3")
    db.init()
    db.record_source_check(
        "Federal Reserve",
        "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        update_frequency="scheduled calendar",
        parser_compatibility="html",
        cursor_behavior="replace by meeting date",
        duplicate_policy="stable source/type/time key",
        checked_at=now,
    )
    db.store_regime_snapshot(
        RegimeSnapshot(
            "Mixed",
            0.82,
            "fresh",
            {
                "broad_index_trend": "up",
                "volatility": "normal",
                "breadth": "mixed",
                "sector_leadership": "technology",
                "risk_on_risk_off": "mixed",
            },
            calculated_at=now.isoformat(),
        )
    )
    return db


def test_daylight_saving_conversion_uses_named_timezone():
    assert local_to_utc("2026-03-08T09:30:00", "America/New_York") == "2026-03-08T13:30:00+00:00"
    assert local_to_utc("2026-11-01T09:30:00", "America/New_York") == "2026-11-01T14:30:00+00:00"


def test_duplicate_event_is_not_inserted_twice(tmp_path):
    now = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    db = _fresh_db(tmp_path, now)
    event = CalendarEvent(
        title="FOMC policy decision",
        event_type="central_bank",
        event_time_utc=(now + timedelta(hours=50)).isoformat(),
        time_confirmed=True,
        source_url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        source_confidence=0.99,
        affected_country="US",
        market="US equities",
        expected_impact="High",
    )

    first_id, first_change = db.upsert_event(event)
    second_id, second_change = db.upsert_event(event)

    assert first_id == second_id
    assert first_change == "created"
    assert second_change == "unchanged"


def test_changed_time_and_cancelled_events_preserve_revisions(tmp_path):
    now = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    db = _fresh_db(tmp_path, now)
    original = CalendarEvent(
        title="Treasury refunding announcement",
        event_type="treasury",
        event_time_utc=(now + timedelta(hours=20)).isoformat(),
        time_confirmed=True,
        source_url="https://home.treasury.gov/",
        source_confidence=0.97,
        affected_country="US",
        market="US equities",
        expected_impact="High",
    )
    moved = CalendarEvent(
        title=original.title,
        event_type=original.event_type,
        event_time_utc=(now + timedelta(hours=21)).isoformat(),
        time_confirmed=True,
        source_url=original.source_url,
        source_confidence=original.source_confidence,
        affected_country=original.affected_country,
        market=original.market,
        expected_impact=original.expected_impact,
    )
    cancelled = CalendarEvent(
        title=original.title,
        event_type=original.event_type,
        event_time_utc=moved.event_time_utc,
        time_confirmed=True,
        source_url=original.source_url,
        source_confidence=original.source_confidence,
        affected_country=original.affected_country,
        market=original.market,
        expected_impact=original.expected_impact,
        status="cancelled",
    )

    db.upsert_event(original)
    _, moved_change = db.upsert_event(moved)
    _, cancelled_change = db.upsert_event(cancelled)

    with db.connect() as con:
        revisions = [r["revision_type"] for r in con.execute("SELECT revision_type FROM event_revisions ORDER BY id")]

    assert moved_change == "time_changed"
    assert cancelled_change == "cancelled"
    assert revisions == ["created", "time_changed", "cancelled"]


def test_market_holiday_blocks_broad_us_signal(tmp_path):
    now = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    db = _fresh_db(tmp_path, now)
    db.upsert_event(
        CalendarEvent(
            title="NYSE market holiday",
            event_type="market_holiday",
            window_start_utc=(now + timedelta(hours=12)).isoformat(),
            window_end_utc=(now + timedelta(hours=36)).isoformat(),
            time_confirmed=True,
            source_url="https://www.nyse.com/markets/hours-calendars",
            source_confidence=0.99,
            affected_country="US",
            market="US equities",
            expected_impact="High",
        )
    )

    decision = evaluate_event_risk(Setup(ticker="AAPL"), db, now=now)

    assert not decision.allowed
    assert decision.reason == "major_event_pending"


def test_uncertain_timestamp_blocks_with_uncertain_reason(tmp_path):
    now = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    db = _fresh_db(tmp_path, now)
    db.upsert_event(
        CalendarEvent(
            title="OPEC policy decision window",
            event_type="commodity_policy",
            window_start_utc=(now + timedelta(hours=10)).isoformat(),
            window_end_utc=(now + timedelta(hours=18)).isoformat(),
            time_confirmed=False,
            source_url="https://www.opec.org/",
            source_confidence=0.96,
            market="energy",
            expected_impact="High",
        )
    )

    decision = evaluate_event_risk(Setup(ticker="USO"), db, now=now)

    assert not decision.allowed
    assert decision.reason == "event_time_uncertain"


def test_earnings_near_signal_blocks_specific_ticker(tmp_path):
    now = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    db = _fresh_db(tmp_path, now)
    db.upsert_event(
        CalendarEvent(
            title="NVIDIA earnings",
            event_type="earnings",
            event_time_utc=(now + timedelta(hours=30)).isoformat(),
            time_confirmed=True,
            source_url="https://investor.nvidia.com/events-and-presentations/",
            source_confidence=0.98,
            company="NVIDIA",
            ticker="NVDA",
            market="US equities",
            expected_impact="High",
        )
    )

    decision = evaluate_event_risk(Setup(ticker="NVDA"), db, now=now)

    assert not decision.allowed
    assert decision.reason == "earnings_risk"


def test_macro_release_near_signal_blocks_broad_market(tmp_path):
    now = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    db = _fresh_db(tmp_path, now)
    db.upsert_event(
        CalendarEvent(
            title="Consumer Price Index",
            event_type="economic_release",
            event_time_utc=(now + timedelta(hours=4)).isoformat(),
            time_confirmed=True,
            source_url="https://www.bls.gov/schedule/news_release/cpi.htm",
            source_confidence=0.99,
            affected_country="US",
            market="US equities",
            expected_impact="High",
        )
    )

    decision = evaluate_event_risk(Setup(ticker="SPY"), db, now=now)

    assert not decision.allowed
    assert decision.reason == "major_event_pending"


def test_competing_catalyst_rejects_statement_attribution(tmp_path):
    now = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    db = _fresh_db(tmp_path, now)
    db.upsert_event(
        CalendarEvent(
            title="Tesla earnings release",
            event_type="earnings",
            event_time_utc=(now - timedelta(hours=1)).isoformat(),
            time_confirmed=True,
            source_url="https://ir.tesla.com/",
            source_confidence=0.98,
            company="Tesla",
            ticker="TSLA",
            market="US equities",
            expected_impact="High",
        )
    )

    event = competing_catalyst_for_statement("TSLA", db, observed_at=now)

    assert event is not None
    assert event.title == "Tesla earnings release"


def test_stale_regime_data_blocks(tmp_path):
    now = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    db = EventRiskDB(tmp_path / "stocks.sqlite3")
    db.init()
    db.record_source_check("BLS", "https://www.bls.gov/schedule/news_release/", checked_at=now)
    db.store_regime_snapshot(RegimeSnapshot("Bullish", 0.7, "fresh", {}, calculated_at=(now - timedelta(hours=7)).isoformat()))

    decision = evaluate_event_risk(Setup(), db, now=now)

    assert not decision.allowed
    assert decision.reason == "market_regime_uncertain"


def test_one_source_failure_isolated_when_another_source_is_fresh(tmp_path):
    now = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    db = _fresh_db(tmp_path, now)
    db.record_source_check("Broken provider", "https://example.invalid/", success=False, error="timeout", checked_at=now)

    decision = evaluate_event_risk(Setup(), db, now=now)

    assert decision.allowed
    assert decision.reason is None

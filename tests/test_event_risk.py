from __future__ import annotations

from datetime import datetime, timedelta, timezone

from event_risk import EventRecord, EventRiskStore, SetupContext, calculate_market_regime, evaluate_event_risk
from event_risk.core import competing_catalyst_decision, eastern_to_utc, refresh_seed_calendar


def make_store(tmp_path):
    store = EventRiskStore(tmp_path / "event_risk.sqlite3")
    store.init()
    return store


def test_daylight_saving_conversion_for_eastern_release_times():
    assert eastern_to_utc(2026, 8, 12, 8, 30).isoformat() == "2026-08-12T12:30:00+00:00"
    assert eastern_to_utc(2026, 12, 10, 8, 30).isoformat() == "2026-12-10T13:30:00+00:00"


def test_market_holiday_event_is_stored_with_utc_time(tmp_path):
    store = make_store(tmp_path)
    refresh_seed_calendar(store, datetime(2026, 7, 18, 10, 0, tzinfo=timezone.utc))
    rows = store.upcoming_events(datetime(2026, 9, 6, tzinfo=timezone.utc), timedelta(days=3))
    assert any(row["event_type"] == "market_holiday" and row["time_confirmed"] == 1 for row in rows)


def test_duplicate_events_update_in_place_and_preserve_revision(tmp_path):
    store = make_store(tmp_path)
    event = EventRecord(
        title="BLS CPI test",
        event_type="macro_release",
        source_id="bls_release_schedule",
        source_url="https://www.bls.gov/schedule/2026/home.htm",
        source_confidence=0.95,
        affected_country="US",
        market="broad US risk assets",
        expected_impact="High",
        time_confirmed=True,
        start_at_utc=datetime(2026, 8, 12, 12, 30, tzinfo=timezone.utc),
        uid="fixed",
    )
    store.upsert_event(event)
    store.upsert_event(event)
    with store.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM event_calendar WHERE event_uid='fixed'").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM event_revisions WHERE event_uid='fixed'").fetchone()[0] == 1


def test_changed_and_cancelled_events_preserve_history(tmp_path):
    store = make_store(tmp_path)
    base = EventRecord(
        title="Company vote",
        event_type="shareholder_vote",
        source_id="company_ir",
        source_url="https://example.com/ir",
        source_confidence=0.95,
        affected_country="US",
        market="US equities",
        company="Example",
        ticker_asset="EXM",
        expected_impact="High",
        time_confirmed=True,
        start_at_utc=datetime(2026, 8, 1, 13, 0, tzinfo=timezone.utc),
        uid="vote",
    )
    store.upsert_event(base)
    store.upsert_event(EventRecord(**{**base.__dict__, "status": "cancelled"}))
    with store.connect() as con:
        status = con.execute("SELECT status FROM event_calendar WHERE event_uid='vote'").fetchone()[0]
        revisions = con.execute("SELECT COUNT(*) FROM event_revisions WHERE event_uid='vote'").fetchone()[0]
    assert status == "cancelled"
    assert revisions == 2


def test_uncertain_timestamp_blocks_setup(tmp_path):
    store = make_store(tmp_path)
    refresh_seed_calendar(store, datetime(2026, 7, 18, 10, 0, tzinfo=timezone.utc))
    store.save_regime(calculate_market_regime(_fresh_inputs(), datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)))
    decision = evaluate_event_risk(
        store,
        SetupContext("NOK", "Buy", "Good", "High", 5.0, 4.5, 2.0, sector="Technology", evaluated_at_utc=datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)),
        datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc),
    )
    assert not decision.allowed
    assert decision.reason == "event_time_uncertain"


def test_earnings_near_signal_blocks_when_time_confirmed(tmp_path):
    store = make_store(tmp_path)
    store.save_regime(calculate_market_regime(_fresh_inputs(), datetime(2026, 7, 21, tzinfo=timezone.utc)))
    store.upsert_event(
        EventRecord(
            title="NOK earnings",
            event_type="earnings",
            source_id="nokia_ir_events",
            source_url="https://www.nokia.com/about-us/investors/investor-relations-events/",
            source_confidence=0.95,
            affected_country="FI",
            market="US equities",
            company="Nokia",
            ticker_asset="NOK",
            expected_impact="High",
            time_confirmed=True,
            start_at_utc=datetime(2026, 7, 23, 11, 0, tzinfo=timezone.utc),
        )
    )
    decision = evaluate_event_risk(store, SetupContext("NOK", "Sell", "Bad", "High", 5.0, 5.5, 2.0, evaluated_at_utc=datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)))
    assert not decision.allowed
    assert decision.reason == "earnings_risk"


def test_macro_release_near_signal_blocks(tmp_path):
    store = make_store(tmp_path)
    store.save_regime(calculate_market_regime(_fresh_inputs(), datetime(2026, 7, 29, tzinfo=timezone.utc)))
    store.upsert_event(
        EventRecord(
            title="GDP",
            event_type="macro_release",
            source_id="bea_release_schedule",
            source_url="https://www.bea.gov/news/schedule",
            source_confidence=0.95,
            affected_country="US",
            market="broad US risk assets",
            expected_impact="High",
            time_confirmed=True,
            start_at_utc=datetime(2026, 7, 30, 12, 30, tzinfo=timezone.utc),
        )
    )
    decision = evaluate_event_risk(store, SetupContext("NVDA", "Buy", "Good", "High", 160.0, 150.0, 2.0, evaluated_at_utc=datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)))
    assert not decision.allowed
    assert decision.reason == "major_event_pending"


def test_competing_catalyst_rejects_public_figure_attribution(tmp_path):
    store = make_store(tmp_path)
    store.upsert_event(
        EventRecord(
            title="NOK earnings",
            event_type="earnings",
            source_id="nokia_ir_events",
            source_url="https://www.nokia.com/about-us/investors/investor-relations-events/",
            source_confidence=0.95,
            affected_country="FI",
            market="US equities",
            company="Nokia",
            ticker_asset="NOK",
            expected_impact="High",
            time_confirmed=False,
            window_start_utc=datetime(2026, 7, 23, tzinfo=timezone.utc),
            window_end_utc=datetime(2026, 7, 24, tzinfo=timezone.utc),
        )
    )
    decision = competing_catalyst_decision(store, "NOK", "https://example.com/statement", datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc))
    assert not decision.allowed
    assert decision.reason == "competing_catalyst"


def test_stale_regime_data_is_uncertain_and_blocks(tmp_path):
    store = make_store(tmp_path)
    store.save_regime(calculate_market_regime(_fresh_inputs(), datetime(2026, 7, 1, tzinfo=timezone.utc)))
    decision = evaluate_event_risk(
        store,
        SetupContext("NVDA", "Buy", "Good", "High", 160.0, 150.0, 2.0, evaluated_at_utc=datetime(2026, 7, 18, tzinfo=timezone.utc)),
        datetime(2026, 7, 18, tzinfo=timezone.utc),
    )
    assert not decision.allowed
    assert decision.reason == "market_regime_uncertain"


def test_one_source_failure_isolated_in_cursor_table(tmp_path):
    store = make_store(tmp_path)
    refresh_seed_calendar(store, datetime(2026, 7, 18, 10, 0, tzinfo=timezone.utc))
    store.save_source_cursor("temporary_failed_source", "cursor", "failure", "timeout")
    with store.connect() as con:
        success_count = con.execute("SELECT COUNT(*) FROM source_cursors WHERE status='success'").fetchone()[0]
        failure_count = con.execute("SELECT COUNT(*) FROM source_cursors WHERE status='failure'").fetchone()[0]
    assert success_count >= 1
    assert failure_count == 1


def _fresh_inputs():
    return {
        "broad_index_trend": {"fresh": True, "state": "Bullish"},
        "volatility": {"fresh": True, "state": "Bullish"},
        "breadth": {"fresh": True, "state": "Bullish"},
        "sector_leadership": {"fresh": True, "state": "Bullish"},
        "risk_on_off": {"fresh": True, "state": "Bullish"},
    }

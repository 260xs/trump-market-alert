from __future__ import annotations

from datetime import datetime, timedelta, timezone

from stocks.universe import (
    CorporateAction,
    ProviderSymbolRecord,
    StockUniverseDB,
    audit_corporate_actions,
    build_universe,
    validate_bars,
)


NOW = datetime(2026, 7, 22, 8, 30, tzinfo=timezone.utc)


def record(**overrides):
    data = {
        "ticker": "ABC",
        "legal_name": "ABC Corp",
        "exchange": "NASDAQ",
        "currency": "USD",
        "asset_type": "common stock",
        "listing_status": "active",
        "provider_symbol_id": "figi-abc",
    }
    data.update(overrides)
    return ProviderSymbolRecord.from_mapping(data, provider="official-exchange-directory", provider_version="2026-07-22", observed_at=NOW)


def bars(count: int, *, interval: str, start_price: float = 100.0, latest_age_hours: int = 1):
    if interval == "daily":
        step = timedelta(days=1)
        latest = NOW - timedelta(hours=latest_age_hours)
    else:
        step = timedelta(hours=1)
        latest = NOW - timedelta(hours=latest_age_hours)
    first = latest - step * (count - 1)
    out = []
    for i in range(count):
        price = start_price + i * 0.1
        out.append(
            {
                "timestamp": (first + step * i).isoformat(),
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price + 0.2,
                "volume": 100_000 + i,
            }
        )
    return out


def test_build_universe_accepts_common_adr_and_etf_and_excludes_unsupported_types():
    decisions = build_universe(
        [
            record(ticker="AAA", asset_type="common stock", provider_symbol_id="figi-aaa"),
            record(ticker="BBB", asset_type="ADR", provider_symbol_id="figi-bbb"),
            record(ticker="CCC", asset_type="ETF", provider_symbol_id="figi-ccc"),
            record(ticker="DDD", asset_type="Warrant", provider_symbol_id="figi-ddd"),
            record(ticker="EEE", asset_type="Unit", provider_symbol_id="figi-eee"),
            record(ticker="FFF", listing_status="delisted", provider_symbol_id="figi-fff"),
        ]
    )

    assert [d.record.ticker for d in decisions if d.eligible] == ["AAA", "BBB", "CCC"]
    excluded = {d.record.ticker: d.reason_code for d in decisions if not d.eligible}
    assert excluded == {"DDD": "unsupported_security_type", "EEE": "unsupported_security_type", "FFF": "inactive_listing"}


def test_provider_disagreement_quarantines_duplicate_ticker_identity():
    decisions = build_universe(
        [
            record(ticker="BRK.B", exchange="NYSE", provider_symbol_id="figi-brkb", share_class="B"),
            record(ticker="BRK.B", exchange="NASDAQ", provider_symbol_id="figi-other", share_class="B"),
        ]
    )

    assert decisions[0].eligible
    assert decisions[1].status == "quarantined"
    assert decisions[1].reason_code == "provider_disagreement"


def test_stock_universe_db_preserves_symbol_history_and_cursor_resume(tmp_path):
    db = StockUniverseDB(tmp_path / "stocks.sqlite3")
    db.init()
    first = build_universe([record(ticker="META", legal_name="Meta Platforms Inc.", provider_symbol_id="figi-meta")])
    second = build_universe([record(ticker="META", legal_name="Meta Platforms Inc.", listing_status="delisted", provider_symbol_id="figi-meta")])

    db.save_decisions(first)
    db.update_cursor("universe-refresh", "batch-001", processed=1)
    db.save_decisions(second)
    db.update_cursor("universe-refresh", "batch-002", processed=1, failed=1)

    assert db.eligible_tickers() == []
    cursor = db.load_cursor("universe-refresh")
    assert cursor is not None
    assert cursor["cursor_value"] == "batch-002"
    assert cursor["processed_count"] == 2
    assert cursor["failed_count"] == 1
    with db.connect() as con:
        history = con.execute("SELECT listing_status, status FROM stock_symbol_history ORDER BY id").fetchall()
    assert [(row["listing_status"], row["status"]) for row in history] == [("active", "eligible"), ("delisted", "excluded")]


def test_validate_bars_passes_representative_fresh_daily_and_hourly_data():
    result = validate_bars("NVDA", bars(130, interval="daily"), bars(80, interval="hourly"), now=NOW)

    assert result.passed
    assert result.reason_codes == []
    assert result.metrics["daily_bars"] == 130
    assert result.metrics["hourly_bars"] == 80
    assert result.metrics["daily_average_dollar_volume_20"] > 0


def test_validate_bars_detects_stale_missing_duplicate_bad_timezone_split_gap_and_invalid_prices():
    daily = bars(130, interval="daily", latest_age_hours=24 * 8)
    hourly = bars(80, interval="hourly")
    daily[3] = dict(daily[2])
    daily[4]["timestamp"] = "2026-07-01T09:30:00"
    daily[5]["close"] = -1
    hourly[10]["open"] = 0
    hourly[11]["high"] = hourly[11]["low"] - 1

    result = validate_bars("BAD", daily, hourly, now=NOW)

    assert not result.passed
    assert "daily_stale" in result.reason_codes
    assert "daily_bad_timezone" in result.reason_codes
    assert "hourly_invalid_price" in result.reason_codes
    assert "hourly_impossible_ohlc" in result.reason_codes


def test_validate_bars_isolates_one_symbol_failure():
    good = validate_bars("GOOD", bars(130, interval="daily"), bars(80, interval="hourly"), now=NOW)
    bad = validate_bars("BAD", [], bars(80, interval="hourly"), now=NOW)

    assert good.passed
    assert not bad.passed
    assert bad.reason_codes == ["daily_insufficient_history"]


def test_corporate_action_audit_detects_adjustment_problems():
    actions = [
        CorporateAction("SPLT", "split", NOW.isoformat(), "split-1", {"ratio": 4}),
        CorporateAction("SPLT", "dividend", NOW.isoformat(), "div-1", {"amount": 0.25}),
    ]
    adjusted = bars(5, interval="daily")
    unadjusted = bars(4, interval="daily")

    result = audit_corporate_actions(actions, adjusted, unadjusted)

    assert not result.passed
    assert "adjusted_unadjusted_length_mismatch" in result.reason_codes
    assert "adjusted_unadjusted_timestamp_mismatch" in result.reason_codes

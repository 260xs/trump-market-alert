from __future__ import annotations

from datetime import datetime, timedelta, timezone

from stocks.universe_quality import SymbolRecord, UniverseStore, compare_provider_metadata, parse_listing_rows, process_batch, validate_price_bars

NOW = datetime(2026, 7, 19, 8, 13, tzinfo=timezone.utc)


def symbol(ticker: str = "NVDA") -> SymbolRecord:
    return SymbolRecord(ticker=ticker, legal_name=f"{ticker} Corp", exchange="NASDAQ", currency="USD", asset_type="COMMON_STOCK", listing_status="active", provider="test-provider", provider_symbol=ticker, first_seen_at=NOW.isoformat(), last_seen_at=NOW.isoformat())


def bars(count: int = 70, *, start: float = 100.0, step: float = 0.2):
    base = NOW - timedelta(hours=count)
    return [{"timestamp": base + timedelta(hours=i + 1), "open": start + i * step - 0.1, "high": start + i * step + 0.3, "low": start + i * step - 0.3, "close": start + i * step, "adjusted_close": start + i * step, "volume": 1_000_000} for i in range(count)]


def test_listing_parser_accepts_common_adr_and_etf_and_excludes_unsupported_types():
    rows = [
        {"symbol": "AAPL", "security_name": "Apple Inc. Common Stock", "security_type": "Common Stock", "listing_status": "active"},
        {"symbol": "TSM", "security_name": "Taiwan Semiconductor ADS", "security_type": "ADR", "listing_status": "active"},
        {"symbol": "SPY", "security_name": "SPDR S&P 500 ETF", "security_type": "ETF", "listing_status": "active"},
        {"symbol": "ABCW", "security_name": "ABC Warrant", "security_type": "Warrant", "listing_status": "active"},
        {"symbol": "XYZU", "security_name": "XYZ Unit", "security_type": "Unit", "listing_status": "active"},
        {"symbol": "OLD", "security_name": "Old Co", "security_type": "Common Stock", "listing_status": "delisted"},
        {"symbol": "AAPL", "security_name": "Apple duplicate", "security_type": "Common Stock", "listing_status": "active"},
    ]
    records, exclusions = parse_listing_rows(rows, provider="nasdaq-trader", exchange="NASDAQ", seen_at=NOW)
    assert [r.ticker for r in records] == ["AAPL", "TSM", "SPY"]
    assert {e.reason for e in exclusions} == {"unsupported_asset_type:WARRANT", "unsupported_asset_type:UNIT", "inactive_or_delisted", "duplicate_provider_symbol"}


def test_universe_store_preserves_first_seen_and_records_exclusion_reasons(tmp_path):
    store = UniverseStore(tmp_path / "stocks.sqlite3")
    store.init()
    assert store.upsert_symbols([symbol("NVDA")]) == 1
    assert store.upsert_symbols([symbol("NVDA")]) == 1
    _, exclusions = parse_listing_rows([{"symbol": "TEST1", "security_name": "Test security", "security_type": "Test", "listing_status": "active"}], provider="nasdaq-trader", exchange="NASDAQ", seen_at=NOW)
    assert store.record_exclusions(exclusions) == 1
    with store.connect() as con:
        row = con.execute("SELECT first_seen_at, last_seen_at FROM symbol_universe WHERE ticker='NVDA'").fetchone()
        reasons = [r["reason"] for r in con.execute("SELECT reason FROM symbol_exclusions").fetchall()]
    assert row["first_seen_at"] == NOW.isoformat()
    assert row["last_seen_at"] == NOW.isoformat()
    assert reasons == ["unsupported_asset_type:TEST"]


def test_data_quality_rejects_stale_candles():
    old = bars()
    for index, item in enumerate(old):
        item["timestamp"] = NOW - timedelta(days=10, hours=len(old) - index)
    finding = validate_price_bars("NVDA", old, interval="1d", now=NOW)
    assert finding.status == "quarantine"
    assert finding.reason == "stale_candles"


def test_data_quality_rejects_missing_bars_duplicate_timestamps_and_bad_timezone():
    assert validate_price_bars("NVDA", [], interval="1h", now=NOW).reason == "missing_bars"
    duplicate = bars()
    duplicate[-1]["timestamp"] = duplicate[-2]["timestamp"]
    assert validate_price_bars("NVDA", duplicate, interval="1h", now=NOW).reason == "duplicate_timestamps"
    naive = bars()
    naive[-1]["timestamp"] = datetime(2026, 7, 19, 7, 0)
    assert validate_price_bars("NVDA", naive, interval="1h", now=NOW).reason == "bad_timezone"


def test_data_quality_rejects_invalid_prices_missing_adjusted_and_split_gap():
    invalid = bars()
    invalid[-1]["close"] = 0
    assert validate_price_bars("NVDA", invalid, interval="1h", now=NOW).reason == "zero_or_negative_price"
    unadjusted = bars()
    for item in unadjusted:
        item.pop("adjusted_close")
    assert validate_price_bars("NVDA", unadjusted, interval="1h", now=NOW, require_adjusted_pair=True).reason == "missing_adjusted_price"
    split_gap = bars()
    split_gap[-1]["close"] = split_gap[-2]["close"] * 0.45
    split_gap[-1]["open"] = split_gap[-1]["close"]
    split_gap[-1]["high"] = split_gap[-1]["close"] + 0.2
    split_gap[-1]["low"] = split_gap[-1]["close"] - 0.2
    assert validate_price_bars("NVDA", split_gap, interval="1h", now=NOW).reason == "possible_unadjusted_split_gap"


def test_provider_metadata_disagreement_quarantines_symbol():
    finding = compare_provider_metadata(symbol("BRK.B"), SymbolRecord(ticker="BRK.B", legal_name="Berkshire Hathaway Inc Class B", exchange="NYSE", currency="USD", asset_type="COMMON_STOCK", listing_status="active", provider="official-exchange", provider_symbol="BRK.B"))
    assert finding.status == "quarantine"
    assert finding.reason == "provider_metadata_disagreement"


def test_cursor_resume_and_one_symbol_failure_isolation(tmp_path):
    store = UniverseStore(tmp_path / "stocks.sqlite3")
    store.init()
    symbols = [symbol("AAA"), symbol("BBB"), symbol("CCC")]
    calls = []

    def handler(record: SymbolRecord):
        calls.append(record.ticker)
        if record.ticker == "BBB":
            raise TimeoutError("provider timeout")
        return validate_price_bars(record.ticker, bars(), interval="1h", now=NOW)

    first = process_batch(store, "unit-test", symbols, handler, batch_size=2)
    second = process_batch(store, "unit-test", symbols, handler, batch_size=2)
    assert first == {"processed": 2, "passed": 1, "quarantined": 0, "failed": 1, "remaining": 1}
    assert second == {"processed": 1, "passed": 1, "quarantined": 0, "failed": 0, "remaining": 0}
    assert calls == ["AAA", "BBB", "CCC"]
    assert store.get_cursor("unit-test") == 3
    with store.connect() as con:
        failed = con.execute("SELECT ticker, reason FROM failed_symbols").fetchone()
    assert failed["ticker"] == "BBB"
    assert failed["reason"] == "TimeoutError"

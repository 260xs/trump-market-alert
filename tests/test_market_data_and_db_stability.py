from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from stocks.research_db import StockResearchDB, iso, utc_now


class FakeDataFrame:
    empty = False

    def reset_index(self):
        return self

    def iterrows(self):
        row = {
            "Date": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "Open": 10,
            "High": 12,
            "Low": 9,
            "Close": 11,
            "Volume": 1000,
        }
        return iter([(0, row)])


def test_market_data_retries_and_caches_success(monkeypatch):
    import stocks.market_data as market_data

    market_data._CACHE.clear()
    calls = {"count": 0}

    def fake_download(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary upstream failure")
        return FakeDataFrame()

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=fake_download))
    monkeypatch.setenv("MARKET_DATA_RETRIES", "2")
    monkeypatch.setenv("MARKET_DATA_RETRY_SLEEP_SECONDS", "0")
    monkeypatch.setenv("MARKET_DATA_CACHE_TTL_SECONDS", "900")

    first = market_data.fetch_bars("NVDA", "30d", "1h")
    second = market_data.fetch_bars("NVDA", "30d", "1h")

    assert calls["count"] == 2
    assert first == second
    assert first[0]["close"] == 11.0
    assert first[0]["volume"] == 1000.0


def test_stock_scan_history_is_pruned(tmp_path):
    db = StockResearchDB(tmp_path / "stocks.sqlite3")
    db.init()
    old_time = iso(utc_now() - timedelta(days=30))

    with db.connect() as con:
        for i in range(3):
            con.execute(
                "INSERT INTO stock_scans (ticker, payload_json, scanned_at) VALUES (?, ?, ?)",
                (f"OLD{i}", "{}", old_time),
            )

    db.store_scan("NVDA", {"signal": "Neutral"})

    with db.connect() as con:
        rows = con.execute("SELECT ticker FROM stock_scans ORDER BY ticker").fetchall()

    assert [row["ticker"] for row in rows] == ["NVDA"]

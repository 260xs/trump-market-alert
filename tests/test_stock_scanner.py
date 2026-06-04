from __future__ import annotations

import math
from pathlib import Path

from stocks.scanner import analyze_bars, hourly_scan
from stocks.research_db import StockResearchDB


def make_bars(closes, volume=1_000_000):
    bars = []
    for i, c in enumerate(closes):
        bars.append({"timestamp": i, "open": c, "high": c + 1, "low": c - 1, "close": c, "volume": volume})
    return bars


class FakeTelegram:
    enabled = True

    def __init__(self):
        self.messages = []

    def send_text(self, text: str) -> str:
        self.messages.append(text)
        return "1"


def test_entry_setup_has_trigger_exit_and_medium_or_high_confidence():
    base = [100 + i * 0.05 + math.sin(i / 2) * 2 for i in range(79)]
    recent_high = max(x + 1 for x in base[-21:-1])
    closes = base + [recent_high + 0.5]
    daily = [90 + i * 0.45 for i in range(80)]

    setup = analyze_bars("NVDA", "NVIDIA", make_bars(closes, volume=2_000_000), {}, make_bars(daily, volume=2_000_000))

    assert setup.signal == "Good"
    assert setup.setup_type == "Entry"
    assert setup.model_view == "Buy"
    assert setup.confidence in {"High", "Medium"}
    assert setup.trigger_level is not None
    assert setup.exit_level is not None
    assert "1 week to 3 months" in setup.timeframe


def test_exit_risk_setup_has_trigger_exit_and_medium_or_high_confidence():
    base = [150 - i * 0.30 for i in range(79)]
    recent_low = min(x - 1 for x in base[-21:-1])
    closes = base + [recent_low - 2.0]
    daily = [160 - i * 0.45 for i in range(80)]

    setup = analyze_bars("NOK", "Nokia", make_bars(closes, volume=2_000_000), {}, make_bars(daily, volume=2_000_000))

    assert setup.signal == "Bad"
    assert setup.setup_type == "Exit/Risk"
    assert setup.model_view in {"Sell", "Short"}
    assert setup.confidence in {"High", "Medium"}
    assert setup.trigger_level is not None
    assert setup.exit_level is not None
    assert "1 week to 3 months" in setup.timeframe


def test_neutral_setup_is_not_actionable():
    closes = [100 + math.sin(i / 3) for i in range(80)]
    setup = analyze_bars("NVDA", "NVIDIA", make_bars(closes), {}, make_bars(closes))
    assert setup.signal == "Neutral"
    assert setup.model_view == "Hold"
    assert not setup.actionable


def test_hourly_scan_does_not_send_for_neutral(monkeypatch, tmp_path: Path):
    import stocks.scanner as scanner

    closes = [100 + math.sin(i / 3) for i in range(80)]

    def fake_fetch(_ticker, _period, _interval):
        return make_bars(closes)

    monkeypatch.setattr(scanner, "fetch_bars", fake_fetch)
    db = StockResearchDB(tmp_path / "stocks.sqlite3")
    db.init()
    telegram = FakeTelegram()
    cfg = {
        "settings": {"min_setup_confidence": "Medium", "duplicate_silence_hours": 24},
        "priority_stocks": [{"ticker": "NVDA", "name": "NVIDIA"}],
        "universe": ["NVDA"],
    }

    assert hourly_scan(cfg, db, telegram) == 0
    assert telegram.messages == []


def test_hourly_scan_sends_only_actionable_entry(monkeypatch, tmp_path: Path):
    import stocks.scanner as scanner

    base = [100 + i * 0.05 + math.sin(i / 2) * 2 for i in range(79)]
    recent_high = max(x + 1 for x in base[-21:-1])
    hourly = make_bars(base + [recent_high + 0.5], volume=2_000_000)
    daily = make_bars([90 + i * 0.45 for i in range(80)], volume=2_000_000)

    def fake_fetch(_ticker, _period, interval):
        return daily if interval == "1d" else hourly

    monkeypatch.setattr(scanner, "fetch_bars", fake_fetch)
    db = StockResearchDB(tmp_path / "stocks.sqlite3")
    db.init()
    telegram = FakeTelegram()
    cfg = {
        "settings": {"min_setup_confidence": "Medium", "duplicate_silence_hours": 24, "max_alerts_per_run": 5},
        "priority_stocks": [{"ticker": "NVDA", "name": "NVIDIA"}],
        "universe": ["NVDA"],
    }

    assert hourly_scan(cfg, db, telegram) == 0
    assert len(telegram.messages) == 1
    assert "Short-Term Stock Entry Setup" in telegram.messages[0]
    assert "Model view (research only):" in telegram.messages[0]
    assert "Buy" in telegram.messages[0]
    assert "Entry trigger" in telegram.messages[0]
    assert "Exit / invalidation level" in telegram.messages[0]

    # Same setup should be suppressed by duplicate protection.
    assert hourly_scan(cfg, db, telegram) == 0
    assert len(telegram.messages) == 1

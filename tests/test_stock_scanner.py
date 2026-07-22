from __future__ import annotations

import math
from pathlib import Path

from stocks.scanner import analyze_bars, discover_candidates, hourly_scan
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
    assert setup.risk_reward is not None
    assert setup.risk_pct is not None
    assert setup.risk_pct < 15
    assert setup.technical_score >= 6
    assert setup.max_technical_score == 8
    assert "1 week to 3 months" in setup.timeframe


def test_exit_risk_setup_has_trigger_exit_and_medium_or_high_confidence():
    base = [150 - i * 0.30 for i in range(79)]
    recent_low = min(x - 1 for x in base[-21:-1])
    closes = base + [recent_low - 2.0]
    daily = [160 - i * 0.45 for i in range(80)]

    setup = analyze_bars("NOK", "Nokia", make_bars(closes, volume=2_000_000), {}, make_bars(daily, volume=2_000_000))

    assert setup.signal == "Bad"
    assert setup.setup_type == "Exit/Risk"
    assert setup.model_view == "Sell"
    assert setup.confidence in {"High", "Medium"}
    assert setup.trigger_level is not None
    assert setup.exit_level is not None
    assert setup.risk_reward is not None
    assert setup.risk_pct is not None
    assert setup.risk_pct < 15
    assert setup.technical_score >= 6
    assert setup.max_technical_score == 8
    assert "1 week to 3 months" in setup.timeframe


def test_confirmed_breakdown_never_uses_short_model_view():
    base = [150 - i * 0.30 for i in range(79)]
    recent_low = min(x - 1 for x in base[-21:-1])
    closes = base + [recent_low - 2.0]
    daily = [160 - i * 0.45 for i in range(80)]

    setup = analyze_bars(
        "NOK",
        "Nokia",
        make_bars(closes, volume=2_000_000),
        {"allow_short_model_view": True},
        make_bars(daily, volume=2_000_000),
    )

    assert setup.signal == "Bad"
    assert setup.setup_type == "Exit/Risk"
    assert setup.model_view == "Sell"
    assert "Short" not in setup.setup_key
    assert "Short" not in setup.reason


def test_neutral_setup_is_not_actionable():
    closes = [100 + math.sin(i / 3) for i in range(80)]
    setup = analyze_bars("NVDA", "NVIDIA", make_bars(closes), {}, make_bars(closes))
    assert setup.signal == "No Signal"
    assert setup.model_view == "No Signal"
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
    assert "Model view:" in telegram.messages[0]
    assert "Buy" in telegram.messages[0]
    assert "Entry trigger" in telegram.messages[0]
    assert "Exit / invalidation level" in telegram.messages[0]
    assert "Risk:" in telegram.messages[0]
    assert "risk/reward" in telegram.messages[0]
    assert "Technical checks:" in telegram.messages[0]
    assert "research signal" in telegram.messages[0]
    assert db.load_open_entry_setup("NVDA") is not None

    # Same setup should be suppressed by duplicate protection.
    assert hourly_scan(cfg, db, telegram) == 0
    assert len(telegram.messages) == 1


def test_prior_buy_followup_sends_exit_risk_when_invalidation_breaks(monkeypatch, tmp_path: Path):
    import stocks.scanner as scanner

    hourly = make_bars([100 + math.sin(i / 3) for i in range(79)] + [94.0], volume=2_000_000)
    daily = make_bars([100 + math.sin(i / 4) for i in range(80)], volume=2_000_000)

    def fake_fetch(_ticker, _period, interval):
        return daily if interval == "1d" else hourly

    monkeypatch.setattr(scanner, "fetch_bars", fake_fetch)
    db = StockResearchDB(tmp_path / "stocks.sqlite3")
    db.init()
    db.open_entry_setup(
        "NVDA",
        "NVDA:entry:Medium:100:95",
        {
            "ticker": "NVDA",
            "setup_key": "NVDA:entry:Medium:100:95",
            "trigger_level": 100.0,
            "exit_level": 95.0,
            "target_level": 110.0,
            "risk_reward": 2.0,
            "risk_pct": 5.0,
        },
    )
    telegram = FakeTelegram()
    cfg = {
        "settings": {"min_setup_confidence": "Medium", "duplicate_silence_hours": 24, "max_alerts_per_run": 5, "min_risk_reward": 1.8, "max_risk_pct": 9.0},
        "priority_stocks": [{"ticker": "NVDA", "name": "NVIDIA"}],
        "universe": ["NVDA"],
    }

    assert hourly_scan(cfg, db, telegram) == 0
    assert len(telegram.messages) == 1
    assert "Short-Term Stock Exit/Risk Setup" in telegram.messages[0]
    assert "Model view:\nSell" in telegram.messages[0]
    assert "Prior Buy research setup follow-up" in telegram.messages[0]
    assert "not an instruction" in telegram.messages[0]
    assert db.load_open_entry_setup("NVDA") is None


def test_candidate_refresh_is_silent_by_default(monkeypatch, tmp_path: Path):
    import stocks.scanner as scanner

    bars = make_bars([100 + i * 0.4 for i in range(90)], volume=2_500_000)

    def fake_fetch(_ticker, _period, _interval):
        return bars

    monkeypatch.setattr(scanner, "fetch_bars", fake_fetch)
    db = StockResearchDB(tmp_path / "stocks.sqlite3")
    db.init()
    telegram = FakeTelegram()
    cfg = {
        "settings": {"max_scan_symbols_per_run": 5, "top_candidate_count": 3},
        "priority_stocks": [{"ticker": "NVDA", "name": "NVIDIA"}],
        "universe": ["NVDA", "NOK", "AAPL"],
    }

    assert discover_candidates(cfg, db, telegram) == 0
    assert telegram.messages == []

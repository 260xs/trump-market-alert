from __future__ import annotations

import pytest

from stocks import scanner
from stocks.scanner import StockSetup


class DummyDB:
    def __init__(self) -> None:
        self.scans = []
        self.alerts = []

    def load_candidate_tickers(self):
        return []

    def store_scan(self, ticker, payload):
        self.scans.append((ticker, payload))

    def seen_recent(self, setup_key, hours):
        return False

    def seen_ticker_signal_recent(self, ticker, signal, hours):
        return False

    def store_alert(self, ticker, signal, setup_key, payload):
        self.alerts.append((ticker, signal, setup_key, payload))


class DummyTelegram:
    def __init__(self, *, enabled: bool = True, fail: bool = False) -> None:
        self.enabled = enabled
        self.fail = fail
        self.messages = []

    def send_text(self, text):
        if self.fail:
            raise RuntimeError("send failed")
        self.messages.append(text)
        return "1"


def _setup(model_view: str = "Buy") -> StockSetup:
    is_buy = model_view == "Buy"
    return StockSetup(
        ticker="NVDA",
        name="NVIDIA",
        signal="Good" if is_buy else "Bad",
        setup_type="Entry" if is_buy else "Exit/Risk",
        model_view=model_view,
        confidence="High",
        timeframe="Short-term swing focus: 1 week to 3 months",
        last_price=100.0,
        trigger_level=101.0,
        exit_level=95.0,
        target_level=113.0,
        rsi_14=60.0,
        ema_8=99.0,
        ema_21=98.0,
        ema_50=97.0,
        daily_ema_20=96.0,
        daily_sma_50=95.0,
        atr_14=2.0,
        volume_ratio_20=1.3,
        risk_reward=2.0,
        risk_pct=5.0,
        reason="clear test setup",
        setup_key=f"NVDA:{model_view}:101:95",
    )


def _cfg():
    return {
        "priority_stocks": [{"ticker": "NVDA", "name": "NVIDIA"}],
        "settings": {
            "min_setup_confidence": "Medium",
            "min_risk_reward": 1.8,
            "max_risk_pct": 9.0,
            "min_successful_scans": 1,
        },
    }


def _patch_market_data(monkeypatch, setup):
    bars = [{"close": 1.0}] * 60
    monkeypatch.setattr(scanner, "fetch_bars", lambda *args, **kwargs: bars)
    monkeypatch.setattr(scanner, "analyze_bars", lambda *args, **kwargs: setup)


def test_actionable_stock_setup_is_not_recorded_when_telegram_disabled(monkeypatch):
    setup = _setup()
    _patch_market_data(monkeypatch, setup)
    db = DummyDB()

    rc = scanner.hourly_scan(_cfg(), db, DummyTelegram(enabled=False))

    assert rc == 0
    assert db.scans
    assert db.alerts == []


def test_actionable_stock_setup_is_not_recorded_when_telegram_fails(monkeypatch):
    setup = _setup()
    _patch_market_data(monkeypatch, setup)
    db = DummyDB()

    with pytest.raises(RuntimeError, match="send failed"):
        scanner.hourly_scan(_cfg(), db, DummyTelegram(enabled=True, fail=True))

    assert db.alerts == []


def test_actionable_stock_setup_is_recorded_only_after_telegram_succeeds(monkeypatch):
    setup = _setup()
    _patch_market_data(monkeypatch, setup)
    db = DummyDB()
    telegram = DummyTelegram(enabled=True)

    rc = scanner.hourly_scan(_cfg(), db, telegram)

    assert rc == 0
    assert len(telegram.messages) == 1
    assert len(db.alerts) == 1


def test_stock_messages_use_required_entry_and_exit_formats():
    entry = scanner._action_message(_setup("Buy"))
    short = scanner._action_message(_setup("Short"))

    assert entry.startswith("📈 Short-Term Stock Entry Setup")
    assert "\nModel view:\nBuy\n\n" in entry
    assert "\nSignal:\nGood\n\n" in entry
    assert "\nEntry trigger:\n101.00\n\n" in entry
    assert "\nRisk:\n5.00%\n\n" in entry

    assert short.startswith("📉 Short-Term Stock Exit/Risk Setup")
    assert "\nModel view:\nShort\n\n" in short
    assert "\nSignal:\nBad\n\n" in short
    assert "\nExit/risk trigger:\n101.00\n\n" in short
    assert "\nInvalidation / recovery level:\n95.00\n\n" in short

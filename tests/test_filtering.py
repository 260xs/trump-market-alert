from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from config import Settings
from database.db import Database
from database.models import Statement
from pipeline import AlertPipeline


class DummyTelegram:
    enabled = True
    def __init__(self):
        self.messages = []
    def send_text(self, text: str) -> str:
        self.messages.append(text)
        return "1"


class DummyDiscord:
    enabled = False
    def send_text(self, text: str) -> None:
        pass


def settings(tmp_path: Path) -> Settings:
    return Settings(
        sqlite_path=tmp_path / "test.sqlite3",
        telegram_bot_token="x",
        telegram_chat_id="1",
        discord_webhook_url="",
        x_bearer_token="",
        healthchecks_url="",
        min_strict_confidence=0.95,
        max_statement_age_hours=48,
        enable_inferred_alerts=False,
        enable_live_audio=False,
        enable_provisional_live_alerts=True,
        live_sample_seconds=90,
        live_min_source_confidence=0.75,
        live_min_speaker_confidence=0.70,
        live_min_quote_confidence=0.60,
        live_min_market_impact_score=9,
        run_once=True,
        log_level="INFO",
    )


def stmt(text: str, *, live: bool = False, quote_conf: float = 0.98, person_id: str = "donald_trump") -> Statement:
    now = datetime.now(timezone.utc)
    return Statement(
        person_id=person_id,
        source_id="test",
        speaker_name="Donald J. Trump",
        statement_text=text,
        source_url="https://example.com/source",
        platform="test",
        published_at=now,
        detected_at=now,
        source_confidence=0.98 if not live else 0.78,
        speaker_confidence=0.98 if not live else 0.72,
        quote_confidence=quote_conf,
        source_type="live_audio" if live else "official",
        platform_item_id=text[:20],
        is_live=live,
        transcript_timestamp="12:34" if live else "",
        live_offset_seconds=754 if live else None,
    )


def pipeline(tmp_path: Path):
    db = Database(tmp_path / "test.sqlite3")
    db.init()
    p = AlertPipeline(db, settings(tmp_path))
    p.telegram = DummyTelegram()
    p.discord = DummyDiscord()
    return p


def test_strong_bullish_direct_sends(tmp_path):
    p = pipeline(tmp_path)
    assert p.process_statement(stmt("Dell is one of the best companies.")) == 1
    assert "DELL" in p.telegram.messages[0]
    assert "Good" in p.telegram.messages[0]


def test_strong_bearish_direct_sends(tmp_path):
    p = pipeline(tmp_path)
    assert p.process_statement(stmt("Tesla is in serious trouble.")) == 1
    assert "TSLA" in p.telegram.messages[0]
    assert "Bad" in p.telegram.messages[0]


def test_neutral_mention_ignored(tmp_path):
    p = pipeline(tmp_path)
    assert p.process_statement(stmt("I met with the CEO of Dell.")) == 0
    assert not p.telegram.messages


def test_inferred_topic_ignored(tmp_path):
    p = pipeline(tmp_path)
    assert p.process_statement(stmt("Tariffs on China are coming.")) == 0
    assert not p.telegram.messages


def test_ambiguous_marvel_ignored(tmp_path):
    p = pipeline(tmp_path)
    assert p.process_statement(stmt("Marvel is the next trillion-dollar company.")) == 0
    assert not p.telegram.messages


def test_duplicate_ignored(tmp_path):
    p = pipeline(tmp_path)
    s = stmt("Bitcoin is amazing.")
    assert p.process_statement(s) == 1
    s2 = stmt("Bitcoin is amazing.")
    s2.platform_item_id = "different"
    assert p.process_statement(s2) == 0


def test_low_confidence_normal_ignored(tmp_path):
    p = pipeline(tmp_path)
    assert p.process_statement(stmt("Nvidia is amazing.", quote_conf=0.60)) == 0


def test_live_provisional_sends_with_timestamp_for_high_impact_person(tmp_path):
    p = pipeline(tmp_path)
    assert p.process_statement(stmt("Bitcoin is amazing.", live=True, quote_conf=0.68)) == 1
    assert "LIVE PROVISIONAL" in p.telegram.messages[0]
    assert "Approx live minute" in p.telegram.messages[0]
    assert "12:34" in p.telegram.messages[0]


def test_live_provisional_ignored_for_lower_impact_person(tmp_path):
    p = pipeline(tmp_path)
    assert p.process_statement(stmt("Bitcoin is amazing.", live=True, quote_conf=0.68, person_id="cathie_wood")) == 0
    assert not p.telegram.messages

class FlakyTelegram:
    enabled = True
    def __init__(self):
        self.messages = []
        self.calls = 0
    def send_text(self, text: str) -> str:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary telegram outage")
        self.messages.append(text)
        return "2"


def test_telegram_failure_does_not_permanently_dedupe_alert(tmp_path):
    p = pipeline(tmp_path)
    p.telegram = FlakyTelegram()
    s = stmt("Bitcoin is amazing.")
    with pytest.raises(RuntimeError, match="Telegram delivery failed"):
        p.process_statement(s)
    s2 = stmt("Bitcoin is amazing.")
    s2.platform_item_id = "same-post-retry"
    assert p.process_statement(s2) == 1
    assert len(p.telegram.messages) == 1


def test_negated_positive_is_not_good_alert(tmp_path):
    p = pipeline(tmp_path)
    assert p.process_statement(stmt("Nvidia is not a great company.")) == 1
    assert "Bad" in p.telegram.messages[0]


def test_old_statement_is_ignored(tmp_path):
    from datetime import timedelta
    p = pipeline(tmp_path)
    s = stmt("Nvidia is amazing.")
    s.published_at = datetime.now(timezone.utc) - timedelta(days=10)
    assert p.process_statement(s) == 0
    assert not p.telegram.messages

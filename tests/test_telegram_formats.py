from __future__ import annotations

from datetime import datetime, timezone

from alerts.telegram import build_market_alert_text
from database.models import EntityMatch, Signal, Statement


def _statement(*, live: bool = False) -> Statement:
    now = datetime(2026, 6, 6, 9, 0, tzinfo=timezone.utc)
    return Statement(
        person_id="p1",
        source_id="s1",
        speaker_name="Donald J. Trump",
        statement_text="Nvidia is doing an incredible job.",
        source_url="https://example.com/source",
        platform="Example",
        published_at=now,
        detected_at=now,
        source_confidence=0.99,
        speaker_confidence=0.99,
        quote_confidence=0.99,
        source_type="x_api",
        platform_item_id="123",
        transcript_timestamp="12:34" if live else "",
        is_live=live,
    )


def _entity() -> EntityMatch:
    return EntityMatch(
        entity_name="Nvidia",
        entity_type="equity",
        mapped_name="NVIDIA",
        ticker="NVDA",
        asset_type="equity",
        entity_confidence=0.99,
        direct_or_inferred="direct",
        reason="Direct mention mapped to NVIDIA.",
    )


def test_verified_public_figure_alert_matches_required_shape():
    text = build_market_alert_text(
        _statement(),
        _entity(),
        Signal("Good", "strong", 0.99, "Strong positive phrase."),
        "strict",
        "Direct high-confidence good statement about NVIDIA.",
    )

    assert text.startswith("🚨 High-Confidence Market Alert\n\nSpeaker:")
    assert "\nSignal:\nGood\n\n" in text
    assert "\nConfidence:\nHigh\n\n" in text
    assert "Source 0.99 | Speaker" not in text
    assert text.endswith("Warning:\nNot financial advice. Verify before trading.")


def test_live_provisional_alert_matches_required_shape():
    text = build_market_alert_text(
        _statement(live=True),
        _entity(),
        Signal("Good", "strong", 0.99, "Strong positive phrase."),
        "live_provisional",
        "ignored for required live format",
    )

    assert text.startswith("⚠️ LIVE PROVISIONAL Market Alert\n\nSpeaker:")
    assert "\nApprox live minute:\n12:34\n\n" in text
    assert "\nConfidence:\nProvisional\n\n" in text
    assert "Time published:" not in text
    assert "Why this alert was sent:\nDirect live statement with strong positive/negative wording." in text
    assert text.endswith("Warning:\nLive transcript may be imperfect. Verify source before acting. Not financial advice.")

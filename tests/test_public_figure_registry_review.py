from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATUSES = {"Active", "Candidate", "Unavailable", "Stale", "Disabled", "Rejected"}


def test_public_figure_registry_review_schema() -> None:
    data = yaml.safe_load((ROOT / "config/public_figure_registry_review.yaml").read_text(encoding="utf-8"))

    people = data["people"]
    assert people
    assert data["review"]["live_scanner_change"] is False
    assert data["review"]["telegram_disabled"] is True
    assert data["review"]["stock_scans_run"] is False

    for person in people:
        assert person["status"] in ALLOWED_STATUSES
        assert person["canonical_name"]
        assert person["current_role"]
        assert person["organization"]
        assert person["country_or_region"]
        assert person["official_sources"]
        assert person["market_relevance"]
        assert person["collection_cursor"]
        assert 0.0 <= float(person["identity_confidence"]) <= 1.0
        assert 0.0 <= float(person["source_confidence"]) <= 1.0
        assert 0.0 <= float(person["asset_relevance_confidence"]) <= 1.0
        if person["status"] != "Active":
            assert person["non_active_reason"]


def test_public_figure_registry_review_does_not_activate_scanner_sources() -> None:
    text = (ROOT / "config/public_figure_registry_review.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)

    assert "allow_telegram_alerts" not in text
    assert "enabled: true" not in text
    assert data["review"]["live_scanner_change"] is False

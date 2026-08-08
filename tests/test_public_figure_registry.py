from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_public_figure_registry_non_active_entries_have_machine_reasons():
    registry_path = ROOT / "config" / "public_figure_registry.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))

    allowed = set(registry["status_values"])
    assert {"Active", "Candidate", "Unavailable", "Stale", "Disabled", "Rejected"}.issubset(allowed)

    entries = []
    entries.extend(registry.get("shadow_candidates", []))
    entries.extend(registry.get("rejected_or_unavailable", []))

    assert entries
    for entry in entries:
        assert entry["status"] in allowed
        if entry["status"] != "Active":
            assert entry.get("machine_reason")


def test_public_figure_registry_candidates_are_shadow_only_and_have_sources():
    registry = yaml.safe_load((ROOT / "config" / "public_figure_registry.yaml").read_text(encoding="utf-8"))

    assert registry["coverage_scope"]["this_registry_effect"] == "documentation_and_shadow_candidates_only"
    candidates = registry["shadow_candidates"]
    assert len(candidates) >= 8

    for candidate in candidates:
        assert candidate["status"] == "Candidate"
        assert candidate["canonical_name"]
        assert candidate["current_role"]
        assert candidate["organization"]
        assert candidate["country_or_region"]
        assert candidate["official_sources"]
        assert candidate["related_assets_or_sectors"]
        assert candidate["identity_confidence"] >= 0.90
        assert candidate["source_confidence"] >= 0.90
        assert candidate["collection_cursor"]["initialized"] is False


def test_public_figure_coverage_report_records_no_dispatch_or_telegram_send():
    report = (ROOT / "docs" / "COVERAGE_REPORT.md").read_text(encoding="utf-8")

    assert "No workflow was dispatched during this coverage-only run." in report
    assert "No live stock scan was started." in report
    assert "No Telegram test or market alert was sent." in report
    assert "does not claim complete global coverage" in report

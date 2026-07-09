from __future__ import annotations

from pathlib import Path

import yaml

from config import load_asset_map, load_watchlist


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(relative: str):
    with (ROOT / relative).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def test_watchlist_has_broader_market_mover_circle_and_unique_source_ids():
    cfg = load_watchlist()
    people = cfg.get("people", [])
    ids = {person["id"] for person in people}

    assert len(people) >= 35
    assert {
        "donald_trump",
        "elon_musk",
        "jensen_huang",
        "jerome_powell",
        "jamie_dimon",
        "satya_nadella",
        "sam_altman",
        "michael_saylor",
        "bill_ackman",
        "michael_dell",
        "howard_lutnick",
        "jamieson_greer",
        "paul_atkins",
        "brian_armstrong",
        "official_market_policy_feeds",
    }.issubset(ids)

    source_ids: list[str] = []
    for person in people:
        assert person.get("enabled") is True
        assert person.get("allow_telegram_alerts") is True
        for source in person.get("sources", []):
            source_ids.append(source["id"])
            assert source.get("enabled") is True
            assert source.get("source_confidence") is not None
            assert source.get("speaker_confidence") is not None
    assert len(source_ids) == len(set(source_ids))


def test_stock_universe_is_expanded_but_risk_capped():
    cfg = load_yaml("config/stocks.yaml")
    settings = cfg["settings"]
    priority = [item["ticker"] for item in cfg["priority_stocks"]]
    universe = cfg["universe"]

    assert len(priority) >= 30
    assert len(universe) >= 130
    assert set(priority).issubset(set(universe))
    assert {"DELL", "ORCL", "VRT", "ANET", "HPE", "MU", "QCOM", "CRM"}.issubset(priority)
    assert len(universe) == len(set(universe))
    assert settings["max_risk_pct"] <= 6.0
    assert settings["max_risk_pct"] < 15
    assert settings["max_alerts_per_run"] <= 3
    assert settings["send_hourly_summary"] is False
    assert settings["send_candidate_refresh_telegram"] is False


def test_stock_alert_safety_mode_is_high_confidence_only():
    settings = load_yaml("config/stocks.yaml")["settings"]
    assert settings["min_setup_confidence"] == "High"
    assert settings["min_risk_reward"] >= 2.2
    assert settings["risk_reward_multiple"] >= 2.5
    assert settings["min_volume_ratio_high"] >= 1.2
    assert settings["entry_rsi_min"] >= 52
    assert settings["entry_rsi_max"] <= 68
    assert settings["exit_rsi_max"] <= 44


def test_asset_map_covers_expanded_priority_names_and_blocks_common_ambiguity():
    cfg = load_asset_map()
    mapped = {asset["ticker"] for asset in cfg.get("assets", [])}
    blocked = {item["name"] for item in cfg.get("blocked_ambiguous", [])}

    assert {
        "NVDA",
        "NOK",
        "TSLA",
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "META",
        "AMD",
        "AVGO",
        "TSM",
        "ASML",
        "SMCI",
        "PLTR",
        "COIN",
        "JPM",
        "XOM",
        "LLY",
        "QQQ",
        "SPY",
        "MSTR",
        "DELL",
        "ORCL",
        "VRT",
        "ANET",
        "HPE",
        "CRM",
        "CRWD",
        "PANW",
    }.issubset(mapped)
    assert {"Marvel", "X", "Meta", "F", "CAT", "ARM"}.issubset(blocked)

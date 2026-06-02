from __future__ import annotations

from pathlib import Path

import yaml

from trump_market_alert.classify import classify_signal
from trump_market_alert.config import DEFAULT_CONFIG_DIR, ROOT_DIR, load_yaml
from trump_market_alert.mapping import EntityMapper


def test_entity_mapping_detects_bitcoin() -> None:
    entities = load_yaml(DEFAULT_CONFIG_DIR / "entities.yaml")
    mapper = EntityMapper.from_config(entities)
    matches = mapper.match("Trump said Bitcoin is amazing for America.")
    assert matches
    assert matches[0].name == "Bitcoin"
    assert matches[0].related_assets[0].symbol == "BTC"


def test_market_context_detects_tariffs() -> None:
    entities = load_yaml(DEFAULT_CONFIG_DIR / "entities.yaml")
    mapper = EntityMapper.from_config(entities)
    assert mapper.has_market_context("Trump discussed tariffs and the stock market.")


def test_market_context_uses_word_boundaries() -> None:
    entities = load_yaml(DEFAULT_CONFIG_DIR / "entities.yaml")
    mapper = EntityMapper.from_config(entities)
    assert not mapper.has_market_context("Trump spoke at a Las Vegas rally.")


def test_classification_positive_signal() -> None:
    result = classify_signal("Dell is doing a great job and investing in America.")
    assert result.signal == "Bullish"


def test_classification_does_not_treat_bank_as_ban() -> None:
    result = classify_signal("Trump mentioned a bank during the interview.")
    assert result.signal == "Neutral"


def test_workflow_yaml_is_valid_multiline_yaml() -> None:
    workflow = ROOT_DIR / ".github" / "workflows" / "stable-monitor.yml"
    text = workflow.read_text(encoding="utf-8")
    assert text.count("\n") > 80
    loaded = yaml.safe_load(text)
    assert isinstance(loaded, dict)


def test_requirements_are_one_package_per_line() -> None:
    requirements = Path(ROOT_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()
    package_lines = [line for line in requirements if line.strip() and not line.startswith("#")]
    assert len(package_lines) >= 7
    assert all(" " not in line.strip() for line in package_lines)


def test_transcript_to_text_supports_current_api_objects(monkeypatch) -> None:
    import sys
    import types

    monkeypatch.setitem(sys.modules, "feedparser", types.SimpleNamespace(parse=lambda *_args, **_kwargs: types.SimpleNamespace(entries=[])))

    from trump_market_alert.sources import _transcript_to_text

    class Snippet:
        def __init__(self, text: str) -> None:
            self.text = text

    class FetchedTranscript:
        snippets = [Snippet("Bitcoin is"), Snippet("important for markets.")]

    assert _transcript_to_text(FetchedTranscript()) == "Bitcoin is important for markets."


def test_transcript_to_text_supports_legacy_dict_rows(monkeypatch) -> None:
    import sys
    import types

    monkeypatch.setitem(sys.modules, "feedparser", types.SimpleNamespace(parse=lambda *_args, **_kwargs: types.SimpleNamespace(entries=[])))

    from trump_market_alert.sources import _transcript_to_text

    rows = [{"text": "Gold is strong."}, {"text": "Oil moved today."}]
    assert _transcript_to_text(rows) == "Gold is strong. Oil moved today."

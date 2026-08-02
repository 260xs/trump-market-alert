from pathlib import Path

import pytest
import yaml

from nlp.ticker_mapper import TickerMapper


ROOT = Path(__file__).resolve().parents[1]


def mapper() -> TickerMapper:
    asset_map = yaml.safe_load(
        (ROOT / "config" / "asset_map.yaml").read_text(encoding="utf-8")
    )
    return TickerMapper(asset_map)


@pytest.mark.parametrize(
    ("text", "ticker"),
    [
        ("Meta Platforms will invest more in AI.", "META"),
        ("META is a strong company.", "META"),
        ("Marvell Technology reported strong demand.", "MRVL"),
    ],
)
def test_explicit_asset_mentions_beat_ambiguity_blockers(text: str, ticker: str) -> None:
    matches = mapper().map_direct_entities(text)
    assert [match.ticker for match in matches] == [ticker]


@pytest.mark.parametrize(
    "text",
    [
        "The meta analysis is incomplete.",
        "The new Marvel movie was popular.",
        "Apple fruit exports increased.",
        "The Amazon rainforest is under pressure.",
    ],
)
def test_ambiguous_contexts_remain_silent(text: str) -> None:
    assert mapper().map_direct_entities(text) == []

from __future__ import annotations

from config import load_asset_map
from nlp.ticker_mapper import TickerMapper


def _tickers(text: str) -> list[str]:
    mapper = TickerMapper(load_asset_map())
    return [match.ticker for match in mapper.map_direct_entities(text)]


def test_explicit_meta_and_marvell_mentions_remain_mappable() -> None:
    assert _tickers("Meta Platforms raised its AI capital expenditure plan.") == ["META"]
    assert _tickers("META issued new guidance after earnings.") == ["META"]
    assert _tickers("Marvell Technology raised its data center outlook.") == ["MRVL"]
    assert _tickers("MRVL announced stronger data center demand.") == ["MRVL"]


def test_ambiguous_or_non_market_terms_do_not_map_to_tickers() -> None:
    assert _tickers("This is a meta analysis of market narratives.") == []
    assert _tickers("Marvel Studios delayed a movie release.") == []
    assert _tickers("The apple fruit harvest was strong this year.") == []
    assert _tickers("Officials discussed conservation in the Amazon rainforest.") == []
    assert _tickers("The artist chose a gold color for the frame.") == []
    assert _tickers("The chef used olive oil in the recipe.") == []

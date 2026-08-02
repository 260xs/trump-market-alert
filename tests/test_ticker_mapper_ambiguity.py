from __future__ import annotations

from nlp.ticker_mapper import TickerMapper


ASSET_MAP = {
    "assets": [
        {
            "canonical": "Meta Platforms",
            "aliases": ["Meta Platforms", "Facebook"],
            "ticker": "META",
            "asset_type": "public_company",
            "confidence": 0.96,
            "direct_patterns": [r"\bMeta Platforms\b", r"\bFacebook\b", r"\bMETA\b"],
            "avoid_contexts": ["metaphor", "meta-analysis", "meta analysis", "meta level"],
        },
        {
            "canonical": "Marvell Technology",
            "aliases": ["Marvell", "Marvell Technology"],
            "ticker": "MRVL",
            "asset_type": "public_company",
            "confidence": 0.98,
            "direct_patterns": [r"\bMarvell\b", r"\bMarvell Technology\b", r"\bMRVL\b"],
            "avoid_contexts": ["Marvel", "Marvel Studios", "Marvel movie", "Marvel superhero"],
        },
        {
            "canonical": "Apple Inc.",
            "aliases": ["Apple", "Apple Inc", "Apple Inc."],
            "ticker": "AAPL",
            "asset_type": "public_company",
            "confidence": 0.96,
            "direct_patterns": [r"\bApple\b", r"\bApple Inc\b", r"\bAAPL\b"],
            "avoid_contexts": ["apple pie", "apple fruit", "apples", "apple farm", "apple juice"],
        },
        {
            "canonical": "Amazon.com",
            "aliases": ["Amazon", "Amazon.com"],
            "ticker": "AMZN",
            "asset_type": "public_company",
            "confidence": 0.96,
            "direct_patterns": [r"\bAmazon\b", r"\bAmazon.com\b", r"\bAMZN\b"],
            "avoid_contexts": ["amazon rainforest", "amazon river", "amazon jungle"],
        },
    ],
    "blocked_ambiguous": [
        {
            "name": "Marvel",
            "reason": "Could mean Marvel Entertainment, Marvel content, or Marvell Technology.",
            "patterns": [r"\bMarvel\b"],
        },
        {
            "name": "Meta",
            "reason": "Meta alone can be a general word. Require Meta Platforms, Facebook, or ticker META.",
            "patterns": [r"\bmeta\b"],
        },
    ],
}


def _tickers(text: str) -> list[str]:
    return [match.ticker for match in TickerMapper(ASSET_MAP).map_direct_entities(text)]


def test_meta_platforms_and_ticker_are_not_blocked_by_meta_ambiguity():
    assert _tickers("Meta Platforms raised its AI capital expenditure plan.") == ["META"]
    assert _tickers("META issued new guidance after earnings.") == ["META"]


def test_ordinary_meta_context_remains_blocked():
    assert _tickers("This is a meta analysis of market narratives, not a company comment.") == []
    assert _tickers("The speaker made a meta level point about regulation.") == []


def test_marvell_technology_is_not_blocked_by_marvel_ambiguity():
    assert _tickers("Marvell Technology raised its AI infrastructure outlook.") == ["MRVL"]
    assert _tickers("MRVL announced stronger data center demand.") == ["MRVL"]


def test_marvel_entertainment_context_remains_blocked():
    assert _tickers("Marvel Studios delayed a movie release.") == []
    assert _tickers("The Marvel superhero franchise had a strong weekend.") == []


def test_apple_and_amazon_non_market_contexts_remain_blocked():
    assert _tickers("The apple fruit harvest was strong this year.") == []
    assert _tickers("Officials discussed conservation in the Amazon rainforest.") == []

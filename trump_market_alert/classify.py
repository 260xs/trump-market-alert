from __future__ import annotations

import re

from .models import Entity

MARKET_KEYWORDS = [
    "stock", "stocks", "market", "markets", "nasdaq", "dow", "s&p", "sp500", "russell",
    "crypto", "bitcoin", "ethereum", "coin", "token", "blockchain",
    "oil", "gas", "lng", "gold", "silver", "copper", "steel", "commodity", "commodities",
    "bank", "banks", "banking", "fed", "federal reserve", "interest rate", "rates", "inflation",
    "tariff", "tariffs", "trade", "exports", "imports", "china trade",
    "company", "companies", "ceo", "earnings", "profit", "profits", "revenue", "sales",
    "sector", "industry", "manufacturing", "jobs report", "treasury", "bond", "bonds",
]

POSITIVE_TERMS = [
    "great", "amazing", "excellent", "fantastic", "tremendous", "strong", "booming", "record",
    "winner", "winning", "love", "support", "approve", "buy", "invest", "investment", "breakthrough",
    "good job", "doing a great job", "beautiful", "successful", "unleash", "growth", "deal",
]

NEGATIVE_TERMS = [
    "bad", "terrible", "disaster", "failing", "failed", "weak", "corrupt", "scam", "fraud",
    "crash", "collapse", "boycott", "sell", "avoid", "too high", "expensive", "ripoff", "hurt",
    "destroy", "killing", "unfair", "tax them", "punish", "ban", "sanction", "tariffed",
]

UNCLEAR_POLICY_TERMS = ["tariff", "tariffs", "federal reserve", "fed", "rates", "interest rates", "powell"]


def contains_market_keyword(text: str) -> bool:
    t = (text or "").lower()
    return any(re.search(rf"\b{re.escape(k)}\b", t) for k in MARKET_KEYWORDS if k.isalnum()) or any(k in t for k in MARKET_KEYWORDS if not k.isalnum())


def is_market_related(text: str, entities: list[Entity]) -> bool:
    if entities:
        return True
    return contains_market_keyword(text)


def classify_signal(text: str, entities: list[Entity]) -> tuple[str, str, str]:
    t = (text or "").lower()
    pos = sum(1 for w in POSITIVE_TERMS if w in t)
    neg = sum(1 for w in NEGATIVE_TERMS if w in t)

    if pos > 0 and neg == 0:
        signal = "Bullish"
        reason = "positive wording near a market-related mention"
    elif neg > 0 and pos == 0:
        signal = "Bearish"
        reason = "negative wording near a market-related mention"
    elif pos > 0 and neg > 0:
        signal = "Unclear"
        reason = "mixed positive and negative wording"
    else:
        # Policy mentions often move markets, but direction is not automatic.
        signal = "Neutral"
        reason = "market-related mention without clear positive or negative wording"
        if any(w in t for w in UNCLEAR_POLICY_TERMS):
            signal = "Unclear"
            reason = "policy-related mention; market direction depends on details"

    if any(e.relation == "inferred" or e.kind == "ceo" for e in entities):
        confidence = "Medium" if signal in {"Bullish", "Bearish"} else "Low"
    elif entities and signal in {"Bullish", "Bearish"}:
        confidence = "High"
    elif entities:
        confidence = "Medium"
    else:
        confidence = "Low"

    return signal, confidence, reason


def alert_type_for(entities: list[Entity]) -> str:
    if not entities:
        return "Direct mention"
    has_inferred = any(e.relation == "inferred" or e.kind == "ceo" for e in entities)
    has_direct = any(e.relation != "inferred" and e.kind != "ceo" for e in entities)
    if has_inferred and has_direct:
        return "Mixed"
    if has_inferred:
        return "Inferred relationship"
    return "Direct mention"

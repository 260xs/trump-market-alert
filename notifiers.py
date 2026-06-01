from __future__ import annotations

import re

from .models import EntityHit
from .utils import normalize_for_hash

BULLISH = [
    "great", "amazing", "excellent", "strong", "stronger", "best", "booming", "record", "win", "winning",
    "support", "supports", "back", "backs", "love", "likes", "good job", "doing well", "tremendous", "beautiful",
    "buy", "invest", "build", "growth", "jobs", "leader", "successful", "cut taxes", "deregulate",
]
BEARISH = [
    "bad", "terrible", "horrible", "weak", "worst", "crash", "fraud", "scam", "ripoff", "too high",
    "destroy", "hurting", "failing", "failed", "boycott", "sanction", "tariff on", "tax on", "attack",
    "investigate", "sue", "lawsuit", "corrupt", "enemy", "disaster", "sell", "dump", "ban",
]
NEUTRAL_POLICY = ["met with", "meeting", "said", "announced", "signed", "executive order", "nominate", "appoint", "policy"]


def _count_terms(text: str, terms: list[str]) -> int:
    t = normalize_for_hash(text)
    return sum(1 for term in terms if re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", t))


def classify_signal(text: str, hits: list[EntityHit], market_terms: list[str], source_type: str) -> tuple[str, str, str, str]:
    b = _count_terms(text, BULLISH)
    s = _count_terms(text, BEARISH)
    n = _count_terms(text, NEUTRAL_POLICY)

    if b > s:
        signal = "Bullish"
        reason = "Positive language appears near a market-related mention."
    elif s > b:
        signal = "Bearish"
        reason = "Negative, restrictive, or risk language appears near a market-related mention."
    elif n:
        signal = "Neutral"
        reason = "Policy/news language appears without clear positive or negative wording."
    else:
        signal = "Unclear" if market_terms and not hits else "Neutral"
        reason = "Market-related mention found, but direction is not clear."

    if hits and (b or s):
        confidence = "High"
    elif hits or source_type in {"truth_social", "transcript", "live_audio"}:
        confidence = "Medium"
    else:
        confidence = "Low"

    if source_type in {"news", "rss_news"} and '"' not in text and "“" not in text:
        confidence = "Low"
        alert_type = "Reported relationship"
    elif hits:
        alert_type = "Direct mention"
    elif market_terms:
        alert_type = "Inferred relationship"
    else:
        alert_type = "Unclear"

    return signal, confidence, alert_type, reason

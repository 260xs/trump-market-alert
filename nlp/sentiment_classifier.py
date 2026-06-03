from __future__ import annotations

import re

from database.models import Signal


STRONG_BULLISH = [
    "one of the best", "the best", "amazing", "incredible", "fantastic", "great company",
    "great job", "doing an incredible job", "leading the future", "most important company",
    "bright future", "very strong", "stronger than ever", "winner", "winning", "tremendous",
]

STRONG_BEARISH = [
    "serious trouble", "in trouble", "failing", "failure", "scam", "fraud", "terrible company",
    "disaster", "very bad", "horrible", "should investigate", "investigate this company",
    "dangerous", "corrupt", "weak company", "going down", "collapse", "bankrupt",
]

NEUTRAL_CONTEXT = [
    "met with", "meeting with", "talked with", "spoke with", "mentioned", "discussed", "visited",
]

REPORTED_CONTEXT = [
    "people are saying", "people say", "online are saying", "rumors", "rumor", "reportedly", "according to"]


def _contains_phrase(text: str, phrases: list[str]) -> str | None:
    low = text.lower()
    for phrase in phrases:
        if phrase in low:
            return phrase
    return None


def classify_signal(text: str) -> Signal:
    low = text.lower()

    if _contains_phrase(low, REPORTED_CONTEXT):
        return Signal("Unclear", "none", 0.30, "Reported or rumor-like wording, not a direct statement.")

    bullish = _contains_phrase(low, STRONG_BULLISH)
    bearish = _contains_phrase(low, STRONG_BEARISH)

    if bullish and bearish:
        return Signal("Mixed", "mixed", 0.50, "Both strong positive and strong negative language found.")
    if bullish:
        return Signal("Strong Bullish", "strong", 0.97, f"Strong positive phrase detected: {bullish}.")
    if bearish:
        return Signal("Strong Bearish", "strong", 0.97, f"Strong negative phrase detected: {bearish}.")

    if _contains_phrase(low, NEUTRAL_CONTEXT):
        return Signal("Neutral", "none", 0.90, "Neutral meeting/discussion wording, not a strong signal.")

    # Fallback word boundary checks for simple strong statements.
    if re.search(r"\b(great|amazing|fantastic|incredible|tremendous)\b", low):
        return Signal("Strong Bullish", "strong", 0.95, "Strong positive adjective near a direct asset mention.")
    if re.search(r"\b(terrible|scam|fraud|failing|dangerous|disaster)\b", low):
        return Signal("Strong Bearish", "strong", 0.95, "Strong negative adjective near a direct asset mention.")

    return Signal("Neutral", "none", 0.80, "No strong bullish or bearish language detected.")

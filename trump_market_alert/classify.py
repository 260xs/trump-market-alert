from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable

from .extract import normalize_text
from .models import Classification, EntityMatch

BULLISH_TERMS = {
    "great", "excellent", "amazing", "strong", "booming", "record", "win", "winning",
    "support", "approve", "back", "invest", "investment", "growth", "jobs",
    "deal", "beautiful", "successful", "best", "powerful",
}

BEARISH_TERMS = {
    "bad", "terrible", "weak", "crash", "collapse", "fraud", "scam", "boycott",
    "ban", "blocked", "destroy", "disaster", "failing", "failed", "corrupt", "tax",
    "tariff", "tariffs", "penalty", "sanction", "sanctions", "inflation", "recession",
}

NEUTRAL_POLICY_TERMS = {
    "fed", "federal reserve", "interest rate", "interest rates", "rates", "dollar",
    "treasury", "trade", "china", "bank", "banks", "economy", "market",
}


@lru_cache(maxsize=512)
def _term_pattern(term: str) -> re.Pattern[str]:
    clean = normalize_text(term).lower()
    escaped = re.escape(clean)
    return re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])", re.IGNORECASE)


def _count_terms(text: str, terms: Iterable[str]) -> int:
    return sum(1 for term in terms if _term_pattern(term).search(text))


def classify_signal(text: str, match: EntityMatch | None = None) -> Classification:
    lower = normalize_text(text).lower()
    bullish = _count_terms(lower, BULLISH_TERMS)
    bearish = _count_terms(lower, BEARISH_TERMS)
    neutral = _count_terms(lower, NEUTRAL_POLICY_TERMS)

    if bullish > bearish and bullish >= 1:
        signal = "Bullish"
        confidence = "High" if bullish >= 2 or (match and match.direct) else "Medium"
        reason = "Positive wording near a detected market entity."
    elif bearish > bullish and bearish >= 1:
        signal = "Bearish"
        confidence = "High" if bearish >= 2 or (match and match.direct) else "Medium"
        reason = "Negative or restrictive wording near a detected market entity."
    elif neutral >= 1 or match:
        signal = "Neutral"
        confidence = "Medium" if match else "Low"
        reason = "Market-related mention without clear positive or negative wording."
    else:
        signal = "Unclear"
        confidence = "Low"
        reason = "Market relationship is weak or indirect."

    if match and match.direct:
        alert_type = "Direct mention"
    elif match:
        alert_type = "Inferred relationship"
    else:
        alert_type = "Unclear"

    return Classification(signal=signal, confidence=confidence, alert_type=alert_type, reason=reason)

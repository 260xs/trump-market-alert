from __future__ import annotations

import re

from database.models import Signal

STRONG_GOOD = [
    "one of the best", "the best", "amazing", "incredible", "fantastic", "great company",
    "great job", "doing an incredible job", "leading the future", "most important company",
    "bright future", "very strong", "stronger than ever", "winner", "winning", "tremendous",
    "excellent company", "dominant company", "world class", "doing very well", "very good",
]

STRONG_BAD = [
    "serious trouble", "in trouble", "failing", "failure", "scam", "fraud", "terrible company",
    "disaster", "very bad", "horrible", "should investigate", "investigate this company",
    "dangerous", "corrupt", "weak company", "going down", "collapse", "bankrupt",
    "major problem", "big problem", "not doing well", "doing very badly",
]

NEUTRAL_CONTEXT = [
    "met with", "meeting with", "talked with", "spoke with", "mentioned", "discussed", "visited",
]

REPORTED_CONTEXT = [
    "people are saying", "people say", "online are saying", "rumors", "rumor", "reportedly", "according to"
]

NEGATED_POSITIVE_RE = re.compile(
    r"\b(not|never|isn[\'’]?t|aren[\'’]?t|wasn[\'’]?t|weren[\'’]?t|no longer)\s+"
    r"(?:a\s+|an\s+|the\s+)?"
    r"(good|great|amazing|fantastic|incredible|excellent|strong|dominant|the best)\b",
    re.IGNORECASE,
)

NEGATED_NEGATIVE_RE = re.compile(
    r"\b(not|never|isn[\'’]?t|aren[\'’]?t|wasn[\'’]?t|weren[\'’]?t)\s+"
    r"(?:a\s+|an\s+|the\s+)?"
    r"(bad|terrible|failing|scam|fraud|dangerous|weak|bankrupt)\b",
    re.IGNORECASE,
)

POSITIVE_WORD_RE = re.compile(r"\b(great|amazing|fantastic|incredible|tremendous|excellent|dominant)\b", re.IGNORECASE)
NEGATIVE_WORD_RE = re.compile(r"\b(terrible|scam|fraud|failing|dangerous|disaster|bankrupt|corrupt)\b", re.IGNORECASE)


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

    if NEGATED_POSITIVE_RE.search(text):
        return Signal("Bad", "strong", 0.96, "A strong positive term is directly negated.")
    if NEGATED_NEGATIVE_RE.search(text):
        return Signal("Unclear", "mixed", 0.60, "A negative term is negated, but this is not a strong positive alert.")

    good = _contains_phrase(low, STRONG_GOOD)
    bad = _contains_phrase(low, STRONG_BAD)

    if good and bad:
        return Signal("Mixed", "mixed", 0.50, "Both strong positive and strong negative language found.")
    if good:
        return Signal("Good", "strong", 0.97, f"Strong positive phrase detected: {good}.")
    if bad:
        return Signal("Bad", "strong", 0.97, f"Strong negative phrase detected: {bad}.")

    if _contains_phrase(low, NEUTRAL_CONTEXT):
        return Signal("Neutral", "none", 0.90, "Neutral meeting/discussion wording, not a strong signal.")

    if POSITIVE_WORD_RE.search(text):
        return Signal("Good", "strong", 0.95, "Strong positive adjective near a direct asset mention.")
    if NEGATIVE_WORD_RE.search(text):
        return Signal("Bad", "strong", 0.95, "Strong negative adjective near a direct asset mention.")

    return Signal("Neutral", "none", 0.80, "No strong good or bad language detected.")

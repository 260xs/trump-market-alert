from __future__ import annotations

import re
from typing import Any

from .mapping import MappingIndex
from .models import AlertDecision, EntityHit
from .utils import clean_text, normalize_for_hash, stable_hash

MARKET_TERMS = [
    "stock", "stocks", "market", "markets", "nasdaq", "dow", "s&p", "s&p 500", "wall street",
    "bond", "bonds", "yield", "treasury", "dollar", "inflation", "recession", "economy", "economic",
    "earnings", "shares", "ipo", "ceo", "company", "companies", "bank", "banks", "banking",
    "fed", "federal reserve", "interest rate", "rates", "tariff", "tariffs", "trade", "chip", "chips",
    "semiconductor", "ai", "crypto", "cryptocurrency", "bitcoin", "ethereum", "btc", "eth", "oil", "gas",
    "energy", "gold", "silver", "commodity", "commodities", "steel", "autos", "ev", "defense",
    "pharma", "healthcare", "housing", "real estate", "tax", "taxes", "regulation", "sanction", "china",
]

QUOTE_RE = re.compile(r"[\"“‘']([^\"”’']{8,600})[\"”’']")
SENTENCE_RE = re.compile(r"[^.!?\n]{1,700}[.!?]")


def market_terms(text: str) -> list[str]:
    t = normalize_for_hash(text)
    found: list[str] = []
    for term in MARKET_TERMS:
        if re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", t):
            found.append(term)
    return found


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    out = [clean_text(x.group(0)) for x in SENTENCE_RE.finditer(text)]
    if not out and text:
        out = [text[:700]]
    return out


def extract_best_quote(text: str, hits: list[EntityHit], terms: list[str]) -> str:
    text = clean_text(text)
    quoted = [clean_text(m.group(1)) for m in QUOTE_RE.finditer(text)]
    if quoted:
        def score(q: str) -> int:
            ql = q.lower()
            s = 0
            for h in hits:
                if h.name.lower() in ql or h.matched_alias.lower() in ql:
                    s += 5
            for term in terms:
                if term.lower() in ql:
                    s += 2
            return s + min(len(q), 120) // 30
        return max(quoted, key=score)[:900]

    sentences = split_sentences(text)
    if not sentences:
        return text[:900]

    def sentence_score(s: str) -> int:
        sl = s.lower()
        score = 0
        for h in hits:
            if h.name.lower() in sl or h.matched_alias.lower() in sl:
                score += 5
        for term in terms:
            if term.lower() in sl:
                score += 2
        if "trump" in sl or "donald" in sl or "president" in sl:
            score += 1
        return score

    best = max(sentences, key=sentence_score)
    return best[:900]


def make_dedupe_key(source: str, source_id: str, quote: str, hits: list[EntityHit]) -> str:
    ents = ",".join(sorted(h.name for h in hits))
    return stable_hash(source, source_id, normalize_for_hash(quote), ents, n=40)


def decide(text: str, mapping: MappingIndex, source_type: str = "text") -> AlertDecision:
    clean = clean_text(text)
    hits = mapping.find(clean)
    terms = market_terms(clean)
    should = bool(hits or terms)
    quote = extract_best_quote(clean, hits, terms) if should else ""

    # If there is a market term but no mapped entity, keep a market/policy entity placeholder.
    if should and not hits:
        hits = []

    # Imported here to avoid circular import.
    from .classify import classify_signal

    signal, confidence, alert_type, reason = classify_signal(quote or clean, hits, terms, source_type)
    return AlertDecision(
        should_alert=should,
        quote=quote,
        entities=hits,
        signal=signal,
        confidence=confidence,
        alert_type=alert_type,
        reason=reason,
        market_terms=terms,
    )

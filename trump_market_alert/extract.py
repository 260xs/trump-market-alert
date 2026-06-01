from __future__ import annotations

import re
from dataclasses import replace
from urllib.parse import urlparse

from .classify import alert_type_for, classify_signal, contains_market_keyword, is_market_related
from .mapping import EntityMapper
from .models import Alert, Entity, Event
from .utils import chunk_text, domain_matches, normalize_for_hash, safe_truncate, sha256_text

QUOTE_RE = re.compile(r"[\"“”‘’']([^\"“”‘’']{6,500})[\"“”‘’']")


def candidate_quotes(ev: Event, min_chars: int, allow_article_snippets: bool, trusted_domains: list[str]) -> list[str]:
    text = ev.text or ""
    if not text.strip():
        return []

    if ev.kind in {"truth_social", "x_post", "youtube_transcript", "sample", "transcript"}:
        return chunk_text(text, max_chars=1100, overlap=120)

    if ev.kind in {"article", "rss"}:
        # Trusted transcript pages can be processed as source text. Generic news articles only pass quoted phrases.
        if domain_matches(ev.url, trusted_domains):
            return chunk_text(text, max_chars=1100, overlap=120)

        quotes = [q.strip() for q in QUOTE_RE.findall(text) if len(q.strip()) >= min_chars]
        if quotes:
            return quotes
        if allow_article_snippets:
            return chunk_text(text, max_chars=700, overlap=80)
        return []

    return chunk_text(text, max_chars=1100, overlap=120)


def build_alerts(
    ev: Event,
    mapper: EntityMapper,
    min_quote_chars: int,
    allow_article_snippets: bool,
    trusted_transcript_domains: list[str],
) -> list[Alert]:
    alerts: list[Alert] = []
    for quote in candidate_quotes(ev, min_quote_chars, allow_article_snippets, trusted_transcript_domains):
        if len(quote.strip()) < min_quote_chars:
            continue
        entities = mapper.detect(quote)
        if not is_market_related(quote, entities):
            continue
        if not entities and contains_market_keyword(quote):
            entities = [
                Entity(
                    name="Financial markets / macro",
                    kind="market",
                    aliases=[],
                    assets=[],
                    relation="direct",
                )
            ]
        signal, confidence, reason = classify_signal(quote, entities)
        typ = alert_type_for(entities)
        asset_key = ",".join(sorted({a.symbol for e in entities for a in e.assets}))
        ent_key = ",".join(sorted(e.name for e in entities))
        key = sha256_text(ev.src, ev.item_id, normalize_for_hash(quote), ent_key, asset_key)
        alerts.append(
            Alert(
                quote=quote,
                source_platform=ev.platform or ev.src,
                source_link=ev.url,
                published_at=ev.published_at,
                detected_at=ev.detected_at,
                entities=entities,
                signal=signal,
                confidence=confidence,
                alert_type=typ,
                dedupe_key=key,
                reason=reason,
            )
        )
    return alerts

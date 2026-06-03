from __future__ import annotations

import re
from difflib import SequenceMatcher

from database.db import hash_text
from database.models import Statement, EntityMatch, Signal


def normalize_quote(text: str) -> str:
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9$%\.\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def quote_hash(text: str) -> str:
    return hash_text(text.strip())


def normalized_quote_hash(text: str) -> str:
    return hash_text(normalize_quote(text))


def platform_key(stmt: Statement) -> str:
    if stmt.platform_item_id:
        return f"platform:{stmt.platform}:{stmt.platform_item_id}"
    return f"source_url:{stmt.source_url}"


def alert_duplicate_key(stmt: Statement, entity: EntityMatch, signal: Signal) -> str:
    # Deliberately exclude source URL/post ID so the same quote repeated by
    # multiple outlets does not send multiple Telegram alerts.
    normalized = normalize_quote(stmt.statement_text)
    day = stmt.published_at.date().isoformat()
    base = f"{stmt.speaker_name}|{entity.ticker}|{signal.signal}|{day}|{normalized}"
    return hash_text(base)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_quote(a), normalize_quote(b)).ratio()

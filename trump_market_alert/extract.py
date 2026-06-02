from __future__ import annotations

import hashlib
import html
import re
from typing import Iterable

from bs4 import BeautifulSoup

WHITESPACE_RE = re.compile(r"\s+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
TRUMP_RE = re.compile(r"\b(Donald\s+Trump|President\s+Trump|Trump|realDonaldTrump)\b", re.IGNORECASE)


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "lxml")
    text = soup.get_text(" ")
    return normalize_text(html.unescape(text))


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(str(value))
    value = value.replace("\u201c", '"').replace("\u201d", '"')
    value = value.replace("\u2018", "'").replace("\u2019", "'")
    return WHITESPACE_RE.sub(" ", value).strip()


def contains_trump_reference(text: str) -> bool:
    return bool(TRUMP_RE.search(text or ""))


def stable_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update((part or "").encode("utf-8", errors="ignore"))
        h.update(b"\x1f")
    return h.hexdigest()


def _term_positions(text_lower: str, terms: Iterable[str]) -> list[int]:
    positions: list[int] = []
    for term in terms:
        t = normalize_text(term).lower()
        if len(t) < 3:
            continue
        idx = text_lower.find(t)
        if idx >= 0:
            positions.append(idx)
    return positions


def best_quote(text: str, terms: Iterable[str], max_chars: int = 650) -> str:
    clean = normalize_text(text)
    if len(clean) <= max_chars:
        return clean

    text_lower = clean.lower()
    positions = _term_positions(text_lower, terms)
    center = min(positions) if positions else 0

    start = max(0, center - max_chars // 3)
    end = min(len(clean), start + max_chars)
    excerpt = clean[start:end]

    # Try to avoid cutting the first and last sentence badly.
    if start > 0:
        first_space = excerpt.find(" ")
        if first_space > 0:
            excerpt = excerpt[first_space + 1 :]
        excerpt = "..." + excerpt
    if end < len(clean):
        last_space = excerpt.rfind(" ")
        if last_space > max_chars * 0.75:
            excerpt = excerpt[:last_space]
        excerpt = excerpt + "..."

    return normalize_text(excerpt)


def split_sentences(text: str) -> list[str]:
    clean = normalize_text(text)
    if not clean:
        return []
    return [s.strip() for s in SENTENCE_RE.split(clean) if s.strip()]

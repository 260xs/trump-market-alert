from __future__ import annotations

import hashlib
import html
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

LOG_FMT = "%(asctime)s %(levelname)s %(name)s - %(message)s"


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=LOG_FMT)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            dt = date_parser.parse(value)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    try:
        # feedparser published_parsed is a time.struct_time.
        dt = parsedate_to_datetime(str(value))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def clean_html(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "html.parser")
    text = soup.get_text(" ")
    return normalize_ws(html.unescape(text))


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_for_hash(value: str) -> str:
    value = normalize_ws(value).lower()
    value = re.sub(r"[^a-z0-9$]+", " ", value)
    return normalize_ws(value)


def sha256_text(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update((part or "").encode("utf-8", errors="ignore"))
        h.update(b"\x00")
    return h.hexdigest()


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def domain_matches(url: str, domains: Iterable[str]) -> bool:
    host = domain_of(url)
    for d in domains:
        d = d.lower().strip()
        if host == d or host.endswith("." + d):
            return True
    return False


def chunk_text(text: str, max_chars: int = 1100, overlap: int = 120) -> list[str]:
    text = normalize_ws(text)
    if len(text) <= max_chars:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            # Prefer breaking on sentence/punctuation near the end.
            cut = max(text.rfind(". ", start, end), text.rfind("? ", start, end), text.rfind("! ", start, end))
            if cut > start + int(max_chars * 0.55):
                end = cut + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return [c for c in chunks if c]


def safe_truncate(text: str, max_chars: int) -> str:
    text = text or ""
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1].rstrip()
    return cut + "…"

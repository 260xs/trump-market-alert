from __future__ import annotations

import hashlib
import html
import json
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from bs4 import BeautifulSoup
from dateutil import parser as dtparser

LOGGER = logging.getLogger("trump_market_alert")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        # RSS dates often parse better through email.utils.
        if isinstance(value, str) and "," in value:
            return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        pass
    try:
        dt = dtparser.parse(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def clean_html(value: str | None) -> str:
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ")
    return clean_text(text)


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def stable_hash(*parts: Any, n: int = 32) -> str:
    h = hashlib.sha256()
    for part in parts:
        if isinstance(part, (dict, list)):
            data = json.dumps(part, sort_keys=True, default=str)
        else:
            data = "" if part is None else str(part)
        h.update(data.encode("utf-8", errors="ignore"))
        h.update(b"\x1e")
    return h.hexdigest()[:n]


def normalize_for_hash(text: str) -> str:
    text = clean_text(text).lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^a-z0-9$%]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, max_len: int = 3800) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        cut = remaining.rfind("\n", 0, max_len)
        if cut < 500:
            cut = max_len
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return chunks


def safe_get(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = d
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

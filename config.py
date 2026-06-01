from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class SourceItem:
    source: str
    source_id: str
    platform: str
    text: str
    url: str
    published_at: datetime | None = None
    detected_at: datetime = field(default_factory=utc_now)
    author: str = "Donald Trump / public source"
    source_type: str = "text"  # text, transcript, live_audio, news
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Asset:
    symbol: str
    kind: str
    explanation: str


@dataclass(slots=True)
class EntityHit:
    name: str
    kind: str
    matched_alias: str
    start: int
    end: int
    assets: list[Asset]


@dataclass(slots=True)
class AlertDecision:
    should_alert: bool
    quote: str
    entities: list[EntityHit]
    signal: str
    confidence: str
    alert_type: str
    reason: str
    market_terms: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AlertRecord:
    dedupe_key: str
    item: SourceItem
    decision: AlertDecision

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Event:
    src: str
    item_id: str
    text: str
    url: str
    published_at: datetime | None = None
    detected_at: datetime = field(default_factory=utc_now)
    kind: str = "post"
    platform: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Asset:
    symbol: str
    type: str
    explanation: str = ""


@dataclass(slots=True)
class Entity:
    name: str
    kind: str
    aliases: list[str]
    assets: list[Asset]
    relation: str = "direct"


@dataclass(slots=True)
class Alert:
    quote: str
    source_platform: str
    source_link: str
    published_at: datetime | None
    detected_at: datetime
    entities: list[Entity]
    signal: str
    confidence: str
    alert_type: str
    dedupe_key: str
    reason: str = ""

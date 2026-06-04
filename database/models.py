from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Person:
    id: str
    full_name: str
    aliases: list[str]
    role: str
    category: str
    market_impact_score: int
    enabled: bool
    allow_telegram_alerts: bool


@dataclass
class SourceConfig:
    id: str
    person_id: str
    platform: str
    source_type: str
    url: str = ""
    priority: str = "medium"
    enabled: bool = True
    polling_interval_seconds: int = 600
    source_confidence: float = 0.80
    speaker_confidence: float = 0.95
    channel_id: str = ""
    expected_speaker: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Statement:
    person_id: str
    source_id: str
    speaker_name: str
    statement_text: str
    source_url: str
    platform: str
    published_at: datetime
    detected_at: datetime
    source_confidence: float
    speaker_confidence: float
    quote_confidence: float
    source_type: str = "unknown"
    platform_item_id: str = ""
    transcript_timestamp: str = ""
    live_offset_seconds: int | None = None
    is_live: bool = False
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityMatch:
    entity_name: str
    entity_type: str
    mapped_name: str
    ticker: str
    asset_type: str
    entity_confidence: float
    direct_or_inferred: str
    reason: str


@dataclass
class Signal:
    signal: str
    strength: str
    confidence: float
    reason: str


@dataclass
class AlertDecision:
    should_send: bool
    lane: str
    reason: str
    duplicate_key: str
    entity: EntityMatch | None = None
    signal: Signal | None = None

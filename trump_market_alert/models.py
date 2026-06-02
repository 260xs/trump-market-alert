from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class SourceItem:
    source_name: str
    source_type: str
    item_id: str
    title: str
    text: str
    url: str
    published_at: datetime | None = None
    author: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def published_at_utc(self) -> datetime | None:
        return ensure_utc(self.published_at)


@dataclass(frozen=True)
class RelatedAsset:
    symbol: str
    asset_type: str
    name: str
    relationship: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RelatedAsset":
        return cls(
            symbol=str(data.get("symbol", "")).strip(),
            asset_type=str(data.get("asset_type", "asset")).strip(),
            name=str(data.get("name", "")).strip(),
            relationship=str(data.get("relationship", "related")).strip(),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "symbol": self.symbol,
            "asset_type": self.asset_type,
            "name": self.name,
            "relationship": self.relationship,
        }


@dataclass(frozen=True)
class EntityMatch:
    entity_id: str
    name: str
    entity_type: str
    matched_alias: str
    related_assets: list[RelatedAsset]
    direct: bool = True


@dataclass(frozen=True)
class Classification:
    signal: str
    confidence: str
    alert_type: str
    reason: str


@dataclass(frozen=True)
class Alert:
    fingerprint: str
    quote: str
    source_name: str
    source_type: str
    source_url: str
    time_published: datetime | None
    time_detected: datetime
    entity_name: str
    entity_type: str
    matched_alias: str
    related_assets: list[RelatedAsset]
    signal: str
    confidence: str
    alert_type: str
    reason: str

    def assets_as_dicts(self) -> list[dict[str, str]]:
        return [asset.to_dict() for asset in self.related_assets]

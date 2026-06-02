from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .extract import normalize_text
from .models import EntityMatch, RelatedAsset


@dataclass(frozen=True)
class EntityDefinition:
    entity_id: str
    name: str
    entity_type: str
    aliases: list[str]
    related_assets: list[RelatedAsset]


@lru_cache(maxsize=2048)
def _bounded_pattern(term: str) -> re.Pattern[str]:
    clean = normalize_text(term)
    escaped = re.escape(clean)
    return re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])", re.IGNORECASE)


class EntityMapper:
    def __init__(self, entities: list[EntityDefinition], market_keywords: list[str]) -> None:
        self.entities = entities
        self.market_keywords = [normalize_text(k) for k in market_keywords if normalize_text(k)]
        self._market_patterns = [_bounded_pattern(k) for k in self.market_keywords if len(k) >= 2]
        self._patterns: list[tuple[re.Pattern[str], EntityDefinition, str]] = []
        for entity in entities:
            for alias in entity.aliases:
                clean_alias = normalize_text(alias)
                if len(clean_alias) < 2:
                    continue
                pattern = _bounded_pattern(clean_alias)
                self._patterns.append((pattern, entity, clean_alias))

    @classmethod
    def from_config(cls, data: dict[str, Any]) -> "EntityMapper":
        raw_entities = data.get("entities", []) or []
        entities: list[EntityDefinition] = []
        for raw in raw_entities:
            if not isinstance(raw, dict):
                continue
            assets = [RelatedAsset.from_dict(a) for a in raw.get("related_assets", []) or [] if isinstance(a, dict)]
            aliases = [str(a) for a in raw.get("aliases", []) or []]
            name = str(raw.get("name", "")).strip()
            if name and name not in aliases:
                aliases.append(name)
            entity_id = str(raw.get("id", name)).strip() or name
            if not entity_id or not name:
                continue
            entities.append(
                EntityDefinition(
                    entity_id=entity_id,
                    name=name,
                    entity_type=str(raw.get("type", "entity")).strip() or "entity",
                    aliases=aliases,
                    related_assets=assets,
                )
            )
        keywords = [str(k) for k in data.get("market_keywords", []) or []]
        return cls(entities=entities, market_keywords=keywords)

    def has_market_context(self, text: str) -> bool:
        clean = normalize_text(text)
        return any(pattern.search(clean) for pattern in self._market_patterns)

    def match(self, text: str, limit: int = 6) -> list[EntityMatch]:
        found: list[tuple[int, EntityMatch]] = []
        seen: set[str] = set()
        clean_text = text or ""
        for pattern, entity, alias in self._patterns:
            m = pattern.search(clean_text)
            if not m or entity.entity_id in seen:
                continue
            seen.add(entity.entity_id)
            found.append(
                (
                    m.start(),
                    EntityMatch(
                        entity_id=entity.entity_id,
                        name=entity.name,
                        entity_type=entity.entity_type,
                        matched_alias=alias,
                        related_assets=entity.related_assets,
                        direct=True,
                    ),
                )
            )
        found.sort(key=lambda x: x[0])
        return [match for _, match in found[:limit]]

    def generic_market_match(self) -> EntityMatch:
        return EntityMatch(
            entity_id="general_market",
            name="General market / macro policy",
            entity_type="macro",
            matched_alias="market context",
            related_assets=[
                RelatedAsset(symbol="SPY", asset_type="etf", name="SPDR S&P 500 ETF Trust", relationship="broad_market_proxy"),
                RelatedAsset(symbol="QQQ", asset_type="etf", name="Invesco QQQ Trust", relationship="tech_market_proxy"),
            ],
            direct=False,
        )

    def all_terms_for_quote(self, match: EntityMatch | None = None) -> list[str]:
        terms = list(self.market_keywords)
        if match:
            terms.extend([match.name, match.matched_alias])
            terms.extend(asset.symbol for asset in match.related_assets)
        return terms

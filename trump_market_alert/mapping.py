from __future__ import annotations

import logging
import re
from pathlib import Path

from .config import load_yaml
from .models import Asset, Entity

log = logging.getLogger(__name__)


class EntityMapper:
    def __init__(self, entities: list[Entity]):
        self.entities = entities
        self._patterns: list[tuple[re.Pattern[str], Entity, str]] = []
        for ent in entities:
            for alias in ent.aliases:
                pat = self._alias_pattern(alias)
                self._patterns.append((re.compile(pat, re.IGNORECASE), ent, alias))

    @classmethod
    def from_yaml(cls, path: Path) -> "EntityMapper":
        data = load_yaml(path)
        entities: list[Entity] = []
        for item in data.get("entities", []):
            assets = [Asset(symbol=str(a.get("symbol", "")).upper(), type=str(a.get("type", "")), explanation=str(a.get("explanation", ""))) for a in item.get("assets", [])]
            ent = Entity(
                name=str(item.get("name", "")),
                kind=str(item.get("kind", "unknown")),
                aliases=[str(a) for a in item.get("aliases", [])],
                assets=assets,
                relation=str(item.get("relation", "direct")),
            )
            if ent.name and ent.aliases:
                entities.append(ent)
        log.info("loaded %d entity mappings", len(entities))
        return cls(entities)

    @staticmethod
    def _alias_pattern(alias: str) -> str:
        escaped = re.escape(alias.strip())
        # For normal words, require word boundaries. For aliases beginning with $, do not.
        if alias.startswith("$"):
            return rf"(?<!\w){escaped}(?!\w)"
        if re.fullmatch(r"[A-Za-z0-9.]+", alias):
            return rf"\b{escaped}\b"
        return rf"(?<!\w){escaped}(?!\w)"

    def detect(self, text: str) -> list[Entity]:
        found: dict[str, Entity] = {}
        for pat, ent, _alias in self._patterns:
            if pat.search(text or ""):
                found[ent.name] = ent
        return list(found.values())

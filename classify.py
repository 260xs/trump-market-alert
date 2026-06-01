from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .models import Asset, EntityHit
from .utils import clean_text


@dataclass(slots=True)
class EntityMapping:
    name: str
    kind: str
    aliases: list[str]
    assets: list[Asset]


class MappingIndex:
    def __init__(self, config: dict[str, Any]):
        self.entities: list[EntityMapping] = []
        for row in config.get("entities", []) or []:
            assets = [Asset(symbol=str(a.get("symbol", "")).strip(), kind=str(a.get("kind", "ticker")), explanation=str(a.get("explanation", ""))) for a in row.get("assets", []) or []]
            aliases = [str(x).strip() for x in row.get("aliases", []) if str(x).strip()]
            name = str(row.get("name", "")).strip()
            if name and name not in aliases:
                aliases.insert(0, name)
            self.entities.append(EntityMapping(name=name, kind=str(row.get("kind", "entity")), aliases=aliases, assets=assets))

        alias_patterns: list[tuple[re.Pattern[str], EntityMapping, str]] = []
        for ent in self.entities:
            for alias in ent.aliases:
                if not alias:
                    continue
                escaped = re.escape(alias)
                # Use custom boundaries so aliases like X, Fed, oil, $TSLA still work.
                pat = re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])", re.IGNORECASE)
                alias_patterns.append((pat, ent, alias))
        alias_patterns.sort(key=lambda x: len(x[2]), reverse=True)
        self.alias_patterns = alias_patterns

    def find(self, text: str, limit: int = 12) -> list[EntityHit]:
        text = clean_text(text)
        hits: list[EntityHit] = []
        seen: set[str] = set()
        occupied: list[tuple[int, int]] = []
        for pat, ent, alias in self.alias_patterns:
            if ent.name in seen:
                continue
            m = pat.search(text)
            if not m:
                continue
            if any(not (m.end() <= a or m.start() >= b) for a, b in occupied):
                continue
            hits.append(EntityHit(ent.name, ent.kind, m.group(0), m.start(), m.end(), ent.assets))
            seen.add(ent.name)
            occupied.append((m.start(), m.end()))
            if len(hits) >= limit:
                break
        return sorted(hits, key=lambda h: h.start)

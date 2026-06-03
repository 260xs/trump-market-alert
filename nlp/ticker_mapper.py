from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from database.models import EntityMatch


@dataclass(frozen=True)
class AssetRule:
    canonical: str
    aliases: list[str]
    ticker: str
    asset_type: str
    confidence: float
    direct_patterns: list[str]
    avoid_contexts: list[str]
    required_context_any: list[str]


class TickerMapper:
    def __init__(self, asset_map: dict[str, Any]):
        self.rules: list[AssetRule] = []
        for item in asset_map.get("assets", []):
            self.rules.append(
                AssetRule(
                    canonical=item["canonical"],
                    aliases=item.get("aliases", []),
                    ticker=item["ticker"],
                    asset_type=item.get("asset_type", "unknown"),
                    confidence=float(item.get("confidence", 0.95)),
                    direct_patterns=item.get("direct_patterns", []),
                    avoid_contexts=[x.lower() for x in item.get("avoid_contexts", [])],
                    required_context_any=[x.lower() for x in item.get("required_context_any", [])],
                )
            )
        self.blocked = asset_map.get("blocked_ambiguous", [])

    def _blocked_ambiguous(self, text: str) -> str | None:
        for blocked in self.blocked:
            for pattern in blocked.get("patterns", []):
                if re.search(pattern, text, re.IGNORECASE):
                    return blocked.get("reason", "Ambiguous entity")
        return None

    def map_direct_entities(self, text: str) -> list[EntityMatch]:
        matches: list[EntityMatch] = []
        low = text.lower()

        blocked_reason = self._blocked_ambiguous(text)
        if blocked_reason:
            # Do not return anything. Ambiguous entities are stored as ignored by the pipeline.
            return []

        for rule in self.rules:
            if any(ctx in low for ctx in rule.avoid_contexts):
                continue
            if rule.required_context_any and not any(ctx in low for ctx in rule.required_context_any):
                continue

            for pattern in rule.direct_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    entity_name = self._matched_alias(text, rule.aliases) or rule.canonical
                    matches.append(
                        EntityMatch(
                            entity_name=entity_name,
                            entity_type=rule.asset_type,
                            mapped_name=rule.canonical,
                            ticker=rule.ticker,
                            asset_type=rule.asset_type,
                            entity_confidence=rule.confidence,
                            direct_or_inferred="direct",
                            reason=f"Direct mention mapped to {rule.canonical} ({rule.ticker}).",
                        )
                    )
                    break
        return self._dedupe(matches)

    @staticmethod
    def _matched_alias(text: str, aliases: list[str]) -> str | None:
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE):
                return alias
        return None

    @staticmethod
    def _dedupe(matches: list[EntityMatch]) -> list[EntityMatch]:
        out: list[EntityMatch] = []
        seen: set[str] = set()
        for m in matches:
            if m.ticker not in seen:
                seen.add(m.ticker)
                out.append(m)
        return out

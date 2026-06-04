from __future__ import annotations

from database.models import EntityMatch
from nlp.ticker_mapper import TickerMapper


class EntityExtractor:
    def __init__(self, mapper: TickerMapper):
        self.mapper = mapper

    def extract(self, text: str) -> list[EntityMatch]:
        return self.mapper.map_direct_entities(text)

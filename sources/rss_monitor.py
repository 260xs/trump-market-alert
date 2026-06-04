from __future__ import annotations

from datetime import timezone

import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from database.models import SourceConfig, Statement
from sources.base import SourceMonitor, utc_now


class RssMonitor(SourceMonitor):
    def fetch(self) -> list[Statement]:
        feed = feedparser.parse(self.source.url)
        out: list[Statement] = []
        for entry in feed.entries[:20]:
            title = getattr(entry, "title", "") or ""
            summary = getattr(entry, "summary", "") or ""
            text = f"{title}. {self._clean(summary)}".strip()
            link = getattr(entry, "link", self.source.url)
            published = self._published(entry)
            out.append(
                Statement(
                    person_id=self.source.person_id,
                    source_id=self.source.id,
                    speaker_name=self.source.extra.get("person_name", self.source.person_id),
                    statement_text=text,
                    source_url=link,
                    platform=self.source.platform,
                    published_at=published,
                    detected_at=utc_now(),
                    source_confidence=self.source.source_confidence,
                    speaker_confidence=0.75,
                    quote_confidence=0.70,
                    source_type=self.source.source_type,
                    platform_item_id=getattr(entry, "id", link),
                    raw_metadata={"title": title},
                )
            )
        return out

    @staticmethod
    def _clean(html: str) -> str:
        return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)

    @staticmethod
    def _published(entry) -> object:
        for key in ("published", "updated"):
            value = getattr(entry, key, None)
            if value:
                try:
                    dt = date_parser.parse(value)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.astimezone(timezone.utc)
                except Exception:
                    pass
        return utc_now()

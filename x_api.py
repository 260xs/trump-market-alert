from __future__ import annotations

import logging
from typing import Any

import feedparser

from trump_market_alert.models import SourceItem
from trump_market_alert.utils import clean_html, clean_text, parse_dt, stable_hash
from .base import BaseSource

LOG = logging.getLogger(__name__)


class RSSSource(BaseSource):
    name = "rss"

    def __init__(self, feeds: list[dict[str, Any]], timeout: int = 20):
        self.feeds = feeds
        self.timeout = timeout

    def fetch(self) -> list[SourceItem]:
        items: list[SourceItem] = []
        for feed in self.feeds:
            if not feed.get("enabled", True):
                continue
            name = str(feed.get("name") or feed.get("url"))
            url = str(feed.get("url"))
            try:
                parsed = feedparser.parse(url)
                for entry in parsed.entries[: int(feed.get("limit", 15))]:
                    link = str(getattr(entry, "link", "") or "")
                    title = clean_text(getattr(entry, "title", ""))
                    summary = clean_html(getattr(entry, "summary", ""))
                    text = clean_text(f"{title}. {summary}")
                    if not text:
                        continue
                    source_id = clean_text(str(getattr(entry, "id", "") or link or stable_hash(name, text)))
                    published = parse_dt(getattr(entry, "published", None) or getattr(entry, "updated", None))
                    items.append(
                        SourceItem(
                            source=f"rss:{name}",
                            source_id=source_id,
                            platform=name,
                            text=text,
                            url=link or url,
                            published_at=published,
                            source_type="rss_news" if "news" in name.lower() or "google" in name.lower() else "text",
                            raw={"feed": url, "entry": dict(entry)},
                        )
                    )
            except Exception as exc:
                LOG.exception("RSS source failed for %s: %s", name, exc)
        return items

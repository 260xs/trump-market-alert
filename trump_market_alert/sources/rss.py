from __future__ import annotations

import logging
from collections.abc import Iterable

import feedparser
import requests
from bs4 import BeautifulSoup

from ..models import Event
from ..utils import clean_html, domain_of, now_utc, normalize_ws, parse_dt, sha256_text
from .base import Source

log = logging.getLogger(__name__)


class RssSource(Source):
    def __init__(self, name: str, url: str, fetch_article: bool = False):
        self.name = name
        self.url = url
        self.fetch_article = fetch_article
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "trump-market-alert/1.0 (+public monitoring)"})

    def fetch(self, limit: int = 20) -> Iterable[Event]:
        try:
            feed = feedparser.parse(self.url)
        except Exception as e:
            log.warning("RSS fetch failed for %s: %s", self.name, e)
            return []
        events: list[Event] = []
        for entry in (feed.entries or [])[:limit]:
            link = str(getattr(entry, "link", "") or "")
            eid = str(getattr(entry, "id", "") or getattr(entry, "guid", "") or link or sha256_text(self.name, str(entry)))
            title = clean_html(str(getattr(entry, "title", "") or ""))
            summary = clean_html(str(getattr(entry, "summary", "") or ""))
            text = normalize_ws(f"{title}. {summary}")
            kind = "rss"
            raw_text = text
            if self.fetch_article and link:
                article_text = self._fetch_article_text(link)
                if article_text:
                    text = article_text
                    kind = "article"
            if not text:
                continue
            events.append(
                Event(
                    src=f"rss:{self.name}",
                    platform=self.name,
                    item_id=eid,
                    text=text,
                    url=link or self.url,
                    published_at=parse_dt(getattr(entry, "published", None) or getattr(entry, "updated", None)),
                    detected_at=now_utc(),
                    kind=kind,
                    meta={"feed_url": self.url, "title": title, "summary": summary, "rss_text": raw_text},
                    raw=dict(entry),
                )
            )
        return events

    def _fetch_article_text(self, link: str) -> str:
        try:
            r = self.s.get(link, timeout=20)
            if r.status_code != 200 or not r.text:
                return ""
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                tag.decompose()
            parts = []
            for selector in ["article", "main", "body"]:
                node = soup.select_one(selector)
                if node:
                    for p in node.find_all(["h1", "h2", "p", "li"]):
                        txt = normalize_ws(p.get_text(" "))
                        if len(txt) > 20:
                            parts.append(txt)
                    break
            return normalize_ws(" ".join(parts))[:20000]
        except Exception as e:
            log.debug("article fetch failed for %s: %s", link, e)
            return ""

from __future__ import annotations

from datetime import timezone

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from database.models import SourceConfig, Statement
from sources.base import SourceMonitor, utc_now


class TruthSocialMonitor(SourceMonitor):
    """Best-effort public Truth Social monitor.

    This monitor intentionally avoids private APIs, login bypasses, and scraping tricks.
    If a configured URL returns JSON status objects, it parses them. If it returns a
    public HTML page, it extracts visible text conservatively. If the platform blocks
    access, the source returns no statements instead of bypassing access controls.
    """

    def fetch(self) -> list[Statement]:
        if not self.source.url:
            return []
        headers = {"User-Agent": "PublicFigureMarketAlert/1.0 public-source-monitor"}
        response = requests.get(self.source.url, headers=headers, timeout=20)
        if response.status_code in {401, 403, 404}:
            return []
        response.raise_for_status()
        ctype = response.headers.get("content-type", "")
        if "json" in ctype:
            return self._from_json(response.json())
        return self._from_html(response.text)

    def _from_json(self, data) -> list[Statement]:
        items = data if isinstance(data, list) else data.get("statuses", []) if isinstance(data, dict) else []
        out: list[Statement] = []
        for item in items[:20]:
            if not isinstance(item, dict):
                continue
            content = BeautifulSoup(item.get("content", ""), "html.parser").get_text(" ", strip=True)
            if not content:
                continue
            created = item.get("created_at")
            published = utc_now()
            if created:
                try:
                    dt = date_parser.parse(created)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    published = dt.astimezone(timezone.utc)
                except Exception:
                    pass
            url = item.get("url") or self.source.url
            out.append(
                Statement(
                    person_id=self.source.person_id,
                    source_id=self.source.id,
                    speaker_name=self.source.extra.get("person_name", self.source.person_id),
                    statement_text=content,
                    source_url=url,
                    platform=self.source.platform,
                    published_at=published,
                    detected_at=utc_now(),
                    source_confidence=self.source.source_confidence,
                    speaker_confidence=0.98,
                    quote_confidence=0.98,
                    source_type=self.source.source_type,
                    platform_item_id=str(item.get("id", url)),
                    raw_metadata={"truthsocial": True},
                )
            )
        return out

    def _from_html(self, html: str) -> list[Statement]:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        if not text:
            return []
        return [
            Statement(
                person_id=self.source.person_id,
                source_id=self.source.id,
                speaker_name=self.source.extra.get("person_name", self.source.person_id),
                statement_text=text[:2000],
                source_url=self.source.url,
                platform=self.source.platform,
                published_at=utc_now(),
                detected_at=utc_now(),
                source_confidence=min(self.source.source_confidence, 0.85),
                speaker_confidence=0.80,
                quote_confidence=0.65,
                source_type=self.source.source_type,
                platform_item_id=self.source.url,
                raw_metadata={"html_fallback": True},
            )
        ]

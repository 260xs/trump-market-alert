from __future__ import annotations

import re
from datetime import timezone

import feedparser
from dateutil import parser as date_parser

from database.models import SourceConfig, Statement
from sources.base import SourceMonitor, utc_now


VIDEO_RE = re.compile(r"video:([A-Za-z0-9_-]+)")


class YouTubeMonitor(SourceMonitor):
    def fetch(self) -> list[Statement]:
        if not self.source.channel_id:
            return []
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={self.source.channel_id}"
        feed = feedparser.parse(url)
        out: list[Statement] = []
        for entry in feed.entries[:10]:
            video_id = self._video_id(getattr(entry, "id", ""), getattr(entry, "link", ""))
            link = getattr(entry, "link", f"https://www.youtube.com/watch?v={video_id}")
            title = getattr(entry, "title", "") or ""
            published = self._published(entry)
            text = title
            transcript = self._try_transcript(video_id)
            if transcript:
                text = transcript
            out.append(
                Statement(
                    person_id=self.source.person_id,
                    source_id=self.source.id,
                    speaker_name=self.source.extra.get("person_name", self.source.person_id),
                    statement_text=text,
                    source_url=link,
                    platform="YouTube",
                    published_at=published,
                    detected_at=utc_now(),
                    source_confidence=self.source.source_confidence,
                    speaker_confidence=0.85 if transcript else 0.70,
                    quote_confidence=0.90 if transcript else 0.60,
                    source_type=self.source.source_type,
                    platform_item_id=video_id,
                    raw_metadata={"title": title, "has_transcript": bool(transcript)},
                )
            )
        return out

    @staticmethod
    def _video_id(raw_id: str, link: str) -> str:
        match = VIDEO_RE.search(raw_id or "")
        if match:
            return match.group(1)
        if "v=" in link:
            return link.split("v=", 1)[1].split("&", 1)[0]
        return raw_id or link

    @staticmethod
    def _published(entry) -> object:
        value = getattr(entry, "published", None) or getattr(entry, "updated", None)
        if value:
            try:
                dt = date_parser.parse(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
        return utc_now()

    @staticmethod
    def _try_transcript(video_id: str) -> str:
        if not video_id:
            return ""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
        except Exception:
            return ""
        try:
            api = YouTubeTranscriptApi()
            fetched = api.fetch(video_id)
            snippets = getattr(fetched, "snippets", fetched)
            parts = []
            for item in snippets[:80]:
                text = getattr(item, "text", None)
                if text is None and isinstance(item, dict):
                    text = item.get("text")
                if text:
                    parts.append(str(text))
            return " ".join(parts).strip()
        except Exception:
            return ""

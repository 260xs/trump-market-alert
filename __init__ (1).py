from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import feedparser

from trump_market_alert.models import SourceItem
from trump_market_alert.utils import clean_html, clean_text, parse_dt, stable_hash
from .base import BaseSource

LOG = logging.getLogger(__name__)
YT_VIDEO_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{8,})")


class YouTubeSource(BaseSource):
    name = "youtube"

    def __init__(self, channels: list[dict[str, Any]], transcript_enabled: bool = True, transcript_max_age_hours: int = 96):
        self.channels = channels
        self.transcript_enabled = transcript_enabled
        self.transcript_max_age = timedelta(hours=transcript_max_age_hours)

    def fetch(self) -> list[SourceItem]:
        items: list[SourceItem] = []
        for ch in self.channels:
            if not ch.get("enabled", True):
                continue
            name = str(ch.get("name") or "YouTube")
            feed_url = str(ch.get("feed_url") or "")
            channel_id = ch.get("channel_id")
            if not feed_url and channel_id:
                feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            if not feed_url:
                continue
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[: int(ch.get("limit", 10))]:
                    link = str(getattr(entry, "link", "") or "")
                    title = clean_text(getattr(entry, "title", ""))
                    summary = clean_html(getattr(entry, "summary", ""))
                    published = parse_dt(getattr(entry, "published", None) or getattr(entry, "updated", None))
                    vid = _video_id(link) or stable_hash(feed_url, link, title)
                    text = clean_text(f"{title}. {summary}")
                    if text:
                        items.append(
                            SourceItem(
                                source=f"youtube:{name}",
                                source_id=f"video:{vid}",
                                platform=f"YouTube - {name}",
                                author=name,
                                text=text,
                                url=link,
                                published_at=published,
                                source_type="text",
                                raw={"feed": feed_url, "entry": dict(entry)},
                            )
                        )
                    if self.transcript_enabled and vid and _fresh_enough(published, self.transcript_max_age):
                        items.extend(_transcript_items(name, vid, link, published))
            except Exception as exc:
                LOG.exception("YouTube source failed for %s: %s", name, exc)
        return items


def _video_id(link: str) -> str | None:
    m = YT_VIDEO_RE.search(link)
    return m.group(1) if m else None


def _fresh_enough(published: datetime | None, max_age: timedelta) -> bool:
    if published is None:
        return True
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - published.astimezone(timezone.utc) <= max_age


def _transcript_items(channel_name: str, video_id: str, link: str, published: datetime | None) -> list[SourceItem]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except Exception:
        LOG.info("youtube-transcript-api not installed; transcripts skipped.")
        return []

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])
    except Exception as exc:
        LOG.info("No transcript for YouTube video %s: %s", video_id, exc)
        return []

    items: list[SourceItem] = []
    buf: list[str] = []
    start = 0.0
    chunk_idx = 0
    for row in transcript:
        if not buf:
            start = float(row.get("start", 0.0))
        buf.append(clean_text(str(row.get("text", ""))))
        if len(" ".join(buf)) >= 900:
            txt = clean_text(" ".join(buf))
            if txt:
                items.append(_mk_transcript_item(channel_name, video_id, link, published, chunk_idx, start, txt))
                chunk_idx += 1
            buf = []
    if buf:
        txt = clean_text(" ".join(buf))
        if txt:
            items.append(_mk_transcript_item(channel_name, video_id, link, published, chunk_idx, start, txt))
    return items


def _mk_transcript_item(channel_name: str, video_id: str, link: str, published: datetime | None, idx: int, start: float, txt: str) -> SourceItem:
    start_sec = max(0, int(start))
    url = f"{link}&t={start_sec}s" if "?" in link else f"{link}?t={start_sec}s"
    return SourceItem(
        source=f"youtube_transcript:{channel_name}",
        source_id=f"{video_id}:chunk:{idx}",
        platform=f"YouTube Transcript - {channel_name}",
        author=channel_name,
        text=txt,
        url=url,
        published_at=published,
        source_type="transcript",
        raw={"video_id": video_id, "chunk": idx, "start": start},
    )

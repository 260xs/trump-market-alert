from __future__ import annotations

import logging
from collections.abc import Iterable
from urllib.parse import parse_qs, urlparse

import feedparser

from ..models import Event
from ..utils import chunk_text, clean_html, now_utc, normalize_ws, parse_dt
from .base import Source

log = logging.getLogger(__name__)


class YouTubeSource(Source):
    def __init__(self, name: str, channel_id: str, check_transcripts: bool = True, languages: list[str] | None = None):
        self.name = name
        self.channel_id = channel_id
        self.check_transcripts = check_transcripts
        self.languages = languages or ["en", "en-US"]
        self.feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    def fetch(self, limit: int = 10) -> Iterable[Event]:
        try:
            feed = feedparser.parse(self.feed_url)
        except Exception as e:
            log.warning("YouTube RSS fetch failed for %s: %s", self.name, e)
            return []
        events: list[Event] = []
        for entry in (feed.entries or [])[:limit]:
            vid = self._video_id(entry)
            if not vid:
                continue
            url = f"https://www.youtube.com/watch?v={vid}"
            title = clean_html(str(getattr(entry, "title", "") or ""))
            published = parse_dt(getattr(entry, "published", None) or getattr(entry, "updated", None))
            if self.check_transcripts:
                chunks = self._transcript_chunks(vid)
                for i, (start, text) in enumerate(chunks):
                    if not text:
                        continue
                    events.append(
                        Event(
                            src=f"youtube:{self.channel_id}",
                            platform=f"YouTube - {self.name}",
                            item_id=f"{vid}:tr:{i}:{int(start)}",
                            text=text,
                            url=f"https://youtu.be/{vid}?t={int(start)}",
                            published_at=published,
                            detected_at=now_utc(),
                            kind="youtube_transcript",
                            meta={"video_id": vid, "title": title, "start_seconds": start},
                            raw=dict(entry),
                        )
                    )
                if chunks:
                    continue
            # Fallback: only title/description. This is useful when the title itself contains a direct quote.
            summary = clean_html(str(getattr(entry, "summary", "") or ""))
            events.append(
                Event(
                    src=f"youtube:{self.channel_id}",
                    platform=f"YouTube - {self.name}",
                    item_id=vid,
                    text=normalize_ws(f"{title}. {summary}"),
                    url=url,
                    published_at=published,
                    detected_at=now_utc(),
                    kind="rss",
                    meta={"video_id": vid, "title": title},
                    raw=dict(entry),
                )
            )
        return events

    @staticmethod
    def _video_id(entry) -> str:
        vid = str(getattr(entry, "yt_videoid", "") or "")
        if vid:
            return vid
        link = str(getattr(entry, "link", "") or "")
        if not link:
            return ""
        q = parse_qs(urlparse(link).query)
        return (q.get("v") or [""])[0]

    def _transcript_chunks(self, video_id: str) -> list[tuple[float, str]]:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except Exception:
            log.debug("youtube-transcript-api is not installed")
            return []
        try:
            data = None
            # Supports older and newer package APIs.
            if hasattr(YouTubeTranscriptApi, "get_transcript"):
                data = YouTubeTranscriptApi.get_transcript(video_id, languages=self.languages)
            else:
                api = YouTubeTranscriptApi()
                fetched = api.fetch(video_id, languages=self.languages)
                data = [x.to_raw_data() if hasattr(x, "to_raw_data") else x for x in fetched]
            segs = []
            for row in data or []:
                txt = normalize_ws(str(row.get("text", "")))
                if txt:
                    segs.append((float(row.get("start", 0.0)), txt))
            if not segs:
                return []
            chunks: list[tuple[float, str]] = []
            buf: list[str] = []
            start = segs[0][0]
            size = 0
            for st, txt in segs:
                if size + len(txt) > 900 and buf:
                    chunks.append((start, normalize_ws(" ".join(buf))))
                    buf = []
                    start = st
                    size = 0
                buf.append(txt)
                size += len(txt) + 1
            if buf:
                chunks.append((start, normalize_ws(" ".join(buf))))
            return chunks
        except Exception as e:
            log.debug("No public YouTube transcript for %s: %s", video_id, e)
            return []

from __future__ import annotations

import calendar
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import feedparser
import requests
from dateutil import parser as date_parser

from .extract import normalize_text, strip_html, stable_hash
from .models import SourceItem

LOG = logging.getLogger(__name__)
DEFAULT_USER_AGENT = "TrumpMarketAlert/1.0 (+https://github.com/260xs/trump-market-alert)"
RETRY_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


class HttpClient:
    def __init__(self, timeout: int = 20, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent or DEFAULT_USER_AGENT,
                "Accept": "application/json,text/html,application/xml,text/xml,*/*",
            }
        )

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout, headers=headers)
                if response.status_code in RETRY_STATUS_CODES and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    sleep_seconds = _safe_retry_after(retry_after) or attempt * 2
                    LOG.info("GET retryable status %s for %s; sleeping %ss", response.status_code, url, sleep_seconds)
                    time.sleep(sleep_seconds)
                    continue
                response.raise_for_status()
                return response
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < 3:
                    time.sleep(attempt * 2)
        raise RuntimeError(f"GET failed for {url}: {last_error}")


def _safe_retry_after(value: str | None) -> int | None:
    if not value:
        return None
    try:
        seconds = int(value.strip())
    except ValueError:
        return None
    return max(1, min(seconds, 30))


def _safe_int(value: Any, default: int, *, minimum: int = 1, maximum: int = 100) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(parsed, maximum))


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, str):
            dt = date_parser.parse(value)
        elif isinstance(value, time.struct_time):
            dt = datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc)
        else:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def parse_feed_time(entry: Any) -> datetime | None:
    for key in ("published", "updated", "created", "published_parsed", "updated_parsed"):
        value = getattr(entry, key, None)
        if value is None and hasattr(entry, "get"):
            value = entry.get(key)
        dt = parse_datetime(value)
        if dt:
            return dt
    return None


def is_recent_dt(value: datetime | None, max_age_hours: int) -> bool:
    if value is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    return value >= cutoff


def fetch_truth_social(config: dict[str, Any], client: HttpClient) -> list[SourceItem]:
    if not config.get("enabled", False):
        return []
    items: list[SourceItem] = []
    for account in config.get("accounts", []) or []:
        if not isinstance(account, dict) or not account.get("enabled", True):
            continue
        api_url = account.get("api_url")
        if not api_url:
            continue
        name = str(account.get("name", "Truth Social"))
        try:
            data = client.get(str(api_url)).json()
            if not isinstance(data, list):
                LOG.warning("Truth Social response was not a list for %s", name)
                continue
            limit = _safe_int(account.get("limit"), 20, minimum=1, maximum=40)
            for raw in data[:limit]:
                if not isinstance(raw, dict):
                    continue
                content = strip_html(str(raw.get("content", "")))
                url = str(raw.get("url") or raw.get("uri") or account.get("profile_url") or api_url)
                item_id = str(raw.get("id") or stable_hash(url, content))
                items.append(
                    SourceItem(
                        source_name=f"Truth Social - @{name}",
                        source_type="truth_social",
                        item_id=item_id,
                        title="Truth Social post",
                        text=content,
                        url=url,
                        published_at=parse_datetime(raw.get("created_at")),
                        author=name,
                        raw=raw,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Truth Social fetch failed for %s: %s", name, exc)
    return items


def fetch_rss(config: dict[str, Any], client: HttpClient) -> list[SourceItem]:
    if not config.get("enabled", False):
        return []
    items: list[SourceItem] = []
    for feed in config.get("feeds", []) or []:
        if not isinstance(feed, dict) or not feed.get("enabled", True):
            continue
        url = feed.get("url")
        if not url:
            continue
        name = str(feed.get("name", "RSS"))
        try:
            response = client.get(str(url), headers={"Accept": "application/rss+xml,application/xml,text/xml,*/*"})
            parsed = feedparser.parse(response.content)
            if getattr(parsed, "bozo", False):
                LOG.info("Feed parser warning for %s: %s", name, getattr(parsed, "bozo_exception", "unknown"))
            limit = _safe_int(feed.get("limit"), 20, minimum=1, maximum=50)
            for entry in parsed.entries[:limit]:
                title = normalize_text(getattr(entry, "title", "") or entry.get("title", ""))
                summary = strip_html(getattr(entry, "summary", "") or entry.get("summary", ""))
                link = str(getattr(entry, "link", "") or entry.get("link", "") or url)
                entry_id = str(getattr(entry, "id", "") or entry.get("id", "") or stable_hash(link, title, summary))
                items.append(
                    SourceItem(
                        source_name=name,
                        source_type="rss",
                        item_id=entry_id,
                        title=title,
                        text=summary,
                        url=link,
                        published_at=parse_feed_time(entry),
                        raw=dict(entry),
                    )
                )
        except Exception as exc:  # noqa: BLE001
            LOG.warning("RSS fetch failed for %s: %s", name, exc)
    return items


def youtube_feed_url(channel_id: str) -> str:
    return "https://www.youtube.com/feeds/videos.xml?" + urlencode({"channel_id": channel_id})


def _transcript_to_text(transcript: Any) -> str:
    """Convert youtube-transcript-api return types into plain text.

    The library changed its public API after the 0.6.x series. Current versions
    return a FetchedTranscript object with snippet objects; older versions return
    a list of dictionaries. Supporting both keeps the scanner stable when the
    GitHub runner installs a newer dependency version.
    """

    if transcript is None:
        return ""

    try:
        to_raw_data = getattr(transcript, "to_raw_data", None)
        if callable(to_raw_data):
            transcript = to_raw_data()
    except Exception:  # noqa: BLE001
        pass

    rows = getattr(transcript, "snippets", transcript)
    parts: list[str] = []

    try:
        iterator = iter(rows)
    except TypeError:
        return ""

    for row in iterator:
        if isinstance(row, dict):
            value = row.get("text", "")
        else:
            value = getattr(row, "text", "")
        if value:
            parts.append(str(value))

    return normalize_text(" ".join(parts))


def fetch_youtube_transcript(video_id: str) -> str:
    if not video_id:
        return ""

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except Exception as exc:  # noqa: BLE001
        LOG.info("youtube-transcript-api is unavailable: %s", exc)
        return ""

    languages = ["en", "en-US", "en-GB"]

    try:
        api = YouTubeTranscriptApi()
        fetch = getattr(api, "fetch", None)
        if callable(fetch):
            return _transcript_to_text(fetch(video_id, languages=languages))
    except Exception as exc:  # noqa: BLE001
        LOG.info("Current YouTube transcript fetch failed for %s: %s", video_id, exc)

    try:
        get_transcript = getattr(YouTubeTranscriptApi, "get_transcript", None)
        if callable(get_transcript):
            return _transcript_to_text(get_transcript(video_id, languages=languages))
    except Exception as exc:  # noqa: BLE001
        LOG.info("Legacy YouTube transcript fetch failed for %s: %s", video_id, exc)

    return ""


def fetch_youtube(config: dict[str, Any], client: HttpClient) -> list[SourceItem]:
    if not config.get("enabled", False):
        return []
    items: list[SourceItem] = []
    transcript_enabled = bool(config.get("transcript_enabled", True))
    transcript_max_age_hours = _safe_int(config.get("transcript_max_age_hours"), 96, minimum=1, maximum=720)

    for channel in config.get("channels", []) or []:
        if not isinstance(channel, dict) or not channel.get("enabled", True):
            continue
        channel_id = channel.get("channel_id")
        if not channel_id:
            continue
        name = str(channel.get("name", "YouTube"))
        try:
            feed_url = youtube_feed_url(str(channel_id))
            response = client.get(feed_url, headers={"Accept": "application/rss+xml,application/xml,text/xml,*/*"})
            parsed = feedparser.parse(response.content)
            limit = _safe_int(channel.get("limit"), 10, minimum=1, maximum=25)
            for entry in parsed.entries[:limit]:
                title = normalize_text(getattr(entry, "title", "") or entry.get("title", ""))
                link = str(getattr(entry, "link", "") or entry.get("link", ""))
                video_id = str(entry.get("yt_videoid") or entry.get("yt_videoId") or link.rsplit("v=", 1)[-1])
                summary = strip_html(getattr(entry, "summary", "") or entry.get("summary", ""))
                published_at = parse_feed_time(entry)
                should_fetch_transcript = transcript_enabled and bool(video_id) and is_recent_dt(published_at, transcript_max_age_hours)
                transcript = fetch_youtube_transcript(video_id) if should_fetch_transcript else ""
                text = normalize_text(f"{summary} {transcript}")
                items.append(
                    SourceItem(
                        source_name=f"YouTube - {name}",
                        source_type="youtube",
                        item_id=video_id or stable_hash(link, title),
                        title=title,
                        text=text,
                        url=link or feed_url,
                        published_at=published_at,
                        author=name,
                        raw=dict(entry),
                    )
                )
        except Exception as exc:  # noqa: BLE001
            LOG.warning("YouTube fetch failed for %s: %s", name, exc)
    return items


def fetch_x_api(config: dict[str, Any], client: HttpClient, bearer_token: str | None) -> list[SourceItem]:
    if not config.get("enabled", False) or not bearer_token:
        return []
    items: list[SourceItem] = []
    url = "https://api.x.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {bearer_token}", "Accept": "application/json"}
    max_results = _safe_int(config.get("max_results"), 10, minimum=10, maximum=100)

    for query in config.get("queries", []) or []:
        params = {
            "query": str(query),
            "max_results": str(max_results),
            "tweet.fields": "created_at,author_id,entities",
        }
        try:
            response = client.get(url, params=params, headers=headers)
            data = response.json()
            for tweet in data.get("data", []) or []:
                if not isinstance(tweet, dict):
                    continue
                text = normalize_text(tweet.get("text", ""))
                tweet_id = str(tweet.get("id") or stable_hash(text))
                items.append(
                    SourceItem(
                        source_name="X API recent search",
                        source_type="x_api",
                        item_id=tweet_id,
                        title="X post mentioning Trump and markets",
                        text=text,
                        url=f"https://x.com/i/web/status/{tweet_id}",
                        published_at=parse_datetime(tweet.get("created_at")),
                        raw=tweet,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            LOG.warning("X API fetch failed: %s", exc)
    return items


def fetch_all_sources(sources_config: dict[str, Any], x_bearer_token: str | None = None) -> list[SourceItem]:
    polling = sources_config.get("polling", {}) or {}
    timeout = _safe_int(polling.get("request_timeout_seconds"), 20, minimum=5, maximum=45)
    user_agent = str(polling.get("user_agent") or DEFAULT_USER_AGENT)

    client = HttpClient(timeout=timeout, user_agent=user_agent)
    items: list[SourceItem] = []
    items.extend(fetch_truth_social(sources_config.get("truth_social", {}) or {}, client))
    items.extend(fetch_rss(sources_config.get("rss", {}) or {}, client))
    items.extend(fetch_youtube(sources_config.get("youtube", {}) or {}, client))
    items.extend(fetch_x_api(sources_config.get("x_api", {}) or {}, client, x_bearer_token))
    return items
